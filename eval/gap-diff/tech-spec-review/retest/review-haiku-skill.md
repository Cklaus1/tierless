# Technical Review: Real-Time Notification Fanout

**Spec:** Design Doc: Real-Time Notification Fanout
**Reviewer:** Haiku (skill-driven, five-audit process)
**Verdict:** NOT BUILDABLE — 6 blocking findings, 4 significant, 2 minor

---

## Blocking Findings

### B1. Redis Pub/Sub is fire-and-forget with no delivery guarantee

**Assumption:** The spec assumes that publishing a message to `redis pub/sub channel notifications:<user_id>` is a reliable delivery mechanism.

**Concrete failure:** Redis Pub/Sub is ephemeral and fire-and-forget. If the Fanout Service is momentarily unable to subscribe (e.g., during startup, failover, or a brief Redis network blip), messages published to that channel are **silently lost** — they are not queued, not retried, not persisted. The user never sees the notification, and there is no reconciliation path because the `notifications` table write happens independently.

**Required change:** Either (a) use a persistent queue (e.g., Redis Streams, a message broker with durability) so that messages are buffered until a subscriber is available, or (b) add a reconciliation mechanism that periodically compares the `notifications` table against what was actually delivered via WebSocket and pushes any missed notifications on reconnect. The spec describes neither.

---

### B2. No reconnection strategy for WebSocket connections

**Assumption:** The spec assumes that once a WebSocket connection is established, it persists. It says "the client opens a WebSocket to the Fanout Service on app load" but never describes what happens when the connection drops.

**Concrete failure:** Network blips, server restarts, and load balancer health-check drains all terminate WebSocket connections. Without an explicit reconnection strategy (with backoff-and-jitter to prevent stampedes), the client will either (a) reconnect immediately and flood the service, or (b) never reconnect at all and the user is permanently disconnected. The spec is silent on this entirely.

**Required change:** Define a reconnection protocol: client-side exponential backoff with jitter (e.g., base 1s, max 30s, jitter 50%), re-subscribe to the user's Redis channel on reconnect, and handle the gap between disconnection and reconnection (see B1).

---

### B3. Simultaneous restart of all Fanout Service instances kills all connections

**Assumption:** The spec says "3 instances behind a load balancer for redundancy" but does not describe rolling restarts, draining, or staggered deployment.

**Concrete failure:** If all 3 instances restart simultaneously (e.g., a deployment, a crash, or a Redis failover that causes all instances to reconnect), **every** WebSocket connection drops at once. Combined with the missing reconnection strategy (B2), this creates a correlated failure: all clients reconnect simultaneously, all request Redis subscriptions simultaneously, and the Fanout Service and Redis both experience a stampede. This is the default outcome in any stateful connection-oriented tier without explicit mitigation.

**Required change:** Define a rolling deployment strategy with connection draining. On restart, the service should drain existing connections (send a close frame with a retry-after hint) before shutting down. Clients must use backoff-with-jitter on reconnect. The spec must state these mechanisms explicitly.

---

### B4. "Turn off polling" breaks clients that have not yet updated

**Assumption:** The rollout says "switch the client to WebSockets in the next app release, and turn off polling." This assumes all clients will have the new WebSocket code before polling is disabled.

**Concrete failure:** App releases are not atomic. A significant fraction of users will still be running the old polling-based client when polling is turned off. Those users will receive **no notifications at all** until they update. This is not a gradual rollout — it is a hard cutover that breaks a population of users.

**Required change:** Implement a feature flag or server-side capability negotiation so that old clients continue to receive notifications via polling while new clients use WebSockets. Polling should be deprecated, not removed, until the old client population is negligible. The spec must define a transition period and a rollback plan.

---

### B5. Dual-write: DB write and Redis publish have no ordering or consistency guarantee

**Assumption:** The spec says "we keep writing to the notifications table so history still works" and separately "publishes a message to Redis." These are two independent writes with no coordination.

**Concrete failure in both directions:**

- **DB write succeeds, Redis publish fails:** The notification appears in history but the user never sees it in real time. The user sees it only the next time they poll (if polling is still on) or never (if polling is off). This is a **silent loss**.
- **Redis publish succeeds, DB write fails:** The user sees a real-time notification that never appears in their history. This is a **ghost notification** — it creates a worse UX than missing the notification entirely, because the user sees something that "disappears" when they check history.

**Required change:** Either (a) make the Redis publish conditional on a successful DB write (DB first, then publish), or (b) use a transactional outbox pattern where a single write to a durable table is then consumed by a fanout worker that publishes to Redis. The spec must define the ordering and the partial-failure handling for both directions.

---

### B6. Mobile backgrounded apps cannot maintain WebSockets

**Assumption:** The spec says "instant" delivery via WebSocket, which works fine in a foreground browser tab.

**Concrete failure:** On mobile platforms (iOS Safari, Android Chrome), backgrounded tabs have their WebSocket connections killed by the OS after a short period (typically 5-30 minutes). The user will not receive real-time notifications while the app is backgrounded. The spec's core value proposition ("instant") is broken for the mobile population, which is a significant and growing share of users.

**Required change:** Add a push notification fallback (APNs for iOS, FCM for Android) for the mobile population. The spec must define when push is used vs. WebSocket, and how the two delivery paths are deduplicated so the user doesn't see the same notification twice.

---

## Significant Findings

### S1. "One WebSocket connection per online user" breaks multi-device users

**Assumption:** The spec says "A new Fanout Service holds one WebSocket connection per online user."

**Concrete failure:** Users routinely have multiple devices (phone + laptop + tablet) and multiple browser tabs open. If the Fanout Service only tracks one connection per user, then: (a) the second device/tab to connect may not receive the notification if the first connection is stale or in a bad state, or (b) the second connection overwrites the first, causing the first to miss notifications. The spec does not define which connection is authoritative.

**Required change:** Track connections per user-device or per-session, not per-user. The Fanout Service must fan out to all active connections for a given user, not just one.

---

### S2. No authentication or authorization for WebSocket connections

**Assumption:** The spec says "the client opens a WebSocket to the Fanout Service" but does not describe how the service authenticates the connecting client.

**Concrete failure:** Without authentication, any client can connect to any user's WebSocket channel by guessing or enumerating user IDs. An attacker could subscribe to `notifications:<other_user_id>` and read that user's notifications in real time. This is a critical security gap.

**Required change:** Define an authentication mechanism for WebSocket connections (e.g., signed JWT in the connection URL or upgrade handshake). The Fanout Service must verify the connecting user has permission to subscribe to the requested channel before subscribing.

---

### S3. No rate limiting on the Fanout Service

**Assumption:** The spec does not mention rate limiting for either incoming publishes or outgoing WebSocket pushes.

**Concrete failure:** A single user with a very high notification volume (e.g., a popular user being mentioned in a viral thread) could overwhelm the Fanout Service's WebSocket connection to that user. Similarly, a single originating service could flood the Redis channels. Without rate limiting, this becomes a denial-of-service vector.

**Required change:** Define rate limits per-user and per-originating-service for both Redis publishes and WebSocket pushes. Define a backpressure strategy when limits are exceeded (queue, drop, or batch).

---

### S4. No message deduplication

**Assumption:** The spec does not address whether the same notification could be delivered multiple times.

**Concrete failure:** If an originating service retries a publish (e.g., due to a timeout), or if the Fanout Service reconnects and re-subscribes to a Redis channel, the same notification could be pushed to the client multiple times. The client has no way to deduplicate without a message ID.

**Required change:** Each notification must have a unique ID. The client must track recently seen IDs and deduplicate. The Fanout Service should also deduplicate before pushing.

---

## Minor Findings

### M1. "3 instances" is an unexplained magic number

**Assumption:** The spec says "3 instances" without explaining the sizing rationale.

**Concrete failure:** If the actual load exceeds what 3 instances can handle, the service degrades. If the load is much lower, 3 instances are wasteful. The spec should state the expected connection count per instance, the autoscaling policy, and whether 3 gives N+1 headroom over the expected peak.

**Required change:** Define the expected peak concurrent connections, connections per instance, and autoscaling thresholds. State the N+1 headroom assumption explicitly.

---

### M2. "Sub-second delivery" is unspecified by percentile

**Assumption:** The spec claims "Expected latency: sub-second delivery."

**Concrete failure:** "Sub-second" is meaningless without a percentile. p50 sub-second with p99 at 10 seconds is a very different SLA than p99 sub-second. The spec must define which percentile is targeted and the measurement methodology.

**Required change:** Define the latency target as, e.g., "p99 delivery latency under 1 second" and describe how this is measured (client-side timestamp, server-side timestamp, or both).

---

## Summary

| Category | Count |
|----------|-------|
| Blocking | 6 |
| Significant | 4 |
| Minor | 2 |

The design is **not buildable as-is**. The most critical gaps are:

1. **Redis Pub/Sub is not a reliable delivery mechanism** for a notification system — messages are lost on subscriber unavailability with no recovery path.
2. **No reconnection strategy** means any restart or network blip permanently disconnects users.
3. **Hard cutover rollout** (turn off polling) will break a significant population of users who have not updated their app.
4. **No authentication** on WebSocket connections is a critical security vulnerability.
5. **Dual-write inconsistency** between the DB and Redis has no handling for partial failures in either direction.

The spec would need to be substantially revised before implementation can begin. The core architecture (WebSocket fanout + Redis Pub/Sub) is reasonable for a first pass, but the reliability, security, and rollout assumptions are all incomplete.