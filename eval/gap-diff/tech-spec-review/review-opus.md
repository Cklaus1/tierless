# Technical Review: Real-Time Notification Fanout

**Reviewer:** opus · **Verdict:** Right problem, roughly right shape, but not ready to build. The core WebSocket-push idea is sound; the delivery-guarantee story, reconnect/catch-up flow, and Redis Pub/Sub scaling model are the parts that will cause outages and lost notifications as written.

---

## Summary

The spec correctly identifies that polling is the problem (latency + ~40% of peak read load) and that server push is the fix. WebSockets are a reasonable transport choice. However, the design treats the hard parts of a fanout system — reliable delivery, reconnection, backpressure, scale limits, and failure behavior — as either solved or unmentioned. The single "open question" (which WS library) is by far the least important decision here.

Below: blocking issues first, then risks, then gaps, then smaller notes and concrete recommendations.

---

## Blocking issues (must resolve before build)

### 1. Redis Pub/Sub is fire-and-forget — this design silently drops notifications
Redis Pub/Sub delivers a message only to subscribers **connected at that instant**. There is no persistence, no replay, no ack. This breaks the design in several ordinary situations:

- **User briefly disconnected** (tab sleep, network blip, mobile handoff, deploy): any notification published during the gap is gone from the real-time path.
- **Publish/subscribe race:** the publisher sends to `notifications:<user_id>` the moment the event occurs. If the user's socket isn't subscribed yet (mid-connect, mid-reconnect), the message evaporates.
- **Fanout instance restart/crash:** every message in flight for that instance's users is lost.

The spec says "we keep writing to the `notifications` table so history still works" — but it also **removes the 30s poll entirely** and describes no sync-on-connect step. So the DB row exists, but nothing tells the client to go read it until the *next* real-time event happens to arrive. In practice users will miss notifications and only notice inconsistently. This is the single most important flaw.

**Fix:** Treat the WebSocket as a *low-latency hint*, and the DB as the source of truth. On (re)connect, the client must fetch everything since its last-seen notification id/cursor (a "catch-up" query). Push messages should carry a monotonic id/cursor so the client can detect gaps and reconcile. Consider a lightweight per-user "since" endpoint (or reuse `GET /notifications?since=`) — this also lets you keep a rare, cheap poll as a safety net rather than 30s hammering.

### 2. No reconnection / offline / catch-up design at all
Real-time systems live or die on reconnect behavior, and it is entirely absent. Needed:
- Client reconnect with backoff + jitter (see thundering-herd note below).
- A cursor/last-seen mechanism so reconnect fetches the gap.
- Defined behavior for messages that arrive while offline.
- Heartbeats/ping-pong to detect dead connections (WS half-open connections are common and invisible without app-level pings).

### 3. Ordering of DB write vs. publish is unspecified — history and real-time can disagree
If the originating service publishes to Redis *before* the row is committed, the client may receive a push for a notification that isn't yet queryable (catch-up fetch misses it, or a click 404s). If it publishes *after* commit, ordering is safer but you can still crash between the two and drop the push (acceptable, since catch-up covers it). This ordering needs to be stated explicitly: **commit first, then publish, and rely on catch-up for the publish-failure case.** Otherwise you get transient inconsistencies that are miserable to debug.

---

## Significant risks

### 4. Redis Pub/Sub scaling model — one subscription per online user
Each fanout instance must subscribe to `notifications:<user_id>` for every user it holds. That is potentially hundreds of thousands of channel subscriptions fanned across instances, and every publish is matched against the subscription set. Two concrete problems:

- **Redis Cluster incompatibility:** classic `SUBSCRIBE`/`PUBLISH` does **not** shard across a Redis Cluster — a publish must reach the node the subscriber is on. At scale you either run a single non-clustered Redis (a capacity ceiling and SPOF) or move to **sharded pub/sub** (`SSUBSCRIBE`, Redis 7+) and key the channel by a shard slot. The spec assumes a single Redis and doesn't say so.
- **Per-user channel churn:** subscribe/unsubscribe on every connect/disconnect is a lot of control-plane traffic. A common alternative is a fixed set of shard channels (`notifications:shard:<hash(user_id) % N>`) that each instance subscribes to once, then routes internally. Worth evaluating against per-user channels.

### 5. Redis is now a single point of failure with no HA story
Notifications' real-time path depends entirely on one Redis. No mention of replication, failover (Sentinel/managed HA), or what happens to delivery during a Redis blip. If Redis is down, does the app degrade to polling, or do notifications just stop being real-time silently? Define the degraded mode.

### 6. "3 instances behind a load balancer for redundancy" — redundancy of what?
WebSocket connections are **stateful and pinned** to one instance. If an instance dies, all its users drop and must reconnect (to be spread across the survivors). That is failover, not seamless redundancy — and it needs:
- **LB configured for WebSockets** (long-lived upgrades, generous idle timeouts, sticky/consistent routing). A default HTTP LB with a 60s idle timeout will kill idle sockets.
- A plan for **connection capacity**: 3 instances is a fixed number, not derived from expected concurrent-connection count, per-instance FD/memory limits, or headroom to absorb one instance failing (N+1). Where did 3 come from?

### 7. Thundering herd on deploy/restart
Every fanout deploy drops all connections; all clients reconnect at once, re-subscribe in Redis, and fire catch-up queries simultaneously — a load spike on Redis, the LB, and the DB precisely when the system is already churning. Needs reconnect backoff **with jitter**, and ideally staggered/rolling deploys with connection draining.

### 8. Authentication and authorization of the socket
Nothing about how the WS is authenticated. Critical because the channel is `notifications:<user_id>`: the server must derive `user_id` from an authenticated session/token at connect time and subscribe the user only to **their own** channel. If the client can influence which channel it subscribes to, that's a cross-user notification leak. Also address token expiry on long-lived connections (re-auth or forced reconnect).

---

## Gaps / unaddressed

- **Fallback path:** if WS fails to connect (corporate proxies, blocked upgrades, flaky mobile), there is no fallback. Removing polling entirely leaves those users with *no* notifications. Keep a low-frequency poll or SSE/long-poll fallback.
- **Backpressure / slow consumers:** if a client is slow or a user gets a burst, per-connection send buffers grow and can OOM the instance. Need per-connection buffering limits and a drop/coalesce policy (notifications can often be coalesced to "you have N new").
- **Deduplication / idempotency:** at-least-once from the catch-up + push combination means the same notification can arrive twice (once via push, once via catch-up). Client needs to dedupe by id. State this.
- **Observability:** no metrics named. You'll want concurrent connections, connect/disconnect rate, publish→deliver latency, dropped-message counts, Redis subscription counts, catch-up query volume. Without these the "sub-second" claim is unverifiable and regressions are invisible.
- **Presence definition:** "online user" is used loosely. A user can have multiple devices/tabs = multiple sockets to the same `user_id` across instances. Publish must reach *all* of them (fine with pub/sub broadcast, but the per-user-subscription model needs each instance holding any of that user's sockets to be subscribed — confirm this is intended).
- **Load reduction claim:** the goal was to cut the ~40% DB read load. Catch-up-on-connect + a safety poll partially re-introduce reads. Net reduction should be estimated, not assumed — it's still a big win vs. 30s polling, but quantify it.
- **Rollout safety:** "switch the client to WebSockets and turn off polling" is described as one step. This should be feature-flagged and staged: ship WS alongside polling, ramp a percentage, confirm delivery parity via metrics, *then* retire polling. No rollback plan is given.
- **Message payload/schema:** the shape of the pushed message, its size limits, and whether it carries the full notification or just an id (client then fetches) are unspecified. "Push an id, client fetches" sidesteps the write-vs-publish race and payload-bloat concerns and is worth considering.

---

## Smaller notes

- The lone open question ("what WS library?") is a minor implementation detail relative to everything above. On Node, `ws` (raw) or a higher-level lib like Socket.IO (built-in reconnect/fallback, at the cost of a protocol) are the usual picks — but choose it *after* the delivery/reconnect model is settled.
- "WebSockets are widely supported" is true but glosses over the proxy/firewall reality that motivates a fallback.
- Consider whether **Server-Sent Events** meet the requirement. Notifications are server→client only; SSE is one-directional, rides plain HTTP (friendlier to proxies/LBs), and has built-in reconnect with `Last-Event-ID` — which directly solves the catch-up problem this spec is missing. WebSockets are justified if you need client→server on the same channel; if not, SSE is a lower-risk fit and the doc should say why it was rejected.

---

## Recommended changes before building

1. **Make the DB the source of truth; make push a hint.** Add an explicit connect-time catch-up using a per-user cursor/last-seen id. Every push carries that id.
2. **Design reconnect fully:** backoff + jitter, heartbeats/ping-pong, resubscribe, gap fetch.
3. **Pin down write-then-publish ordering** and accept at-least-once + client dedupe by id.
4. **Decide the Redis scaling & HA model:** single vs. sharded pub/sub, per-user vs. shard channels, replication/failover, and the degraded mode when Redis is unavailable.
5. **Specify LB/WS requirements** (upgrade support, idle timeouts, capacity math for N+1), and connection-capacity budget behind the "3 instances" number.
6. **Auth the socket server-side**, derive `user_id` from the session, never trust a client-supplied channel.
7. **Keep a fallback** (low-freq poll or SSE) and **stage the rollout** behind a flag with a rollback path; only retire polling after parity is proven in metrics.
8. **Add observability** for connections, delivery latency, and drops.
9. **Re-evaluate SSE vs. WebSockets** explicitly given the requirement is one-directional push.

None of this changes the fundamental architecture — event → broker → per-user push, with DB for history is the right skeleton. The work is turning "publish to Redis and push" into a system that survives disconnects, restarts, and scale, and that never silently loses a notification.
