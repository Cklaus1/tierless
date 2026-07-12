# Spec Review: Real-Time Notification Fanout

**Spec:** Design Doc: Real-Time Notification Fanout
**Reviewer:** sonnet (applying spec-review skill — five audits)
**Verdict:** NOT BUILDABLE as-is. Multiple blocking findings in dependency-failure, dual-write/ordering, correlated-event, and goal x population audits.

---

## 1. Dependency-Failure Audit

### D1. Redis Pub/Sub is the sole transport — it is a single point of failure.
**Assumption:** The Fanout Service subscribes to Redis Pub/Sub channels and relies on Redis being available at all times for message delivery.
**Concrete failure:** When Redis restarts (planned deploy, crash, or network partition), all subscriptions are lost. The Fanout Service has no mechanism to detect this and re-subscribe. During the outage window, zero WebSocket pushes occur. Users see no new notifications until Redis recovers and the service is manually or automatically restarted. The spec says nothing about degraded mode, health checks against Redis, or reconnection logic.
**Required change:** Add explicit Redis failure handling: periodic health checks, automatic re-subscribe on reconnect, and a fallback path (e.g., resume polling or queue messages locally) when Redis is unreachable. Define the degraded mode explicitly.

### D2. The Fanout Service itself is a single point of failure per user.
**Assumption:** "A new Fanout Service holds one WebSocket connection per online user."
**Concrete failure:** If the Fanout Service process crashes or is redeployed, all WebSocket connections drop simultaneously. The spec says "3 instances behind a load balancer" but does not explain how user state (which user is on which instance) is shared or migrated. A crash means every user's connection is dead, and there is no mechanism to re-establish those connections on another instance. Users lose real-time delivery until they manually reload the page.
**Required change:** Define how user-to-instance mapping is maintained across restarts. Either: (a) a shared registry (e.g., Redis) where instances announce which user-IDs they serve, and the load balancer routes by user-ID; or (b) a broadcast mechanism where all instances subscribe to all channels and the load balancer is irrelevant for fanout. The spec must name the chosen approach.

### D3. The load balancer is an unexamined dependency.
**Assumption:** "3 instances of the Fanout Service behind a load balancer."
**Concrete failure:** The load balancer must route WebSocket connections to the correct instance (sticky sessions or user-ID-based routing). If it uses round-robin without sticky sessions, a user's reconnection after a blip may land on a different instance that does not know about that user's subscription. The spec does not mention sticky sessions, connection affinity, or any routing strategy.
**Required change:** Specify load balancer configuration: sticky sessions by user-ID, or a routing layer that maps user-ID to instance. Document the failover behavior when an instance goes down.

### D4. The originating services (which publish to Redis) have no failure path documented.
**Assumption:** "the originating service publishes a message to a new Redis Pub/Sub channel."
**Concrete failure:** If the originating service crashes between publishing to Redis and the event being fully committed to the `notifications` table, the WebSocket push goes out but the DB write never happens. The user sees a notification in real-time that does not appear in their history. Conversely, if the DB write succeeds but Redis publish fails, the user never gets the real-time push but the notification exists in history.
**Required change:** Define the ordering of DB write vs. Redis publish. Either: (a) DB write first, then publish (so the notification always exists in history); or (b) a transactional dual-write with a reconciliation process.

---

## 2. Dual-Write / Ordering Audit

### DW1. Writing to `notifications` table AND publishing to Redis — ordering is unspecified.
**Assumption:** "We keep writing to the `notifications` table so history still works" and "the originating service publishes a message to a new Redis Pub/Sub channel."
**Concrete failure (DB succeeds, Redis fails):** The notification is persisted in the database but never pushed via WebSocket. The user does not see it in real-time. They discover it on the next poll (but polling is being dropped). Result: the notification is silently lost in real-time, and the user never sees it at all unless they manually refresh or the old polling is kept as a fallback.
**Concrete failure (Redis succeeds, DB fails):** The notification is pushed to the user's WebSocket but never persisted. The user sees it in real-time, but it disappears from history. If they reload the page, it is gone. This is a ghost notification.
**Required change:** Define a strict ordering: DB write must happen first, then Redis publish. If Redis publish fails, retry with backoff. The spec must state this explicitly and describe the retry/fallback behavior.

### DW2. No reconciliation mechanism for dual-write divergence.
**Assumption:** The spec assumes both writes always succeed or that one being missing is acceptable.
**Concrete failure:** Over time, transient failures accumulate. Some notifications exist only in Redis (never persisted), some only in the DB (never pushed). There is no audit trail, no reconciliation job, and no way to detect the divergence.
**Required change:** Add a reconciliation mechanism: a periodic job that compares the `notifications` table against a Redis-side tracking set, or a dead-letter queue for failed Redis publishes that are retried later.

---

## 3. Correlated-Event Audit

### CE1. Mass reconnect storm on Fanout Service deploy or crash.
**Assumption:** "We'll deploy the Fanout Service, switch the client to WebSockets."
**Concrete failure:** When the Fanout Service is deployed (all 3 instances restart simultaneously), every connected WebSocket drops at once. Thousands of clients attempt to reconnect simultaneously, creating a reconnect storm. The load balancer receives a spike of connection attempts. The Fanout Service instances must re-subscribe to all Redis channels, creating a burst of Redis traffic. This can overwhelm both the load balancer and Redis.
**Required change:** Implement staggered rolling restarts (not all 3 instances at once). Add exponential backoff with jitter on client reconnect. Consider connection draining on the load balancer before instance shutdown.

### CE2. Cache stampede / Redis channel subscription storm on restart.
**Assumption:** After a restart, all instances re-subscribe to all channels.
**Concrete failure:** If there are 100,000 online users, each with a unique Redis channel, all 3 Fanout Service instances re-subscribing to all 100,000 channels simultaneously creates a massive Redis load spike. Redis Pub/Sub does not persist subscriptions, so every instance must re-subscribe to every channel it serves. This can cause Redis CPU spikes and increased latency for all pub/sub traffic.
**Required change:** Stagger re-subscriptions across instances. Consider a subscription registry where one instance "owns" a subset of channels and other instances only take over on failure.

### CE3. Network blip causes correlated disconnects across all instances.
**Assumption:** A transient network issue affects all connections.
**Concrete failure:** A network blip that affects the load balancer or the connection between Fanout Service instances and Redis causes all WebSocket connections to drop simultaneously. The same reconnect storm as CE1 applies.
**Required change:** Same as CE1: backoff-with-jitter, staggered restarts, and explicit degraded mode.

---

## 4. Goal x Population x State Cross-Product

### GP1. "Instant" delivery x mobile-backgrounded app.
**Assumption:** "We want notifications to feel instant" and "the client opens a WebSocket to the Fanout Service on app load."
**Concrete failure:** On mobile, when the app is backgrounded, the OS may kill the WebSocket connection (iOS suspends background network, Android limits background connectivity). The user never receives real-time notifications while the app is in the background. They only receive them when they reopen the app — which is not "instant."
**Required change:** Add platform push notifications (APNs for iOS, FCM for Android) as a fallback when the WebSocket is not active. The spec must address mobile explicitly, not just "browsers."

### GP2. "Drop the 30-second polling" x already-shipped old clients.
**Assumption:** "We'll deploy the Fanout Service, switch the client to WebSockets in the next app release, and turn off polling."
**Concrete failure:** App releases are not atomic. Users who do not update immediately (or cannot update, e.g., enterprise deployments) continue running the old polling client. If polling is turned off server-side, these users lose all notification delivery. Even if polling is kept for old clients, the spec does not mention versioned API support or a deprecation timeline.
**Required change:** Do not turn off polling until a deprecation period has passed and a mechanism exists to identify which clients support WebSockets. Implement a feature flag or API version check so old clients continue polling while new clients use WebSockets.

### GP3. "One WebSocket connection per online user" x multi-tab / multi-device.
**Assumption:** "A new Fanout Service holds one WebSocket connection per online user."
**Concrete failure:** A user with two browser tabs open to the app will open two WebSocket connections. The Fanout Service has no deduplication logic, so the same notification is pushed twice (once per tab). A user on a phone and a laptop opens two connections on different instances. The notification is pushed to both instances, and the user sees it twice (once on each device). This is acceptable for some notification types (message, mention) but not for others (system alert, follow) — the spec does not differentiate.
**Required change:** Implement per-user connection deduplication: either the client sends a user-ID in the connection URL and the Fanout Service deduplicates, or the client manages a single connection and reconnects on tab visibility change. For multi-device, decide whether notifications should be delivered to all devices or just the most recent one.

### GP4. "Sub-second delivery" x slow / high-latency networks.
**Assumption:** "Expected latency: sub-second delivery."
**Concrete failure:** Sub-second from what point to what point? From the originating service publishing to Redis, to the user seeing it on screen? On a 3G connection with 500ms RTT, the WebSocket message itself takes 500ms+ to arrive. The "sub-second" claim is only true for p50 on good networks, not p99. The spec does not define the measurement boundary or the percentile.
**Required change:** Define the latency metric precisely: "p99 end-to-end latency from event publish to client render is under 2 seconds on 4G networks." Remove the vague "sub-second" claim.

### GP5. "3 instances" x traffic volume.
**Assumption:** "We'll run 3 instances of the Fanout Service behind a load balancer for redundancy."
**Concrete failure:** Where did "3" come from? If there are 100,000 concurrent WebSocket connections, each instance holds ~33,000 connections. Node.js can handle this, but the memory, file descriptor, and network bandwidth per instance must be calculated. If there are 1,000,000 concurrent users, 3 instances is insufficient. The number 3 gives no N+1 headroom — it is just enough for redundancy, not for scaling.
**Required change:** Calculate the expected concurrent connections and messages-per-second. Size instances based on that calculation. Define auto-scaling policy. The number 3 must be derived from a capacity plan, not chosen arbitrarily.

### GP6. WebSocket x browser without WebSocket support.
**Assumption:** "They're widely supported in browsers."
**Concrete failure:** Some enterprise environments block WebSocket connections via firewalls or proxy servers. Corporate VPNs, some mobile carriers, and older browsers (IE11 without polyfill) do not support WebSockets. These users lose all notification delivery if polling is turned off.
**Required change:** Add a fallback mechanism for clients that cannot maintain a WebSocket: SSE (Server-Sent Events) or keep polling as a graceful degradation path.

---

## 5. Quantify-the-Claims Audit

### QC1. "Sub-second delivery" — no percentile, no measurement boundary.
**Claim:** "Expected latency: sub-second delivery."
**Measurable target needed:** "p99 end-to-end latency from event publish to client render is under X seconds on Y network condition." Without a percentile, "sub-second" is meaningless — it could be p50 while p99 is 10 seconds.

### QC2. "Cuts load 40%" — unverified and contradicted by the design.
**Claim:** The background section states polling is "~40% of read traffic at peak." The design claims to eliminate polling, implying a 40% load reduction.
**Measurable target needed:** The net effect must account for: (a) WebSocket connection overhead (each connection consumes memory and file descriptors on the Fanout Service); (b) Redis Pub/Sub bandwidth (each notification is published to a channel, which is additional load on Redis); (c) the dual-write (DB write + Redis publish) adds write load, not just read load. The spec does not quantify the net effect. The 40% reduction in DB read traffic may be offset by increased Redis load and Fanout Service resource consumption.
**Required change:** Provide a capacity analysis showing the net load change across all affected systems (DB, Redis, Fanout Service, load balancer).

### QC3. "Widely supported in browsers" — unquantified.
**Claim:** "They're widely supported in browsers."
**Measurable target needed:** What percentage of the user base uses a browser that supports WebSockets? If 5% of users are on unsupported browsers, the design breaks for them. The spec must quantify the supported browser share.

### QC4. "Low overhead per message" — unquantified.
**Claim:** "WebSockets give us true server push with low overhead per message."
**Measurable target needed:** What is the per-message overhead in bytes? How does it compare to the 30-second polling request overhead (which includes headers, HTTP framing, etc.)? The spec should quantify the bandwidth savings.

---

## Summary of Findings

| # | Audit | Severity | Finding |
|---|-------|----------|---------|
| D1 | Dependency-failure | **BLOCKING** | Redis is a single point of failure with no degraded mode or reconnection logic |
| D2 | Dependency-failure | **BLOCKING** | Fanout Service crash kills all user connections with no state migration |
| D3 | Dependency-failure | **BLOCKING** | Load balancer routing strategy for WebSocket connections is unspecified |
| D4 | Dependency-failure | **SIGNIFICANT** | Originating service failure path (publish vs. DB write ordering) is undefined |
| DW1 | Dual-write | **BLOCKING** | DB write vs. Redis publish ordering is unspecified; both failure directions produce data loss |
| DW2 | Dual-write | **SIGNIFICANT** | No reconciliation mechanism for dual-write divergence |
| CE1 | Correlated-event | **BLOCKING** | Mass reconnect storm on deploy/crash with no backoff or stagger strategy |
| CE2 | Correlated-event | **SIGNIFICANT** | Redis channel subscription storm on restart with no staggering |
| CE3 | Correlated-event | **SIGNIFICANT** | Network blip causes correlated disconnects with no mitigation |
| GP1 | Goal x population | **BLOCKING** | Mobile backgrounded apps lose WebSocket; no push notification fallback |
| GP2 | Goal x population | **BLOCKING** | Turning off polling breaks old clients that have not updated |
| GP3 | Goal x population | **SIGNIFICANT** | Multi-tab and multi-device users receive duplicate notifications |
| GP4 | Goal x population | **SIGNIFICANT** | "Sub-second" is undefined; high-latency networks break the claim |
| GP5 | Goal x population | **SIGNIFICANT** | "3 instances" is arbitrary; no capacity plan or auto-scaling |
| GP6 | Goal x population | **SIGNIFICANT** | Enterprise/VPN environments may block WebSockets with no fallback |
| QC1 | Quantify-claims | **SIGNIFICANT** | "Sub-second" has no percentile or measurement boundary |
| QC2 | Quantify-claims | **SIGNIFICANT** | 40% load reduction claim ignores Fanout Service and Redis overhead |
| QC3 | Quantify-claims | **MINOR** | "Widely supported" is unquantified |
| QC4 | Quantify-claims | **MINOR** | "Low overhead" is unquantified |

**Blocking findings: 7** (D1, D2, D3, DW1, CE1, GP1, GP2)
**Significant findings: 9** (D4, DW2, CE2, CE3, GP3, GP4, GP5, GP6, QC1, QC2)
**Minor findings: 2** (QC3, QC4)

**Verdict: NOT BUILDABLE.** The spec is a sketch, not a design. The core architecture (Fanout Service + Redis Pub/Sub + WebSockets) is sound in concept, but the following must be resolved before implementation:

1. **Redis failure handling and reconnection** (D1)
2. **User-to-instance state management across restarts** (D2)
3. **Load balancer routing strategy** (D3)
4. **Dual-write ordering: DB first, then Redis, with retry** (DW1)
5. **Reconnect storm mitigation: backoff-with-jitter, staggered restarts** (CE1)
6. **Mobile push notification fallback** (GP1)
7. **Gradual rollout: do not turn off polling until old clients are deprecated** (GP2)

Without these, the system will lose notifications on any Redis outage, any deploy, any crash, and will break for mobile users and users on old app versions.