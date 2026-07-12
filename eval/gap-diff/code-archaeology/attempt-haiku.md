# Code Archaeology: Making the Retry Count Configurable

## 1. Questions That Must Be Answered Before Touching This Code

### 1.1. What is the calling context?
- Who calls `sync_account`? Is it called from a web request handler, a background worker, a CLI tool, or all of the above?
- If called from multiple entry points, do some callers already implement their own retry logic? Would making the retry count configurable create double-retry behavior?
- Is `sync_account` called in a loop over many accounts? If so, increasing retries on one account could cascade and starve others.

### 1.2. What is the expected behavior of the `force` parameter?
- The function has a `force=False` parameter that bypasses the distributed lock. Does `force=True` imply "retry anyway even if already running"? Or does it mean "retry more aggressively"?
- If `force` is true, the lock is acquired but the `if not lock and not force` guard is skipped. Does `force` also need to influence the retry count?

### 1.3. What does `upstream.fetch` do, and what does `UpstreamError` mean?
- Is `UpstreamError` a network timeout, an HTTP 5xx, a connection refused, or something else? Different error types may warrant different retry strategies.
- Does `upstream.fetch` have its own internal retry logic? If so, the outer retry loop may be redundant or may create exponential backoff on top of exponential backoff.

### 1.4. What is `get_local_version` and where does the version live?
- Is the version stored in Redis, in a local cache, in a database, or on disk?
- What happens if `get_local_version` raises an exception? The function has no try/except around it, so it would propagate unhandled.

### 1.5. What is `db.write` and what are its failure modes?
- Does `db.write` have its own retry logic?
- If `db.write` succeeds but `emit_event` fails, the data is persisted but the event is lost. Is that acceptable?
- Is `db.write` transactional? If the function crashes between `db.write` and `emit_event`, is the state recoverable?

### 1.6. What is the event system (`emit_event`)?
- Is `emit_event` synchronous or asynchronous? If synchronous, a slow or down event system blocks the entire sync.
- Is there a dead-letter queue or retry for failed events?
- Who consumes `account.synced` and `account.sync_failed`? Are there downstream systems that depend on these events arriving in order?

### 1.7. What is the Redis instance and is it shared?
- Is this a dedicated Redis instance or shared with other services?
- What happens if Redis is down? `redis.setnx` will raise an exception, and the entire sync will fail with no retry (no try/except around the lock acquisition).
- Is there a Redis sentinel/cluster? What about connection pooling?

### 1.8. What is the `upstream` service?
- Is it an internal microservice, a third-party API, or a database?
- What is its SLA? If it is known to be unreliable, the hardcoded retry of 3 may have been chosen deliberately.
- Does it have rate limits? Three retries with exponential backoff (2^0, 2^1, 2^2 = 1, 2, 4 seconds) totals ~7 seconds of blocking per account. If called for thousands of accounts, this could trigger rate limits.

### 1.9. What is the total expected runtime of this function?
- With 3 retries, max backoff = 1 + 2 + 4 = 7 seconds of sleep, plus up to 10 * 3 = 30 seconds of fetch timeouts. Worst case: ~37 seconds per account.
- If the retry count is increased to, say, 10, the worst case becomes 1 + 2 + 4 + 8 + 16 + 32 + 64 + 128 + 256 + 512 = 1023 seconds (~17 minutes) of sleep alone, plus fetch timeouts. This could be a production incident.

### 1.10. Is there any monitoring or alerting on this function?
- Are there metrics on sync duration, failure rate, or retry count?
- If the retry count is increased, will existing alert thresholds fire falsely?

---

## 2. Hidden Dependencies and Risks

### 2.1. The distributed lock has a race condition (critical bug, pre-existing)
```python
lock = redis.setnx(f"sync:{account_id}", 1)
if not lock and not force:
    return
redis.expire(f"sync:{account_id}", 300)
```
- `setnx` returns the value (1 if set, 0 if already set). If `setnx` succeeds, the lock is set but `expire` is called AFTER the guard. If `setnx` fails (lock already held), the function returns. This part is correct.
- HOWEVER: if the process crashes between `setnx` and `expire`, the lock key has no TTL and will never expire. A subsequent run will be permanently blocked.
- Additionally, `redis.setnx` is deprecated in modern Redis clients in favor of `set(key, value, nx=True)`. This suggests the codebase may be running on an older Redis client version.

### 2.2. The lock is never released on exception
```python
for attempt in range(3):
    try:
        ...
    except UpstreamError:
        ...
redis.delete(f"sync:{account_id}")
```
- If `upstream.fetch` raises a non-`UpstreamError` exception (e.g., `ValueError`, `KeyError`, `ConnectionError` from a different library), the function exits without deleting the Redis lock. The lock will persist until its TTL expires (300 seconds), blocking all future syncs for that account.
- This is a pre-existing bug that would be exacerbated if the retry count is increased, because the lock TTL (300s) may not be long enough for the extended sync to complete.

### 2.3. The lock TTL may be insufficient with more retries
- Current TTL: 300 seconds (5 minutes).
- With 3 retries, worst case is ~37 seconds. Plenty of headroom.
- With 10 retries, worst case is ~17+ minutes. The lock would expire mid-sync, allowing a second sync to start, causing duplicate writes and inconsistent state.

### 2.4. `emit_event` is called inside the retry loop
- If `emit_event` raises an exception that is NOT `UpstreamError`, the lock is not released (same issue as 2.2).
- If `emit_event` is slow, it extends the total sync time, which again may exceed the lock TTL.

### 2.5. Version comparison is not atomic with the fetch
```python
data = upstream.fetch(account_id, timeout=10 * (attempt + 1))
if data.get('version') <= get_local_version(account_id):
    break
```
- Between the `upstream.fetch` and `get_local_version`, the local version could change (if another process updated it). This is a TOCTOU race.
- `data.get('version')` will return `None` if `version` is missing. `None <= some_int` raises `TypeError` in Python 3. This is a silent crash path.

### 2.6. The exponential backoff base is hardcoded
- `time.sleep(2 ** attempt)` uses base 2. If the retry count is made configurable, should the backoff base also be configurable? Or at least the total backoff duration?
- If retries are increased but backoff is not adjusted, the system may hammer the upstream too hard.

### 2.7. No circuit breaker
- If the upstream is completely down, the function will retry 3 times (or N times) and then give up. There is no circuit breaker to stop calling a known-failing upstream. Making retries configurable without adding a circuit breaker means operators could easily create a thundering herd.

### 2.8. The function is synchronous and blocking
- There is no async/await, no threading, no message queue. Each call blocks the caller for up to ~37 seconds. If this is called from a web handler, it will hold a connection/thread for that duration.
- Increasing retries makes this worse.

---

## 3. What to Check Before Making the Change

### 3.1. Code-level checks
- [ ] Search the entire codebase for callers of `sync_account` — grep for `sync_account(` and `from.*import.*sync_account`.
- [ ] Search for any existing configuration mechanism (config files, environment variables, feature flags) to understand the pattern used in this codebase.
- [ ] Check if `upstream` is a module, class, or global — understand its interface.
- [ ] Check if `redis` is a module, class, or global — understand its interface and whether `setnx` is the correct method for the Redis version in use.
- [ ] Check if `emit_event` is synchronous or asynchronous — look at its implementation.
- [ ] Check if `db.write` is synchronous or asynchronous.
- [ ] Check if there are any tests for `sync_account` — run them before and after the change.

### 3.2. Infrastructure checks
- [ ] What Redis version and client library is in use? (The use of `setnx` suggests an older client.)
- [ ] What is the upstream service's rate limit and SLA?
- [ ] Is there a message queue or task queue (Celery, RQ, Sidekiq) that should be used instead of in-process retries?
- [ ] What is the maximum concurrent sync count? If 100 accounts sync simultaneously with 10 retries each, that is 1,000 concurrent upstream calls.

### 3.3. Observability checks
- [ ] Are there existing metrics for sync duration, failure rate, retry count?
- [ ] Is there a distributed tracing system (OpenTelemetry, Datadog) that tracks this function?
- [ ] Are there alerts on sync failures? Would changing the retry count cause alert fatigue or mask real issues?

### 3.4. Risk-mitigation checks
- [ ] Can the retry count be changed via configuration without a code deploy? If not, this is a higher-risk change because any wrong value requires a redeploy.
- [ ] Is there a feature flag or A/B testing framework that could be used to roll out the change gradually?
- [ ] What is the rollback plan? If the new retry count causes problems, can it be reverted quickly?

---

## 4. Recommended Approach (If Proceeding)

### 4.1. Fix the pre-existing bugs first
1. **Release the lock on all exit paths** — wrap the body in a try/finally or use a context manager:
   ```python
   try:
       # ... existing logic ...
   finally:
       redis.delete(f"sync:{account_id}")
   ```
2. **Fix the lock TTL race** — use `set` with `nx=True` and `ex=300` atomically:
   ```python
   lock = redis.set(f"sync:{account_id}", 1, nx=True, ex=300)
   ```
3. **Handle missing `version` key** — use a sentinel or default:
   ```python
   if data.get('version', 0) <= get_local_version(account_id):
   ```

### 4.2. Make the retry count configurable
- Add a parameter with a default of 3 to preserve backward compatibility:
  ```python
  def sync_account(account_id, force=False, max_retries=3):
  ```
- Or read from a configuration source (environment variable, config file, feature flag):
  ```python
  import os
  max_retries = int(os.environ.get("SYNC_MAX_RETRIES", 3))
  ```
- The parameter approach is simpler and easier to test. The config-file approach is more flexible for production but requires understanding the existing configuration pattern.

### 4.3. Consider making backoff configurable too
- If retries are configurable, the backoff strategy should be reviewed. Consider:
  - Configurable base: `time.sleep(base ** attempt)`
  - Configurable max backoff: `min(base ** attempt, max_backoff)`
  - Jitter: `time.sleep(min(base ** attempt + random jitter, max_backoff))` to prevent thundering herd

### 4.4. Add a circuit breaker
- Before increasing retries, consider adding a circuit breaker pattern to stop calling a failing upstream:
  ```python
  if circuit_breaker.is_open():
      raise CircuitBreakerOpen("upstream is down")
  ```

### 4.5. Add observability
- Add metrics: sync duration, retry count, failure rate.
- Add logging: log each retry attempt with the attempt number and elapsed time.

---

## 5. Summary of Findings

| Category | Finding | Severity |
|---|---|---|
| Bug | Lock not released on non-UpstreamError exceptions | High |
| Bug | Lock TTL race: crash between setnx and expire leaves permanent lock | Medium |
| Bug | `data.get('version')` can be None, causing TypeError in comparison | Medium |
| Risk | Lock TTL (300s) may be insufficient with more retries | Medium |
| Risk | No circuit breaker; increasing retries could hammer a failing upstream | High |
| Risk | Synchronous blocking; increasing retries increases connection/thread hold time | Medium |
| Risk | `emit_event` inside retry loop with no error handling | Medium |
| Risk | TOCTOU race between fetch and version check | Low |
| Design | Hardcoded backoff base (2) may not scale with configurable retries | Medium |
| Design | No observability (metrics, tracing) on this function | Medium |
| Design | `redis.setnx` is deprecated in modern Redis clients | Low |
| Design | No configuration mechanism exists; adding one requires understanding the codebase pattern | Low |

The most important insight: **this function has pre-existing bugs that would be exacerbated by increasing the retry count.** The lock-not-released-on-exception bug means that increasing retries (and thus increasing the window for exceptions) makes the permanent-lock scenario more likely. The lock-TTL issue means that a longer-running sync (more retries) could outlast the lock, allowing duplicate concurrent syncs.

The safest path is: fix the bugs first, then make the retry count configurable, then add observability, then consider a circuit breaker.