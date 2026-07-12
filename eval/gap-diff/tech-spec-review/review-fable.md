# Technical Review: Real-Time Notification Fanout

**Reviewer:** Fable (automated review) · **Date:** 2026-07-11 · **Doc reviewed:** `spec.md`

## Verdict

The overall direction — push delivery over a persistent connection, backed by the existing
`notifications` table as the source of truth — is reasonable and matches the stated goals
(sub-second delivery, kill the polling load). However, the design as written is **not ready to
build**. It treats Redis Pub/Sub as a reliable delivery mechanism (it is not), drops polling
without any catch-up or fallback path, has no reconnection/missed-message story, no auth story
for the WebSocket, no rollout phasing, and hand-waves the operationally hardest parts
(connection lifecycle, Redis HA, deploys of a stateful connection tier). Each of these is a
correctness or availability problem, not a polish item.

Below: what's sound, then issues ordered by severity, then concrete recommendations.

---

## What's sound

- Keeping the `notifications` table as the durable record and treating the real-time channel
  as a delivery optimization is the right architecture. Do not let this drift — the design
  must be written so that losing any pub/sub message is *recoverable*, not fatal.
- Removing 30-second polling that accounts for ~40% of peak read traffic is a well-motivated,
  measurable goal.
- Per-user channels (`notifications:<user_id>`) keep routing logic simple, and subscriptions
  naturally follow the connection regardless of which instance a user lands on, so no sticky
  sessions are required. That part composes correctly with the 3-instance LB setup.

---

## Critical issues (must fix before build)

### 1. Redis Pub/Sub is fire-and-forget; the design has no missed-message recovery

Redis Pub/Sub provides **at-most-once, online-only** delivery. Messages are dropped, silently,
whenever:

- the user is offline or the app is backgrounded/closed;
- the WebSocket is mid-reconnect (network blip, laptop lid, mobile handoff);
- a message is published in the race window between the client's WS connect and the fanout
  instance completing its Redis `SUBSCRIBE` for that user;
- a fanout instance crashes or is deployed (all its subscriptions vanish);
- Redis itself restarts or fails over (all subscriptions are lost cluster-wide, and messages
  published during the failover window are gone).

The spec simultaneously **removes polling**, leaving no mechanism by which a client ever
learns about a notification it didn't receive live. The result: notifications that are in the
database but never shown until the user happens to reload and the client refetches history —
which is strictly worse than today's 30-second polling for reliability.

**Required change:** make the client fetch missed notifications from `GET /notifications`
(with a `since` cursor / last-seen notification ID) on every WS connect *and* reconnect, and
treat the WS purely as a "something new happened" hint layered on top of a durable cursor.
Equivalently: the socket can even deliver just a "ping, resync" signal rather than the payload.
Once you do this, at-most-once pub/sub becomes acceptable. Without it, the design is broken.

### 2. Dual-write inconsistency between the DB and Redis

The originating service both writes the `notifications` row and publishes to Redis. These are
two systems with no transaction across them:

- Publish succeeds but the DB write fails/rolls back → user sees a ghost notification with no
  backing record.
- DB write succeeds but the publish fails (Redis down, network) → notification silently
  invisible until the next full reload, because polling is gone.

**Required change:** publish only after the DB commit (accepting a lost publish as the failure
mode, recovered by the reconnect-resync in issue 1), or use an outbox/CDC pattern if stronger
guarantees are wanted. Also standardize *where* the publish happens — if every originating
service publishes independently, the envelope format, error handling, and metrics will diverge.
A small shared library or a single "notification writer" service/queue is worth specifying.

### 3. No authentication or authorization on the WebSocket

The spec never says how the Fanout Service knows who the connecting user is, or what stops
user A from receiving user B's channel. This is a security hole, not an open question.

**Required change:** specify auth at the WS handshake (short-lived token passed at upgrade
time — note browsers cannot set arbitrary headers on WS, so use a query param token or a
cookie), validate it server-side, and derive the subscribed channel *only* from the
authenticated identity — never from a client-supplied user ID. Also specify: WSS only, Origin
checking, token expiry/refresh behavior for long-lived connections, and per-IP/per-user
connection limits.

### 4. Rollout plan will break existing clients and has no rollback

"Deploy the service, switch the client in the next app release, and turn off polling" ignores
that client releases are not atomic — old app versions (especially mobile) will keep polling
for weeks or months. Turning off polling breaks them. There is also no feature flag, no
staged rollout, no dual-running period, and no rollback plan if the Fanout Service melts down
at peak.

**Required change:** phase it — (a) ship the service and connect a small % of clients via
flag while polling continues everywhere; (b) for flagged clients, lengthen the poll interval
rather than removing it (a slow poll doubles as the reliability backstop and the fallback for
networks where WebSockets don't work — see issue 5); (c) ramp; (d) only deprecate the fast
polling path once adoption metrics say so. Keep the polling endpoint indefinitely — issue 1
requires it anyway for resync.

---

## Major issues (design gaps that will bite in production)

### 5. No fallback transport, and no reconnection strategy

WebSockets fail on a nontrivial fraction of real networks (corporate proxies, some captive
portals, aggressive middleboxes). The spec has no fallback and no reconnect policy. With three
instances, a single deploy or crash disconnects ~1/3 of all online users simultaneously; if
they all reconnect immediately, you get a reconnect storm against the survivors and against
the resync endpoint (issue 1).

Specify: exponential backoff with jitter on the client; connection draining and slow-rolling
deploys on the server; heartbeat/ping-pong (both to detect dead peers and to keep LB idle
timeouts from silently killing connections — confirm the LB's WebSocket and idle-timeout
support explicitly); and a degraded mode (fall back to slow polling) when the socket can't be
established after N attempts.

### 6. "One connection per online user" is wrong — it's per device/tab

A user with the app open in three tabs and on a phone has four connections. The design should
say connections are per-client, all subscribed to the same user channel (this actually works
fine with Pub/Sub), and capacity planning must count *connections*, not users. Related gap:
nothing about read/unread state — if the badge count is computed client-side from pushed
events, devices will disagree. Read-state sync (e.g., a "read" event also published on the
user channel, plus authoritative counts from the API) should be in scope or explicitly
deferred.

### 7. No capacity or Redis-topology analysis

- How many concurrent connections at peak? Node.js can hold many idle sockets per instance,
  but 3 instances is a guess, not a sizing. State the target (e.g., 50k conns/instance),
  memory per connection, and file-descriptor/ulimit settings.
- Per-user `SUBSCRIBE`/`UNSUBSCRIBE` churn on every connect/disconnect is fine at moderate
  scale on a single Redis, but the doc should state expected subscription counts and churn
  rate. Note that classic Pub/Sub on **Redis Cluster** broadcasts every publish to every node
  — if Redis Cluster is in the picture, use sharded pub/sub (`SSUBSCRIBE`) or a single
  dedicated non-clustered Redis for this.
- Redis is a single point of failure here and Pub/Sub state does not survive failover.
  Acceptable *only* because of the resync mechanism from issue 1 — say so, and specify the
  fanout service's behavior on Redis disconnect (resubscribe all local users, then tell
  clients to resync).
- An alternative worth one paragraph: each instance subscribes to a handful of *sharded*
  channels (or one firehose) and routes locally to its connected users. This trades
  subscription churn for filtering work and can be simpler operationally.

### 8. Mobile is unaddressed

A WebSocket does not deliver to a backgrounded or killed mobile app. If "instant
notifications" includes mobile, APNs/FCM push is a separate, necessary track; if this design
is web/foreground-only, the doc should say so explicitly, because stakeholders will read
"notifications feel instant" as including phones.

---

## Minor issues

- **No observability plan.** Minimum: connection count per instance, connect/disconnect and
  reconnect rates, publish→deliver latency (attach a publish timestamp to the envelope),
  Redis pub/sub delivery errors, dropped/undeliverable message counts, and an end-to-end
  synthetic probe. Also define the success metric ("sub-second delivery" — at which
  percentile? p50 or p99?), and the DB-load reduction target so the project can be judged.
- **No message envelope/versioning.** Define the JSON schema for the pushed message now
  (type, id, created_at, payload, schema version). Multiple producer services will otherwise
  each invent one.
- **Idempotency/ordering.** Clients should dedupe by notification ID (reconnect + resync will
  produce duplicates by design) and not assume ordering across the WS and REST paths.
- **Backpressure.** A slow client on a large fanout burst can balloon the per-socket send
  buffer; specify a max buffered bytes per connection and a disconnect-and-resync policy when
  exceeded.
- **Alternatives are not seriously considered.** The "Why WebSockets" section argues against
  polling, not against the real alternatives. Server-Sent Events deserve a paragraph: this
  traffic is strictly server→client, SSE works over plain HTTP (fewer proxy problems), and
  `Last-Event-ID` gives reconnect-resume semantics almost for free — it arguably fits this
  problem *better* than WebSockets unless bidirectional traffic is planned. Managed push
  (Ably/Pusher/etc.) is also worth a build-vs-buy sentence.
- The single open question ("which WebSocket library?") is the least consequential decision
  in the doc. The open-questions list should instead carry the items above.

---

## Recommended changes, summarized

1. Add a client resync-on-(re)connect protocol using `GET /notifications?since=<cursor>`;
   treat pub/sub as a lossy hint. (Blocks everything else.)
2. Publish to Redis only after DB commit, via one shared code path; define the message
   envelope and dedupe-by-ID on the client.
3. Specify WS auth (short-lived token at handshake, channel derived from authenticated
   identity), WSS, origin checks, and connection limits.
4. Rewrite the rollout as a flagged, phased migration; keep a slow-poll fallback permanently;
   define rollback.
5. Add reconnect backoff + jitter, heartbeats, LB idle-timeout config, and deploy-time
   connection draining.
6. Add capacity numbers (peak concurrent connections, per-instance targets), Redis topology
   and failover behavior, and the metrics/SLO section.
7. State explicitly whether mobile background delivery is in scope; if yes, add APNs/FCM.
8. Give SSE (and build-vs-buy) an honest evaluation before committing to raw WebSockets.

With items 1–4 addressed, this becomes a sound, buildable design; items 5–8 determine whether
it survives its first month in production.
