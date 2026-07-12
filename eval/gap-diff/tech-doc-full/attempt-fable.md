# Review: "Caching Layer" design doc

**Verdict: Not ready.** This is a proposal sketch, not a design. It names a technology and a pattern (cache-aside) but skips the problem definition, the correctness questions that make caching hard, the failure modes, and the operational plan. I'd send it back for a full revision before any implementation starts. Below is everything I'd want addressed, roughly ordered from "blocks approval" to "should be covered."

---

## 1. The problem is not actually diagnosed

- **"Our API is slow and the database is under load" is not a problem statement.** Which endpoints are slow? What are the current p50/p95/p99 latencies? What's the target? Which queries dominate DB load — is it reads or writes? A cache only helps read-heavy, repeated, tolerably-stale access patterns. Without profiling data, we don't know a cache helps at all.
- **No evidence caching is the right fix.** Cheaper/simpler alternatives are never considered and must be ruled out first (or at least discussed in an "Alternatives" section):
  - Missing or wrong indexes; slow query analysis (`EXPLAIN` the top offenders).
  - N+1 query patterns in the app layer.
  - Connection pooling misconfiguration / pool exhaustion.
  - Read replicas to offload read traffic.
  - Query/result caching at the app level (in-process memoization) for hot, small data.
  - Materialized views or denormalization for expensive aggregates.
  - DB instance right-sizing.
  If the slowness is from writes, lock contention, or a handful of unindexed queries, Redis fixes nothing and adds a distributed-systems problem.
- **No success metrics.** The doc's only measurable claim is "should improve latency a lot." Define targets: e.g., "p95 for endpoints X, Y drops from 800ms to <150ms; DB read QPS drops 60%; cache hit rate >80%." Without these you can't evaluate the rollout or know when you're done.
- **No Goals / Non-goals section.** What is explicitly out of scope (e.g., caching writes, session storage, rate limiting)? Scope will creep the moment Redis exists.

## 2. Cache invalidation and consistency — the actual hard part — is entirely absent

This is the biggest technical gap. The doc describes cache-aside reads and never mentions writes.

- **What happens on write/update/delete?** If the app updates a row, the cached copy is now stale forever (or until TTL). The doc needs a strategy: invalidate-on-write (delete the key), write-through, or accept TTL-bounded staleness — and it needs to say which data can tolerate which.
- **No TTL policy at all.** Every cached entry needs a TTL, per data type. Without TTLs, stale data lives forever and memory grows unbounded.
- **Staleness tolerance per data type.** Some data (product descriptions) tolerates minutes of staleness; some (account balances, permissions, inventory) may tolerate none. The doc must classify what gets cached. Caching authorization/permission data wrongly is a security bug, not just a UX bug.
- **Race conditions in cache-aside.** Classic bug: request A reads DB (old value), request B writes DB and invalidates cache, then A populates the cache with the stale value it read. Mitigations (short TTLs, compare-and-set, versioned keys, delayed double-delete) should be acknowledged.
- **Multiple writers.** If other services, background jobs, admin tools, or direct DB migrations mutate the data, they bypass app-level invalidation. How do those paths invalidate? (CDC/Debezium, DB triggers, or "they don't and we rely on TTL" — pick one explicitly.)
- **Transactionality.** DB writes and cache invalidations are not atomic. What happens when the DB commit succeeds but the cache delete fails (network blip)? Order of operations matters (invalidate after commit, not before/inside the transaction).
- **Key versioning / schema evolution.** When the shape of a cached object changes with a deploy, old cached blobs will fail to deserialize or, worse, silently deserialize wrong. Need a version component in keys or in the serialized payload, and a plan for mixed-version fleets during deploys.

## 3. Failure modes and availability

- **Redis becomes a new single point of failure — the doc adds one instance with no HA story.** What happens when Redis is down, slow, or unreachable?
  - **Fail open** (fall through to the DB): correct default for a cache, but then a Redis outage instantly sends 100% of traffic to a database that we already know "is under load." That's a thundering-herd outage waiting to happen. Does the DB survive a cold cache at peak? This must be answered with numbers.
  - **Fail closed** (error out): unacceptable for a cache; the doc should state that Redis is never on the availability-critical path.
- **Timeouts and circuit breaking.** A slow Redis is worse than a dead one. Cache reads need aggressive timeouts (a few ms), a circuit breaker, and bounded connection pools so a Redis brownout doesn't consume all app threads and take the API down — the cache making things slower/less reliable is a very common failure.
- **Cache stampede / dog-piling.** When a hot key expires (or on cold start / after a flush), N concurrent requests all miss and hammer the DB with the same expensive query simultaneously. Need a mitigation: request coalescing / single-flight, lock-based repopulation, probabilistic early expiration, or TTL jitter so keys don't expire in synchronized waves.
- **Cold start.** First deploy, failover, or restart means 0% hit rate. Is warming needed? Is the rollout sequenced so the DB isn't overwhelmed while the cache fills?
- **Hot keys.** A single very-hot key concentrates load on one Redis shard/instance and can saturate its network. Any known hot objects? (Mitigations: client-side/in-process L1 cache, key replication.)
- **Negative caching.** Do we cache "not found"? If not, requests for nonexistent IDs (or an enumeration attack) bypass the cache entirely and hit the DB every time. If yes, with what TTL?
- **Eviction under memory pressure.** What `maxmemory` and which eviction policy (`allkeys-lru`, `volatile-ttl`, `noeviction`)? `noeviction` (a common default) makes writes fail when full. This must be chosen deliberately.

## 4. Capacity, topology, and infrastructure — "add a Redis instance" is not a design

- **Managed vs. self-hosted.** ElastiCache/MemoryStore/Upstash vs. running it ourselves? Who patches it, who's on call for it? Strong default: managed. The doc doesn't say.
- **Topology and HA.** Single node? Primary + replica with automatic failover (Sentinel/managed failover)? Cluster mode for sharding? Depends on the availability requirement and data size — none of which are stated.
- **Sizing.** Working-set size estimate: number of cacheable objects × average serialized size × overhead, plus growth. Determines instance size and cost. Not mentioned.
- **Persistence.** RDB/AOF or none? For a pure cache, usually none — but that should be an explicit decision (persistence affects failover behavior and latency spikes from forking).
- **Network placement.** Same VPC/region/AZ as the app? Cross-AZ Redis calls add latency and data-transfer cost; cross-region would defeat the purpose. Multi-AZ replica placement for failover?
- **Cost.** Zero cost analysis. Managed Redis at a useful size is real money; compare against the alternative (e.g., one read replica, or a bigger DB instance).

## 5. Security and compliance — completely missing

- **Authentication and encryption.** Redis is unauthenticated and plaintext by default. Require AUTH/ACLs, TLS in transit, encryption at rest (managed offerings support this), and network isolation (private subnet, security groups — never publicly reachable). Internet-exposed Redis is one of the most commonly popped services in the wild.
- **Sensitive data.** Will PII/PHI/payment data land in the cache? That pulls Redis into compliance scope (GDPR/SOC2/etc.), affects retention (a GDPR deletion request must also purge cache entries), and constrains what can be cached at all.
- **Multi-tenancy / authorization in keys.** Cache keys must encode the full authorization context. The classic catastrophic bug: caching a response under `key = endpoint + resource_id` and serving user A's private data to user B. Key design needs explicit review for every cached object.
- **Secrets management** for the Redis credentials.

## 6. Key and value design — unspecified

- **Key schema and namespacing** (e.g., `svc:entity:v2:{id}`), documented conventions, and a version segment for schema migrations.
- **Serialization format.** JSON? MessagePack? Language-native pickling (please no — deserialization of untrusted-ish data + cross-language lock-in)? Affects size, speed, and cross-service compatibility.
- **Value size limits.** Caching huge blobs (multi-MB query results) causes latency spikes and network saturation; need a max-size guard and a decision about what's too big to cache.
- **What, exactly, is cached?** Raw DB rows? Assembled domain objects? Full HTTP responses? Each has different invalidation granularity and reuse characteristics. The doc never says.

## 7. Rollout plan — "Deploy Redis, point the app at it, done" is not a plan

- **No incrementality.** It should be: deploy infra → integrate behind a feature flag, default off → enable for one low-risk endpoint → measure hit rate/latency/DB load → expand endpoint by endpoint → ramp by traffic percentage. Big-bang cutover of a correctness-affecting layer is how you serve stale or cross-user data at 100% blast radius.
- **No kill switch / rollback.** A runtime flag to bypass the cache instantly (not a redeploy) is mandatory. Also note: rolling back the app doesn't roll back poisoned cache contents — need the ability to flush/invalidate by namespace.
- **No shadow/validation phase.** Consider dual-read (serve from DB, compare with cache, log mismatches) to detect staleness/serialization bugs before serving cached data.
- **No load/failure testing.** Test the DB's ability to absorb a cold cache; test app behavior with Redis killed, with Redis at 100% memory, and with injected latency.
- **No timeline, milestones, or owner.**

## 8. Observability and operations — missing

- **Metrics:** hit/miss rate (per key-namespace), cache read/write latency, Redis memory usage, evictions, connection count, error/timeout rate, and — critically — DB load before/after so the doc's central claim is verifiable.
- **Alerts:** hit rate collapse, memory > threshold, eviction spikes, replication lag, failover events, elevated cache timeouts.
- **Dashboards and a runbook:** what on-call does when Redis fails over, fills up, or serves stale data; how to flush a namespace safely (and why `FLUSHALL` at peak is dangerous — see stampede).
- **Ownership:** which team owns Redis, its upgrades (version/EOL policy), and its pager.
- **Staleness debugging:** when a user reports wrong data, how do engineers determine whether it's the cache? (Key inspection tooling, `TTL`/`OBJECT` commands, trace annotations for cache hit/miss.)

## 9. Testing strategy — missing

- Unit tests around cache logic (hit, miss, invalidation on write, serialization round-trip).
- Integration tests with a real Redis (testcontainers) including failure injection (Redis down mid-request).
- Concurrency tests for the read-populate-write race.
- CI/local dev story: does every dev environment now need Redis, or does the code path degrade gracefully without it?

## 10. Doc structure and framing

- **Solution-first framing.** The doc starts with "We should add Redis" and reasons backward. It should start from the measured problem and evaluate options — Redis may well win, but as a conclusion, not a premise. Also: why Redis specifically vs. Memcached (simpler, pure cache), vs. in-process caching, vs. no new infra (replicas/indexes)? No alternatives section exists.
- **"Redis is fast so things will be faster" is a non-sequitur.** End-to-end latency improvement depends on hit rate and on whether the cached queries are the slow ones. A 30% hit rate on cheap queries improves nothing and adds a network hop (+ serialization cost) to every request.
- **The one open question listed (client library) is the least important decision in the project.** That it's the *only* open question is the clearest signal the design hasn't been thought through — invalidation strategy, failure behavior, what to cache, and HA topology are the real open questions.
- Missing standard sections: author/date/status, goals/non-goals, background with data, alternatives considered, detailed design, security review, rollout, monitoring, risks, open questions (real ones), success criteria.

---

## What I'd ask for before re-review

1. Profiling data: top N slow endpoints/queries with latency percentiles and DB load attribution; explicit argument for why caching (vs. indexes/replicas/query fixes) is the right lever.
2. Explicit list of what data will be cached, each with: staleness tolerance, TTL, invalidation trigger(s), key schema (including auth context), and estimated size/QPS.
3. Failure-mode section: Redis down (fail-open behavior + DB cold-cache capacity math), Redis slow (timeouts/circuit breaker), stampede mitigation, eviction policy.
4. Infra decision: managed vs. self-hosted, topology/HA, sizing, cost, security posture (TLS/AUTH/network isolation), and ownership/on-call.
5. A staged rollout plan with a runtime kill switch, per-endpoint enablement, success metrics, and rollback story.
6. Observability plan: metrics, alerts, dashboards, runbook.

The underlying instinct may be right — a read cache is often the correct fix for a read-heavy, hot-working-set workload. But as written, this doc would get the team a new tier of infrastructure with unbounded staleness, an unexamined new SPOF, potential cross-user data leaks, and no way to measure whether it worked. Not ready; needs a substantial second draft.
