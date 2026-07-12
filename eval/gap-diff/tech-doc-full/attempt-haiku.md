# Design Doc Review: Caching Layer (Redis)

## Overall Assessment

**Not ready.** This design doc is closer to a one-liner pitch than a design document. It identifies a real problem (API slowness, database under load) and proposes a real solution (Redis caching), but it lacks virtually every element required for a team to evaluate, implement, or operate the proposal. It reads like a Slack message, not a design doc.

Below is a complete review organized by category.

---

## 1. Problem Statement Is Incomplete

The doc states "Our API is slow and the database is under load" but provides no evidence or specificity:

- **No metrics.** What is "slow"? What is the current p50/p95/p99 latency? What is the current database CPU, memory, IOPS, connection count? Without baselines, there is no way to measure whether the change succeeded.
- **No root cause analysis.** "Database under load" could mean many things: too many connections, slow queries, missing indexes, unbounded result sets, hot rows, lock contention, replication lag. Caching only helps if the load is caused by repeated reads of the same data. If the database is under load from writes, or from queries that are inherently expensive (joins, aggregations), caching will not meaningfully help.
- **No scope of the problem.** Which endpoints/APIs are slow? Is it a few hot endpoints or all of them? Is the problem read-heavy or write-heavy? The doc does not say.
- **No alternative solutions considered.** Before adding an entire new infrastructure component, the doc should address: query optimization, database read replicas, connection pooling, application-level in-memory caching (e.g., LRU map), pagination/limiting, or CDN for static data. Redis is a significant operational cost -- it should be justified, not assumed.

**Verdict:** The problem is real but under-specified. The doc should include concrete metrics and a brief analysis of why caching is the right lever.

---

## 2. Design Is Absent

The "Design" section is two sentences. It describes the cache-aside (lazy-loading) pattern at a level that is not actionable:

- **No cache key strategy.** How are cache keys constructed? From what request parameters? What happens when a resource is updated or deleted -- how are stale keys invalidated? This is one of the hardest parts of caching and it is not addressed at all.
- **No cache scope.** What data goes in the cache? All endpoints? Only read-only endpoints? Only specific tables? The doc does not say.
- **No TTL / expiration strategy.** How long does data stay in the cache? Is it per-key? Per-data-type? What happens when the cache expires -- do you get a thundering herd of database queries?
- **No cache eviction policy.** Redis has LRU, LFU, random eviction, etc. Which is chosen and why?
- **No handling of cache misses vs. cache hits.** The doc says "if the data is there, return it; if not, query the database, store the result, return it." This is the entire design. There is no discussion of:
  - Serialization format (JSON? Protocol Buffers? MessagePack?)
  - Cache size limits and memory management
  - What happens when Redis is full
  - What happens when the database schema changes
  - Handling of partial data (e.g., paginated results -- do you cache the full result set or per-page?)
- **No discussion of cache consistency.** If data is updated, how long until the cache reflects the change? Is eventual consistency acceptable? What about race conditions where two requests simultaneously miss the cache and both hammer the database?
- **No diagram.** A simple architecture diagram showing app -> Redis -> database would be expected in any design doc of this scope.

**Verdict:** The design is not detailed enough for implementation. A developer reading this would have to make every significant decision themselves.

---

## 3. No Operational / Infrastructure Considerations

Adding Redis is not "deploy Redis, point the app at it, done." This is the most problematic gap:

- **Redis deployment model.** Is this a managed service (AWS ElastiCache, Redis Cloud, etc.) or self-hosted? The operational implications are vastly different.
- **High availability.** Is this a single Redis instance? What happens when it goes down? Does the app degrade gracefully (falling back to direct database queries), or does the entire API fail?
- **Persistence.** Is RDB/AOF persistence enabled? If Redis crashes, is the cache state lost (acceptable for a cache) or should it be persisted?
- **Security.** How is Redis authenticated? Is it on a private network? TLS? The doc does not mention security at all.
- **Monitoring and alerting.** What metrics will be tracked? Cache hit rate, miss rate, latency, memory usage, evictions, connections? What are the alert thresholds?
- **Scaling.** How will Redis scale as traffic grows? Single-node Redis has limits. When do you need Redis Cluster or Sentinel?
- **Cost.** Redis instances (managed or self-hosted) cost money. The doc does not include any cost estimate.
- **Disaster recovery.** What is the RTO/RPO for Redis? If the entire Redis layer fails, can the system survive?

**Verdict:** The operational plan is non-existent. This is the single biggest risk area.

---

## 4. No Performance / Capacity Planning

- **No capacity estimates.** How much memory will the cache need? What is the estimated data size? How many keys? What is the expected hit rate?
- **No benchmarking plan.** How will you measure the improvement? What are the success criteria?
- **No discussion of cache warming.** Will the cache start empty? If so, the first burst of traffic will hit the database hard. Is there a cache-warming strategy?
- **No discussion of the cold-start problem.** When Redis is first deployed or restarted, the cache is empty. The database will be hammered until the cache fills.

**Verdict:** No performance analysis is present.

---

## 5. No Migration / Rollout Plan

The "Rollout" section says "Deploy Redis, point the app at it, done." This is dangerously oversimplified:

- **No phased rollout.** Will this be rolled out to all endpoints at once? A canary? A specific environment first?
- **No feature flag / toggle.** Can the cache be disabled if it causes problems? This is critical -- if the cache returns stale or incorrect data, you need an off switch.
- **No rollback plan.** If the deployment causes issues, how do you roll back?
- **No database compatibility concerns.** If the app currently uses a connection pool of, say, 20 connections, and Redis is down, the app will suddenly use all 20 connections for every request. Is the database prepared for this?
- **No configuration management.** How is the Redis connection string, TTLs, and other configuration managed? Environment variables? Config server?

**Verdict:** The rollout plan is a single sentence that ignores every real-world deployment concern.

---

## 6. No Error Handling / Failure Modes

- **What if Redis is slow?** Redis is in-memory and typically sub-millisecond, but network latency, large payloads, or memory pressure can cause slowdowns. What is the timeout for Redis operations?
- **What if Redis is unavailable?** Does the app fail open (go to database) or fail closed (return an error to the user)? The doc does not specify.
- **What if Redis returns corrupted data?** Is there validation?
- **What about partial failures?** If the cache write succeeds but the database query fails (or vice versa), what happens?
- **Circuit breaker?** Should there be a circuit breaker pattern so the app stops trying Redis if it is consistently failing?

**Verdict:** No failure modes are considered.

---

## 7. No Security Considerations

- **Data sensitivity.** Is the cached data PII, health data, financial data, or other sensitive information? If so, caching it in Redis (which may be shared, may have different retention policies, may be backed up) requires careful consideration.
- **Cache injection.** Are cache keys derived from user input? Could an attacker craft keys to cause cache poisoning or DoS (creating millions of unique keys to exhaust memory)?
- **Access control.** Who/what can access the Redis instance? Is it firewalled?
- **Compliance.** Does caching this data violate any compliance requirements (GDPR, HIPAA, PCI)?

**Verdict:** No security analysis is present.

---

## 8. Open Questions Are Incomplete

The single open question ("Which Redis client library should we use?") is the wrong level of abstraction. The client library is an implementation detail. The real open questions are:

- What data should be cached?
- What is the cache key strategy?
- What is the TTL / expiration strategy?
- How is cache invalidation handled?
- What is the deployment model (managed vs. self-hosted)?
- What is the high-availability strategy?
- What are the success criteria / metrics?
- What is the rollback plan?
- What is the cost estimate?
- Is there a feature flag to disable the cache?

**Verdict:** The open questions section is missing the actual open questions.

---

## 9. Missing Standard Design Doc Sections

A complete design doc should include (at minimum):

- **Context / background.** What is the current architecture? What does the current data flow look like?
- **Goals.** What are the specific, measurable goals of this change? (e.g., "Reduce p95 latency from 500ms to 100ms for /api/users")
- **Non-goals.** What is explicitly out of scope? (e.g., "We are not changing the database schema")
- **Proposed design.** A detailed design with diagrams, as described above.
- **Alternatives considered.** Why Redis and not Memcached? Why not application-level caching? Why not optimize the queries?
- **Trade-offs.** What are the costs and risks of this approach? (Operational overhead, cache inconsistency, added complexity, cost)
- **Implementation plan.** Phased approach, milestones, who is responsible.
- **Monitoring and observability.** What will be measured and how.
- **Risks and mitigations.** What could go wrong and how to handle it.
- **Timeline.** When will this be done?

---

## Summary of Pushback

1. **This is not a design doc.** It is a proposal pitch. It needs to be expanded significantly before the team can evaluate it properly.
2. **The problem is under-analyzed.** Before jumping to Redis, the team should understand the actual bottleneck. Caching is not a universal fix.
3. **The operational burden is underestimated.** Redis is not a "point and it works" component. It requires monitoring, alerting, capacity planning, HA strategy, and operational expertise.
4. **The rollout plan is naive.** Deploying a caching layer with no feature flag, no phased rollout, and no rollback plan is a production risk.
5. **The open questions are at the wrong level.** The team needs to answer architectural questions before implementation details like client library selection.

## Recommended Next Steps

1. **Gather metrics.** Measure current latency, database load, and identify which endpoints are slow.
2. **Write a proper design doc.** Include all sections listed above.
3. **Consider a spike.** Before committing to Redis, do a small spike: add Redis to one endpoint, measure the improvement, and learn from the experience. This de-risks the larger rollout.
4. **Start with the easiest win.** Pick one read-heavy, low-changability endpoint and implement caching there first. This validates the approach before scaling.