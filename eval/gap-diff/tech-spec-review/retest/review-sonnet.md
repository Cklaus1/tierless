# Technical Review: Real-Time Notification Fanout

**Spec:** Design Doc: Real-Time Notification Fanout
**Author:** platform team
**Status:** proposed
**Reviewer:** Sonnet
**Date:** 2026-07-11

---

## Summary

The spec proposes adding a WebSocket-based Fanout Service backed by Redis Pub/Sub to replace 30-second client polling for notifications. The core idea is sound, but the document is extremely thin -- it omits nearly every operational, reliability, security, and correctness detail required to implement, deploy, or maintain this system. As written, it would produce a prototype, not a production-ready service. Below are all identified problems, risks, and gaps, organized by category.

---

## 1. Architecture & Design Gaps

### 1.1 [HIGH] No fanout-to-client routing strategy

The spec says "We'll run 3 instances of the Fanout Service behind a load balancer for redundancy" but does not specify how a WebSocket connection for user X is directed to the correct instance. Redis Pub/Sub delivers a message to **all** subscribers, so all three instances would receive every `notifications:<user_id>` message. The spec must define:

- **Connection ownership:** Which instance owns the WebSocket for a given user? Is it sticky (consistent hash on user_id)? Is it dynamic (any instance can serve, with a directory service)?
- **Duplicate prevention:** If all instances receive every pub/sub message, how are duplicates avoided? Without a dedup mechanism, the client would render the same notification multiple times.
- **Connection migration:** If an instance crashes, what happens to the WebSocket connections it owned? Is there a directory (e.g., Redis keys mapping user_id to instance_id) so another instance can take over?

### 1.2 [HIGH] No state synchronization between instances

Because Redis Pub/Sub fans out to all subscribers, all three instances receive every notification event. The spec does not address:

- How an instance knows whether it is the one that should forward a given notification to the client.
- Whether a per-instance in-memory set of "user_id -> WebSocket" is sufficient, or whether a shared directory (Redis hash) is needed for cross-instance lookup.
- What happens when a user reconnects -- does the new instance need to fetch missed notifications from the database?

### 1.3 [MEDIUM] No client reconnection / session recovery strategy

The spec says "The client opens a WebSocket on app load" but does not address:

- **Reconnection logic:** What happens when the WebSocket drops (network blip, server restart, client goes to background)? Exponential backoff? Jitter?
- **Missed notification recovery:** If the client disconnects for even a few seconds, it misses notifications. The spec says "we keep writing to the notifications table" but does not say how the client fetches missed notifications after reconnect. Does the client poll once on reconnect? Does the Fanout Service buffer messages?
- **Session resumption:** If the client reconnects to a different instance, how does the new instance know which notifications the client has already seen?

### 1.4 [MEDIUM] No backward compatibility / phased rollout plan

The spec says "switch the client to WebSockets in the next app release, and turn off polling." This is a breaking change with no transition period:

- **Gradual rollout:** How do you roll out to 1% of users, then 10%, then 100%? There is no feature flag or percentage-based rollout described.
- **Rollback:** If the Fanout Service has a bug that causes duplicate notifications or crashes, how quickly can you roll back? The spec does not mention a kill switch to re-enable polling.
- **Client version diversity:** If the app is mobile, users may be on old versions that do not support WebSockets. The spec does not address supporting multiple client versions simultaneously.

### 1.5 [MEDIUM] No load balancer configuration detail

Running 3 instances behind a load balancer is mentioned but not specified:

- **WebSocket support:** Standard HTTP load balancers do not handle WebSocket upgrades. The LB must support the `Upgrade: websocket` header and maintain connection affinity (or the architecture must handle cross-instance fanout, see 1.1).
- **Health checks:** WebSocket connections are long-lived. Standard HTTP health checks will not work. The spec needs a WebSocket-aware health check strategy.
- **Connection limits:** What is the max connections per instance? With 3 instances, what is the total capacity? If each user has one WebSocket, and you have 100K active users, 3 instances may not be enough.

---

## 2. Reliability & Resilience

### 2.1 [HIGH] No Redis failure mode handling

The entire fanout mechanism depends on Redis Pub/Sub. The spec does not address:

- **Redis outage:** If Redis is down, the Fanout Service cannot subscribe to channels. Notifications stop being delivered in real time. What is the fallback? Does the spec intend for polling to remain as a fallback? If so, for how long?
- **Redis network partition:** If the Fanout Service loses connectivity to Redis but Redis is still running, the service silently stops delivering notifications. There is no circuit breaker or alerting described.
- **Redis single point of failure:** The spec does not mention Redis HA (sentinel, cluster, or managed service with failover). A single Redis instance is a single point of failure for the entire notification system.

### 2.2 [HIGH] Fanout Service has no self-healing / restart behavior

- **Crash recovery:** If a Fanout Service instance crashes, all its WebSocket connections are dropped. The spec does not describe how the service recovers -- does it restart automatically? Does it re-subscribe to channels?
- **Graceful shutdown:** When deploying a new version, how are connections drained? If instances are replaced without draining, users lose their WebSocket connections mid-conversation.
- **Memory leak risk:** Holding one WebSocket per user is a long-lived resource. If the service leaks file descriptors or memory over time, it will eventually crash. No monitoring or auto-restart policy is described.

### 2.3 [MEDIUM] No backpressure or message ordering guarantee

- **Message ordering:** If user A mentions user B, and user C follows user B, both events may be published nearly simultaneously. Is there a guarantee that notifications arrive in the order they were created? Redis Pub/Sub does not guarantee ordering across different channels.
- **Backpressure:** If a client's WebSocket is slow to receive messages (e.g., the client is on a slow network), the Fanout Service's send buffer could grow unbounded. Is there a per-connection send buffer limit? What happens when it's full -- drop messages, block the publisher, or disconnect the client?
- **Publisher rate limiting:** If a single user triggers many events rapidly (e.g., a bot that mentions many users), the Fanout Service could be overwhelmed. Is there a rate limit on event publishing?

### 2.4 [MEDIUM] No idempotency for notification delivery

- **Duplicate delivery:** If the Fanout Service receives the same pub/sub message twice (e.g., due to a Redis retry or network issue), the client would see duplicate notifications. Is there an idempotency key (e.g., notification ID) that the client can deduplicate?
- **At-least-once delivery semantics:** Redis Pub/Sub is fire-and-forget. If a subscriber is slow, it may miss messages. The spec does not clarify whether at-least-once or at-most-once delivery is acceptable.

---

## 3. Security

### 3.1 [HIGH] No authentication for WebSocket connections

The spec does not mention how the Fanout Service authenticates WebSocket connections:

- **Connection auth:** How does the Fanout Service know which user owns a given WebSocket connection? Does the client send a token in the URL query string? In an HTTP upgrade header? In the first message after the connection opens?
- **Token validation:** If the token is in the URL, it may be logged in server access logs, browser history, or proxy logs. If the token is in a header, it must be sent during the HTTP upgrade handshake.
- **Token expiration:** What happens when the user's auth token expires? Does the Fanout Service refresh the token? Does it close the connection?
- **Cross-site WebSocket hijacking (CSWSH):** Without proper CSRF protection on the WebSocket upgrade request, an attacker could open a WebSocket connection to the Fanout Service on behalf of an authenticated user, receiving their notifications.

### 3.2 [HIGH] No authorization / access control

- **Channel name injection:** The channel name is `notifications:<user_id>`. If the originating service accepts a `user_id` from an untrusted source, an attacker could publish to `notifications:admin` or `notifications:1` and inject fake notifications. Is `user_id` validated server-side?
- **Notification content validation:** The spec does not mention sanitizing notification content. If a notification contains user-generated content (e.g., "User X mentioned you in: [message]"), is it sanitized to prevent XSS when rendered by the client?

### 3.3 [MEDIUM] No rate limiting on WebSocket connections

- **Per-user connection limit:** Can a user open 10,000 WebSocket connections and exhaust server resources? Is there a per-user connection limit?
- **Per-IP rate limiting:** Can an attacker open many connections from a single IP to exhaust Fanout Service resources?
- **Connection timeout:** Are idle WebSocket connections terminated after a period of inactivity? This prevents resource leaks from abandoned connections.

### 3.4 [MEDIUM] No TLS / encryption specification

- **WebSocket security:** The spec does not mention whether WebSocket connections use `wss://` (TLS-encrypted) or `ws://` (plaintext). In production, WebSockets MUST use TLS to prevent eavesdropping on notification content.
- **Certificate management:** Who manages TLS certificates for the Fanout Service? How are they rotated?

### 3.5 [MEDIUM] No DDoS / abuse protection

- **Connection exhaustion:** An attacker could open many WebSocket connections to exhaust server memory/file descriptors. Is there a global connection limit?
- **Notification flooding:** An attacker could trigger many notification events for a target user, causing the Fanout Service to push a flood of messages. Is there a per-user notification rate limit?

---

## 4. Data & Consistency

### 4.1 [HIGH] No notification deduplication between WebSocket and polling

The spec says "we keep writing to the notifications table so history still works, and we drop the 30-second polling." But during the transition:

- **Double delivery risk:** If a notification is written to the DB and pushed via WebSocket, and the client also polls, the client may see the same notification twice (once via WebSocket, once via polling). The spec does not address how the client distinguishes "new via WebSocket" from "already seen via polling."
- **Polling retirement timing:** "Drop the 30-second polling" is a client-side change. If some clients still poll (old versions, feature flag not enabled), how does the backend handle both?

### 4.2 [MEDIUM] No notification history sync on reconnect

- **Gap filling:** If the WebSocket drops for 5 minutes, the client misses those notifications. The spec says the DB has the data, but does not describe how the client fetches the gap. Does the client need a separate API call? Does the Fanout Service buffer messages?
- **Read receipts:** If the client receives a notification via WebSocket but the user never opens the app, the notification is "delivered" but not "read." How is read status tracked?

### 4.3 [MEDIUM] No notification batching or coalescing

- **Burst notifications:** If user A mentions user B 10 times in 1 second, the Fanout Service pushes 10 WebSocket messages. This is wasteful and jarring for the user. Should notifications be batched (e.g., "You were mentioned 10 times")?
- **Coalescing strategy:** The spec does not mention any batching, throttling, or coalescing of rapid notifications.

---

## 5. Scalability & Performance

### 5.1 [HIGH] No capacity planning

- **Connection count:** How many concurrent users? How many WebSocket connections per instance? With 3 instances, what is the max concurrent connections? WebSocket connections consume memory (buffer, TLS state, file descriptor). If you have 1M active users, 3 instances is almost certainly not enough.
- **Redis Pub/Sub scaling:** Redis Pub/Sub replicates every message to every subscriber. If you have 3 Fanout Service instances and 1M users, each instance subscribes to 1M channels. Redis can handle this, but it is a non-trivial memory footprint.
- **Channel count:** `notifications:<user_id>` means one channel per user. With 1M users, that is 1M channels. Redis handles this, but it is worth noting.

### 5.2 [MEDIUM] No latency budget or SLO

- **Latency claim:** "Expected latency: sub-second delivery" is stated but not backed by any analysis. What is the p50, p95, p99 latency? What are the components of latency (event publish -> Redis -> Fanout Service -> WebSocket -> client)?
- **SLO/SLA:** What is the target availability for the notification system? 99.9%? 99.99%?

### 5.3 [MEDIUM] No monitoring, alerting, or observability

- **Metrics:** The spec does not mention any metrics: connection count, message throughput, delivery latency, error rate, reconnection rate, Redis latency.
- **Alerting:** What alerts are configured? (e.g., "Fanout Service instance down," "Redis latency > 100ms," "WebSocket connection error rate > 1%")
- **Distributed tracing:** If a notification takes 5 seconds to arrive, how do you debug whether the delay was in the originating service, Redis, the Fanout Service, the network, or the client?
- **Logging:** What is logged? Connection open/close, errors, reconnections?

### 5.4 [MEDIUM] No database impact analysis

- **Write amplification:** The spec says "we keep writing to the notifications table." This means every notification is written twice: once to the DB (existing path) and once via Redis Pub/Sub. Is there any concern about write amplification?
- **DB polling reduction claim:** The spec claims polling is "now ~40% of read traffic at peak" and will be dropped. But if the Fanout Service fails, does polling remain as a fallback? If not, this is a reliability regression.

---

## 6. Operational Concerns

### 6.1 [HIGH] No deployment strategy

- **Blue/green or rolling deployment:** How are Fanout Service instances updated without dropping all WebSocket connections?
- **Database migration:** The spec says "No schema changes," which is good, but the Fanout Service needs Redis access. How is Redis configured for the new service?
- **Configuration management:** What configuration does each Fanout Service instance need? (Redis URL, port, TLS settings, rate limits, etc.)

### 6.2 [MEDIUM] No runbook / operational procedures

- **Incident response:** If the Fanout Service starts delivering duplicate notifications, what is the runbook? If Redis goes down, what is the escalation path?
- **Scaling:** How do you add more Fanout Service instances? How do you remove them?
- **Disaster recovery:** If the entire Fanout Service deployment is lost, how quickly can it be restored?

### 6.3 [MEDIUM] No cost analysis

- **Infrastructure cost:** 3 Fanout Service instances (what size?), Redis (what tier?), load balancer (what type?). What is the monthly cost?
- **Comparison to current cost:** The current polling approach uses ~40% of DB read traffic. Is the cost of the new architecture lower, higher, or the same?

---

## 7. Client-Side Gaps

### 7.1 [HIGH] No client-side WebSocket lifecycle management

- **Reconnection:** The spec does not describe client-side reconnection logic. A robust client needs exponential backoff with jitter, connection state management, and notification gap detection.
- **UI state management:** When a notification arrives via WebSocket, how does the client update the UI? Is there a notification badge? A toast? Does the client need to fetch the full notification detail from the API?
- **Background mode:** What happens when the app goes to the background (mobile) or the browser tab is minimized? Should the WebSocket stay open? Should push notifications be used instead?

### 7.2 [MEDIUM] No offline / disconnected UX

- **Offline notifications:** If the user is offline (no network), notifications are not delivered. Does the client cache them locally? Does the client use a push notification service (FCM/APNs) as a fallback?
- **Notification center:** The spec does not describe the UI for a notification center / inbox. Is there a list of past notifications? A badge count?

---

## 8. Open Questions from the Spec (and Their Problems)

The spec lists only one open question: "What WebSocket library should we use?"

This is a trivial question compared to the many critical unanswered questions. The following should have been open questions:

1. How is WebSocket connection ownership determined across multiple Fanout Service instances?
2. How are duplicate notifications prevented when all instances receive all pub/sub messages?
3. How does the Fanout Service authenticate WebSocket connections?
4. What is the fallback if Redis is unavailable?
5. How are missed notifications recovered after a WebSocket disconnection?
6. What is the connection capacity per instance and total?
7. How are WebSocket connections upgraded through the load balancer?
8. Is there a feature flag for gradual rollout?
9. What are the latency SLOs (p50, p95, p99)?
10. What metrics and alerts are configured?
11. How are notifications batched or coalesced during bursts?
12. What is the TLS / encryption strategy?
13. How is the Fanout Service monitored and alerted?
14. What is the rollback plan if the Fanout Service causes issues?

---

## 9. Missing Non-Functional Requirements

The spec does not address any of the following:

- **Availability target** (e.g., 99.9%)
- **Latency targets** (p50, p95, p99)
- **Data durability** (are notifications lost if Fanout Service crashes?)
- **Privacy** (notification content may be sensitive; is it encrypted in transit?)
- **Compliance** (are there regulatory requirements for notification delivery?)
- **Accessibility** (how are real-time notifications announced to screen readers?)
- **Internationalization** (notification content in multiple languages?)
- **Testing strategy** (how is this tested? Load testing? Chaos testing? Integration testing?)
- **Documentation** (API docs, runbook, architecture diagram?)

---

## 10. Risk Summary

| # | Risk | Severity | Likelihood |
|---|------|----------|------------|
| 1.1 | No routing strategy for multi-instance fanout | HIGH | Certain |
| 1.3 | No reconnection / session recovery | HIGH | Certain |
| 1.4 | No phased rollout / rollback plan | HIGH | Certain |
| 2.1 | Redis outage stops all real-time delivery | HIGH | Likely |
| 2.2 | No crash recovery for Fanout Service | HIGH | Likely |
| 3.1 | No WebSocket authentication | HIGH | Certain |
| 3.2 | No channel name injection protection | HIGH | Likely |
| 4.1 | Double delivery during transition | HIGH | Certain |
| 5.1 | No capacity planning | HIGH | Likely |
| 6.1 | No deployment strategy | HIGH | Certain |
| 1.5 | LB does not support WebSocket upgrade | MEDIUM | Certain |
| 2.3 | No backpressure or ordering guarantee | MEDIUM | Likely |
| 2.4 | No idempotency for delivery | MEDIUM | Likely |
| 3.3 | No connection rate limiting | MEDIUM | Likely |
| 3.4 | No TLS specified | MEDIUM | Certain |
| 3.5 | No DDoS protection | MEDIUM | Likely |
| 4.2 | No gap-filling on reconnect | MEDIUM | Likely |
| 4.3 | No notification batching | MEDIUM | Likely |
| 5.3 | No monitoring or alerting | MEDIUM | Certain |
| 6.2 | No runbook | MEDIUM | Certain |
| 6.3 | No cost analysis | MEDIUM | Certain |
| 7.1 | No client-side WebSocket lifecycle | HIGH | Certain |
| 7.2 | No offline UX | MEDIUM | Likely |

---

## 11. Recommendations

1. **Define the multi-instance architecture first.** Before writing any code, decide on connection ownership (consistent hash, Redis directory, or sticky sessions) and deduplication strategy. This is the single biggest architectural gap.

2. **Add authentication to WebSocket connections.** Use a signed JWT or session token passed during the HTTP upgrade handshake. Validate it before accepting the connection.

3. **Plan for Redis failure.** Either use a managed Redis with HA, or implement a fallback path (e.g., re-enable polling when Redis is unreachable).

4. **Implement a feature flag for gradual rollout.** Start with 1% of users, monitor metrics, then increase. Have a one-click rollback to polling.

5. **Add comprehensive monitoring.** Connection count, message throughput, delivery latency, error rates, Redis latency, reconnection rate. Set up alerts for anomalies.

6. **Define client-side reconnection logic.** Exponential backoff with jitter, gap detection, and notification recovery from the API.

7. **Use TLS (wss://) for all WebSocket connections.** This is non-negotiable for production.

8. **Add notification batching/coalescing.** If a user receives 10 mentions in 1 second, show "You were mentioned 10 times" rather than 10 separate notifications.

9. **Write a runbook.** Document incident response procedures, scaling procedures, and deployment procedures.

10. **Conduct a load test before launch.** Verify that 3 instances can handle the expected concurrent connection count and message throughput.

---

## 12. Verdict

**Do not approve for implementation in current form.**

The spec identifies a real problem (polling load and latency) and proposes a reasonable direction (WebSocket fanout via Redis Pub/Sub). However, it omits the critical architectural decisions around multi-instance routing, authentication, failure handling, and rollout strategy. These are not "open questions" -- they are fundamental design requirements that must be resolved before any implementation begins.

The spec should be revised to address items 1.1, 1.3, 1.4, 2.1, 2.2, 3.1, 3.2, 4.1, 5.1, 6.1, and 7.1 at minimum before being resubmitted for review.