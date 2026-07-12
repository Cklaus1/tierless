# Technical Review: Real-Time Notification Fanout

**Status:** NOT APPROVED -- major gaps and risks require resolution before implementation.

## Summary

This design proposes replacing 30-second polling with a WebSocket-based fanout service backed by Redis Pub/Sub. The core idea is sound, but the spec is extremely thin -- it covers roughly 20% of what needs to be designed. Several critical gaps around reliability, scaling, failure modes, and client behavior would cause production incidents if implemented as described.

## Critical Issues

### 1. Redis Pub/Sub is fire-and-forget with no delivery guarantees

Redis Pub/Sub drops messages to subscribers that are not connected at publish time. The spec says "Redis holds only transient pub/sub messages (not persisted)." This means:

- If a Fanout Service instance restarts, any messages published during the restart window are lost forever. Users miss notifications.
- If a user's WebSocket reconnects to a different Fanout Service instance (which is likely with 3 instances behind a load balancer), the new instance has no knowledge of the user's last-seen notification state. There is no reconciliation mechanism.
- If the Fanout Service is slow to process a message (GC pause, backpressure), the WebSocket send may block. There is no queue or buffer.

**Recommendation:** Either use Redis Streams (which provides persistence and consumer groups) or maintain a per-user cursor in the `notifications` table that the client sends on reconnect so the Fanout Service can catch up.

### 2. No reconnection and state reconciliation strategy

The spec says "the client opens a WebSocket on app load." It does not address:

- What happens when the WebSocket disconnects (network blip, browser tab switch, server restart)?
- Does the client fall back to polling during disconnection? If so, for how long?
- When the WebSocket reconnects, how does the client know which notifications it missed?
- Can the client deduplicate notifications that were delivered over WebSocket but also returned by a polling fallback?

Without a reconnection strategy, any transient disconnect causes a silent loss of notifications.

### 3. Load balancer routing is underspecified

"3 instances behind a load balancer" is not enough detail. WebSockets are long-lived connections -- the load balancer must support sticky sessions (connection affinity). If it does not, every reconnection could land on a different instance, and that instance will not be subscribed to the user's Redis channel.

The spec does not mention:
- Which load balancer (nginx, ALB, Traefik)?
- Sticky session configuration.
- WebSocket upgrade header handling.
- Connection timeout / idle timeout settings.

### 4. Fanout Service does not scale linearly with user count

Each online user requires one WebSocket connection AND one Redis Pub/Sub subscription. At 100,000 concurrent users, that is 100,000 Redis subscriptions per Fanout Service instance (assuming even distribution across 3 instances, ~33,000 each). Redis Pub/Sub subscriptions are lightweight but:

- Each subscription consumes memory in Redis.
- Publishing to `notifications:<user_id>` means N separate channels for N users. Redis Pub/Sub does not fan out from a single channel -- each user gets their own channel. This is fine for moderate scale but becomes a concern at very high user counts.
- If a single event (e.g., a system alert) needs to notify all users, the originating service would need to publish to N channels. The spec does not address broadcast notifications.

**Recommendation:** Benchmark the Fanout Service and Redis at expected peak concurrency. Consider a hybrid approach where system-wide alerts use a broadcast channel while per-user notifications use per-user channels.

### 5. No authentication or authorization for WebSocket connections

The spec does not mention how the Fanout Service authenticates WebSocket connections. Without authentication:

- Any client can connect and subscribe to any user's channel.
- There is no way to enforce that user A cannot receive user B's notifications.

**Recommendation:** Require a short-lived token (JWT or session cookie) in the WebSocket handshake URL or as the first message. Validate it before establishing the subscription.

### 6. No backpressure or message rate limiting

If a user generates notifications at a high rate (e.g., a bot mentioning them 1000 times per minute), the Fanout Service will push all 1000 messages over the WebSocket in rapid succession. The client has no way to throttle this.

**Recommendation:** The Fanout Service should batch or coalesce notifications per user, or the client should implement a notification queue with rate limiting.

## Significant Gaps

### 7. No monitoring, metrics, or alerting

The spec does not mention:
- How to measure end-to-end notification latency.
- How to track WebSocket connection counts per instance.
- How to detect when the Fanout Service is falling behind.
- What the alerting strategy is for service degradation.

### 8. No graceful degradation path

The rollout plan says "switch the client to WebSockets ... and turn off polling." This is a hard cutover with no:
- Feature flag to toggle between polling and WebSockets.
- A/B test or gradual rollout plan.
- Rollback plan if WebSockets cause issues.

If the Fanout Service has a bug that causes notification loss, there is no way to fall back to polling without a client redeployment.

### 9. No handling of offline users

The spec does not address what happens when a user is offline:
- Notifications are written to the `notifications` table (good), but is there a mechanism to surface them when the user comes back online?
- Does the WebSocket connection trigger a "you have N missed notifications" payload on reconnect?

### 10. No security considerations beyond authentication

- Is the WebSocket connection over WSS (secure) or WS (insecure)? The spec does not specify.
- Are there rate limits on the number of WebSocket connections per user?
- Is there protection against WebSocket-based DoS (e.g., a user opening 100 connections)?

### 11. No discussion of the originating service changes

The spec says "the originating service publishes a message to a new Redis Pub/Sub channel." This implies changes to every service that creates notifications (messaging, mentions, follows, system alerts). The spec does not address:

- How the originating service gets the target user's ID to construct the channel name.
- What happens if the Redis publish fails? Is it retried? Logged?
- Is the Redis publish synchronous or fire-and-forget from the originating service's perspective?

### 12. No client-side implementation details

The spec mentions "the client opens a WebSocket" but does not cover:
- Which framework/library handles the WebSocket on the client?
- How are notifications rendered when they arrive?
- How does the client handle the case where the WebSocket is unavailable (e.g., older browsers, enterprise proxies)?
- What is the fallback behavior?

## Minor Issues

### 13. "Why WebSockets" section is thin

The section only says WebSockets are "widely supported in browsers." It does not compare WebSockets to alternatives like Server-Sent Events (SSE), which would be simpler for a unidirectional push model and handle reconnection natively. For a notification-only use case (server-to-client only), SSE might be a better fit.

### 14. Open questions are incomplete

The only open question is "What WebSocket library should we use?" This is a trivial implementation detail. The real open questions (listed above as critical issues) are not even identified.

## Verdict

**Do not proceed as-is.** The core architecture (Fanout Service + Redis Pub/Sub + WebSocket) is reasonable for the problem domain. However, the spec needs significant expansion before implementation can begin. The highest-priority items to resolve are:

1. Delivery guarantees and reconnection strategy (critical)
2. Authentication for WebSocket connections (critical)
3. Load balancer sticky sessions and configuration (critical)
4. Graceful degradation / feature flag strategy (significant)
5. Monitoring and observability (significant)

A revised spec should be at least 3-5 pages, covering failure modes, scaling assumptions, and the full lifecycle of a notification from creation to client rendering.