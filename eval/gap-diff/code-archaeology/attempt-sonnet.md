# Technical Review: Making Retry Count Configurable in `sync_account`

## 1. Questions That Must Be Answered Before Any Change

1. **Who calls `sync_account` and how?** Is it invoked from a web request handler, a background worker, a Celery task, a cron job, or multiple of these? The caller context determines whether a caller-side retry budget already exists and whether making retries configurable could create double-retry loops.

2. **What is the expected SLA / timeout for a single account sync?** The current 3 retries with exponential backoff (0s, 2s, 4s = ~6s total) produce a specific worst-case latency. If the retry count becomes configurable, what is the maximum acceptable latency for any caller?

3. **Is the retry count the only parameter that should be configurable?** The backoff base (2 seconds), the backoff exponent (2^attempt), and the upstream timeout (10 * (attempt+1) seconds) are all coupled to the retry loop. Should these also be configurable, or are they intentionally fixed?

4. **What happens if `force=True` is passed?** The function acquires a lock, then skips the lock check, but still proceeds through the retry loop. Is `force` used by an admin override path? If so, does the admin path have different retry expectations?

5. **What is the upstream service's rate-limiting policy?** If `sync_account` is called concurrently for many accounts, and each account now retries more than 3 times, could the aggregate traffic exceed upstream rate limits?

6. **Is there a global retry budget or circuit breaker?** Some systems have a shared retry pool or circuit breaker that tracks total retries across all syncs. Making this function's retries configurable could bypass or overload such a system.

7. **What is the data consistency model?** The function writes to a local DB and emits an event. If retries succeed on attempt 3 but the data is stale (version check passes), is that acceptable? What if the upstream returns partially written data during a transient failure?

8. **What is the monitoring/alerting baseline?** Current alerts are likely tuned to the 3-retry behavior (e.g., "sync_failed" fires after 3 attempts). Changing the retry count could cause alert fatigue (more failures reported) or mask failures (more silent retries).

9. **Is there a configuration system in place?** Where should the configurable retry count live: environment variable, config file, feature flag, database, or service discovery? Who should have permission to change it?

10. **Are there integration tests that assert the retry behavior?** Any test that mocks `upstream.fetch` to raise `UpstreamError` N times will break if the retry count changes. What is the test coverage for the retry loop?

---

## 2. Hidden Dependencies

### 2.1 Redis Lock Dependency

- **Line 10:** `redis.setnx(f"sync:{account_id}", 1)` — This is a non-atomic check-then-set. Between the `setnx` call and `redis.expire` on line 13, another process could theoretically acquire the same lock if `setnx` returns 1 but `expire` has not yet executed. This is a known Redis gotcha; the recommended pattern is `SET key value NX EX seconds` (atomic).

- **Line 13:** `redis.expire(f"sync:{account_id}", 300)` — This runs unconditionally, even when `force=True` and the lock was not acquired by this call. It resets the TTL on a lock that may belong to another process, effectively extending their lease. This is a bug: the expire should only run if this process acquired the lock.

- **Line 26:** `redis.delete(f"sync:{account_id}")` — This runs unconditionally at the end of the function, including after the for loop completes normally or via `break`. However, if the function exits early (e.g., `return` on line 12 when lock is held by someone else), the delete on line 26 still executes, potentially deleting a lock that belongs to another process.

- **No lock renewal (watchdog):** If a sync takes longer than 300 seconds, the lock expires and another process can acquire it, leading to concurrent syncs of the same account. There is no mechanism to renew the lock during long-running operations.

### 2.2 Upstream Service Dependency

- **Line 16:** `upstream.fetch(account_id, timeout=10 * (attempt + 1))` — The timeout scales with attempt number (10s, 20s, 30s). This is intentional (giving the upstream more time on retries), but the total possible wait is 60 seconds across 3 attempts. If retries become configurable (e.g., 10 attempts), the total wait could be 550 seconds (~9 minutes).

- **Line 16:** `UpstreamError` is the only exception caught. If `upstream.fetch` raises a different exception (e.g., `ConnectionError`, `TimeoutError`, `ValueError` from JSON parsing), the function does not catch it, and the exception propagates. The lock is never released in that case.

- **Line 16:** The `timeout` parameter is passed as a keyword argument. If the upstream API changes its signature, this could silently break or raise a TypeError.

### 2.3 Database Dependency

- **Line 19:** `db.write(account_id, data)` — This writes to a local database. If this write fails (e.g., database connection error, constraint violation), the exception is not caught, and the function exits without releasing the Redis lock.

- **Line 19:** There is no transaction or idempotency guard. If the function retries and `db.write` is called again with the same data, it could create duplicate records or violate unique constraints, depending on the database schema.

- **Line 17:** `get_local_version(account_id)` — This function is not shown. It could be a database query, a cache lookup, or a network call. If it fails, the exception propagates. If it returns a stale cached value, the version comparison on line 17 could incorrectly skip a sync.

### 2.4 Event Emission Dependency

- **Line 20:** `emit_event("account.synced", account_id, data['version'])` — This emits an event after a successful sync. If `emit_event` fails (e.g., message queue is down), the sync still "succeeds" from the function's perspective (the `break` on line 21 executes). The event loss is silent.

- **Line 20:** `data['version']` — If the `version` key is missing from `data`, this raises a `KeyError`, which is not caught. The lock is not released.

- **Line 24:** `emit_event("account.sync_failed", account_id)` — This only fires on the final attempt. If retries become configurable, the condition `attempt == 2` will no longer be correct. It should be `attempt == max_retries - 1` or equivalent.

- **Line 24:** The "sync_failed" event does not include the number of attempts or the error reason. Consumers of this event cannot distinguish between a transient failure and a permanent one.

### 2.5 Time Dependency

- **Line 25:** `time.sleep(2 ** attempt)` — This is a blocking call. In a synchronous function, this blocks the entire thread/process for the duration of the sleep. If this function runs in a single-threaded event loop (e.g., asyncio without async sleep), it blocks all other work.

- **Line 25:** The total sleep time across 3 attempts is 0 + 2 + 4 = 6 seconds. If retries become configurable, the total sleep time grows exponentially.

---

## 3. Risks of Making Retry Count Configurable

### 3.1 Operational Risks

- **Infinite or very large retry counts:** If the configurable value is not bounded, a misconfiguration could cause the function to retry thousands of times, blocking a thread for hours or days. There is no maximum retry count in the current code.

- **Resource exhaustion:** Each retry holds a Redis lock and potentially a database connection and an upstream HTTP connection. More retries = more resources held for longer. In a high-throughput system, this could exhaust connection pools.

- **Cascading failures:** If the upstream service is degraded, increasing retries across many concurrent syncs could amplify the load on the upstream (more concurrent requests, longer-held connections), worsening the degradation.

- **Alert storm:** If the retry count is increased and the upstream is intermittently failing, the "sync_failed" event will fire less frequently (more retries before failure), but the "synced" event may also fire with stale data. Conversely, if the retry count is decreased, "sync_failed" fires more often, potentially overwhelming alerting systems.

### 3.2 Data Consistency Risks

- **Stale data writes:** The version check on line 17 (`data.get('version') <= get_local_version(account_id)`) breaks the loop if the upstream data is not newer than local data. If retries are increased, the function may keep writing stale data to the database (line 19) before the version check triggers, creating unnecessary write load.

- **Duplicate events:** If `emit_event` is called but the event is not reliably delivered, and the function retries, the same event could be emitted multiple times. Event consumers must be idempotent, but this is not guaranteed.

- **Partial sync state:** The function writes to the database (line 19) and emits an event (line 20) in sequence. If the process crashes between these two lines, the database is updated but the event is not emitted. Conversely, if it crashes between the event emission and the Redis lock release, the event is emitted but the lock is not released.

### 3.3 Security Risks

- **Configuration injection:** If the retry count is read from an environment variable or config file that is writable by an unprivileged user, an attacker could set it to a very large value to cause a denial of service.

- **Redis lock takeover:** The non-atomic `setnx` + `expire` pattern, combined with the unconditional `redis.delete` at the end, means a malicious or buggy caller could delete another process's lock, enabling concurrent syncs of the same account and potential data corruption.

---

## 4. What to Check Before Making the Change

### 4.1 Code Review Checklist

- [ ] **Verify all callers** of `sync_account` to ensure none of them have their own retry logic that would create a double-retry scenario.
- [ ] **Check the `UpstreamError` class** to understand what exceptions it covers and whether there are related exceptions (e.g., `UpstreamTimeoutError`, `UpstreamAuthError`) that should also be caught.
- [ ] **Check `db.write`** to understand its failure modes: does it raise exceptions? Does it have its own retry logic? Is it idempotent?
- [ ] **Check `emit_event`** to understand its failure modes: does it raise exceptions? Is it async? Does it have a retry mechanism?
- [ ] **Check `get_local_version`** to understand its failure modes and whether it caches results (and how stale the cache can be).
- [ ] **Check the Redis client** to understand whether `setnx`, `expire`, and `delete` are synchronous or asynchronous, and whether they raise exceptions on failure.
- [ ] **Check the upstream client** to understand whether `fetch` has its own retry logic, and whether the `timeout` parameter is respected.

### 4.2 Testing Checklist

- [ ] **Unit test:** Write a unit test that verifies the retry loop runs exactly N times (where N is the configurable retry count) before giving up.
- [ ] **Unit test:** Write a unit test that verifies the function breaks early when the version check passes.
- [ ] **Unit test:** Write a unit test that verifies the "sync_failed" event is emitted only on the final attempt.
- [ ] **Unit test:** Write a unit test that verifies the Redis lock is released in all code paths (normal exit, early break, exception).
- [ ] **Integration test:** Run the function against a mock upstream that fails N times and succeeds on the (N+1)th attempt, verifying the correct number of retries.
- [ ] **Integration test:** Run the function with `force=True` and verify the lock behavior is correct.
- [ ] **Load test:** Run the function under high concurrency to verify that the Redis lock prevents concurrent syncs of the same account.
- [ ] **Chaos test:** Kill the upstream service mid-retry and verify the function handles the failure gracefully (lock released, event emitted).

### 4.3 Monitoring and Alerting Checklist

- [ ] **Verify existing alerts** are tuned to the current retry behavior. If the retry count increases, adjust alert thresholds accordingly.
- [ ] **Add a metric** for the number of retries per sync (e.g., a histogram of retry counts). This allows monitoring whether retries are increasing over time, which could indicate upstream degradation.
- [ ] **Add a metric** for the total sync duration (from first attempt to last). This allows monitoring whether the configurable retry count is causing excessive latency.
- [ ] **Add a metric** for the number of "sync_failed" events per account per time window. This allows detecting accounts that are consistently failing to sync.

### 4.4 Configuration Checklist

- [ ] **Choose a configuration mechanism:** environment variable, config file, feature flag, or database. Consider the operational needs: who needs to change it, how often, and with what level of granularity (per-account, per-service, global).
- [ ] **Set a default value:** The default should be 3 (the current hardcoded value) to avoid changing behavior.
- [ ] **Set a maximum value:** To prevent misconfiguration, set a reasonable maximum (e.g., 10 or 20). Beyond this, the exponential backoff becomes impractical.
- [ ] **Set a minimum value:** The minimum should be 1 (at least one attempt). A value of 0 would mean no attempts, which is likely a misconfiguration.
- [ ] **Validate the configuration:** At startup or on configuration change, validate that the retry count is within the allowed range. Log a warning if it is not.

### 4.5 Code Change Plan

The minimal change to make the retry count configurable would be:

1. Replace the hardcoded `range(3)` with a configurable value (e.g., `range(retry_count)`).
2. Replace the hardcoded `attempt == 2` check with `attempt == retry_count - 1`.
3. Add a default value of 3 and a maximum bound.
4. Fix the Redis lock bugs (non-atomic setnx+expire, unconditional delete) as a separate change, because they are independent of the retry count change and fixing them together increases the risk of introducing new bugs.

However, the Redis lock bugs are severe enough that they should be fixed before or alongside the retry count change. Specifically:

- **Line 10-13:** Replace `setnx` + `expire` with an atomic `SET key value NX EX seconds`.
- **Line 26:** Only delete the lock if this process acquired it (track whether the lock was acquired and only delete in that case).
- **Line 13:** Only call `expire` if this process acquired the lock.

---

## 5. Summary of Findings

| Category | Finding | Severity |
|---|---|---|
| Bug | `setnx` + `expire` is non-atomic; another process can acquire the lock between the two calls | High |
| Bug | `redis.expire` runs unconditionally, extending another process's lock lease | Medium |
| Bug | `redis.delete` runs unconditionally, potentially deleting another process's lock | High |
| Bug | `attempt == 2` is hardcoded; will break if retry count changes | Medium |
| Risk | No upper bound on retry count; misconfiguration could cause indefinite retries | High |
| Risk | No lower bound on retry count; 0 retries means no attempts | Medium |
| Risk | Uncaught exceptions (non-`UpstreamError`) leave the Redis lock unreleased | High |
| Risk | `db.write` failure leaves the Redis lock unreleased | High |
| Risk | `data['version']` KeyError leaves the Redis lock unreleased | Medium |
| Risk | `emit_event` failure is silent; event may be lost | Medium |
| Risk | No transaction or idempotency guard on `db.write`; duplicate writes possible | Medium |
| Risk | Total sync latency grows exponentially with retry count; no timeout on the function itself | Medium |
| Risk | Blocking `time.sleep` in a potentially single-threaded environment | Low |
| Risk | Version check may use stale cached data from `get_local_version` | Medium |
| Risk | "sync_failed" event lacks error details and retry count | Low |
| Risk | No monitoring metrics for retry behavior | Medium |
| Risk | No configuration validation for the retry count | High |
| Risk | Double-retry if callers have their own retry logic | Medium |