# Design doc review

Review this design doc (a real one a colleague wrote). Give a thorough review: is it ready, what's
missing, what would you push back on? Be specific.

---
**Title: Caching Layer**

We should add Redis. Our API is slow and the database is under load. Redis is an in-memory store
that is very fast, so putting it in front of the database will make things faster.

**Design:** We'll add a Redis instance. When a request comes in, check Redis first; if the data is
there, return it. If not, query the database, store the result in Redis, and return it.

**Rollout:** Deploy Redis, point the app at it, done. This should improve latency a lot.

**Open questions:** Which Redis client library should we use?
---
