# GRADER checklist — tech-doc (13 items; the doc is a bad-doc with planted gaps)

1 the PROBLEM is stated as the solution ('we should add Redis') — no real problem statement: r"problem.*(solution|missing|not (stated|defined)|is the solution)|solution.*(masquerad|as.*problem|first)|starts with.*(solution|redis)|no.*(problem statement)|what.*problem"
2 no NUMBERS / metrics — 'slow', 'a lot' unquantified (p95? how slow? target?): r"number|metric|quantif|p95|p99|latency.*(target|number|measure)|how slow|unquantif|measure|no (data|number|metric)|vague.*(slow|fast)"
3 no ALTERNATIVES considered (query optimization, read replica, indexes, caching in app): r"alternativ|other option|query optim|read replica|index.*(instead|first)|before.*redis|cheaper.*(option|fix)|do nothing|why redis vs"
4 CACHE INVALIDATION not addressed — stale data (the hard part): r"invalidat|stale|cache.*(stale|invalid|expire|ttl)|consistency|when.*(update|change).*(cache|data)|TTL|eviction"
5 no CACHE-MISS / thundering herd / stampede consideration: r"thundering herd|stampede|cache miss.*(storm|all)|dogpile|miss.*(spike|load)|simultaneous.*(miss|rebuild)"
6 Redis as a new SPOF / what if Redis is down (degraded mode): r"spof|single point|redis (down|fail|unavail)|degraded|fallback.*(redis|db)|what if redis|redis.*(ha|failover)"
7 no eviction policy / memory bounds — Redis fills up: r"eviction|memory.*(bound|limit|full|policy)|maxmemory|LRU|redis.*(full|memory|grow)|out of memory"
8 which data is cacheable? not all data / cache key design missing: r"which data|cacheable|cache key|key design|what to cache|not all.*(data|cacheable)|key.*(scheme|design|collision)"
9 no rollout safety — feature flag / gradual / rollback (the doc says 'deploy, done'): r"feature flag|gradual|rollout.*(safe|stage|flag)|rollback|canary|deploy.*(done|risk)|staged|no rollback"
10 no measurement/verification that it actually helped (before/after): r"measure.*(before|after|helped)|verify.*(faster|improv)|benchmark|did it.*(work|help)|success metric|prove.*(faster|improve)"
11 the open question (client library) is trivial vs the real ones unlisted: r"open question.*(trivial|wrong|minor)|client library.*(trivial|least|minor)|real (question|open)|wrong open question|least important"
12 consistency model / what if DB write happens (dual-write cache vs db): r"consistency|dual.?write|write.*(cache|through|behind)|db.*(update|write).*(cache|stale)|write-through|write-back"
13 no non-goals / scope boundaries stated: r"non.?goal|scope|out of scope|boundar|what.*(not|won.?t).*(do|cache)"

## discriminating: #1 problem-is-solution, #2 no-numbers, #3 no-alternatives, #4 cache-invalidation,
## #11 wrong-open-question. A shallow review says "looks reasonable, add more detail"; a rigorous one
## names that the doc has no problem statement, no metrics, no alternatives, and ignores invalidation.
