# GRADER checklist — the 15 design flaws in spec.md (from the three-way diff)

Score each review: does it raise this flaw SUBSTANTIVELY (✓=1), partially/weakly (~=0.5),
or miss it (✗=0)? A flaw counts as raised only if the review names the actual problem, not
just an adjacent open question.

1. Redis Pub/Sub fire-and-forget; no missed-message recovery (esp. after dropping polling)
2. Reconnect + catch-up cursor + heartbeats/backoff
3. Dual-write DB-commit vs. Redis-publish ordering/consistency (both failure directions)
4. WebSocket auth/authz — derive user from session, never client-supplied channel
5. Redis scaling: per-user subscriptions + Cluster/sharded pub/sub (SSUBSCRIBE)
6. Redis is a SPOF — HA / failover / degraded mode
7. LB WebSocket config (idle timeout); is the sticky-session claim right? (sticky NOT actually required)
8. Thundering herd / reconnect storm on deploy (backoff + jitter)
9. Fallback transport for proxy/firewall-blocked WebSockets (or SSE)
10. Rollout: feature flag / staged / rollback
11. Old un-upgraded clients keep polling (client fleet is non-atomic)
12. Mobile background delivery needs APNs/FCM (a WS delivers nothing to a backgrounded app)
13. Multi-device / per-device connection counting (not "one per user")
14. Read/unread state sync across devices (badge divergence)
15. Broadcast / system-alert fanout to all users (publish to N per-user channels)

Reference tiers (from the diff, for calibration — do NOT reveal to the grader if grading blind):
- Haiku bare ~ 6 full + partials
- Opus ~ 11
- Fable ~ 14 (misses only #15)
