# Constant Coupling Analysis: `sync_account` — Making Retry Count Configurable

## The Constant

`N = 3` — the hardcoded retry count in `for attempt in range(3)`.

---

## Hunt 1: Algebraic Aliases — Off-by-One Shadows

### Hit 1.1: `attempt == 2` (line 23) — the last-attempt guard

```python
if attempt == 2:
    emit_event("account.sync_failed", account_id)
```

This is a disguised declaration of N. The comparison `attempt == 2` is correct **only because** `range(3)` produces values 0, 1, 2. If N changes to 5, `attempt == 2` fires on the third attempt (not the last), emitting a premature failure event while two more retries remain.

**Must become:** `attempt == N - 1` (or `attempt == retries - 1` once configurable).

### Hit 1.2: `range(3)` itself (line 14)

The loop bound is the primary declaration. Any configurable replacement must feed into this expression.

**Must become:** `range(retries)` where `retries` defaults to 3.

### Hit 1.3: `2 ** attempt` (line 25) — the backoff ceiling

The exponential backoff `2 ** attempt` produces values 1, 2, 4 for attempts 0, 1, 2. The total sleep time is 1 + 2 + 4 = 7 seconds. This is a cumulative function of N:

- N=3: total sleep = 1 + 2 + 4 = 7s
- N=4: total sleep = 1 + 2 + 4 + 8 = 15s
- N=5: total sleep = 1 + 2 + 4 + 8 + 16 = 31s
- N=10: total sleep = 2^10 - 1 = 1023s (~17 minutes)

The backoff formula `2 ** attempt` is a scaling coupling to N. The ceiling of the backoff is an accident of N=3.

---

## Hunt 2: Trace the Induction Variable into Every Expression It Feeds

### Hit 2.1: `timeout = 10 * (attempt + 1)` (line 16) — scaling coupling

The upstream fetch timeout scales linearly with the attempt number:

- attempt=0: timeout=10s
- attempt=1: timeout=20s
- attempt=2: timeout=30s

At N=3, the maximum timeout is 30s. If N=10, the maximum timeout is 100s. This is a direct scaling coupling: the timeout ceiling is an accident of N.

**Risk:** At N=10, a single fetch call could block for 100 seconds. The total wall-clock time for one sync_account call (all retries failing) becomes:

```
timeout_sum = 10*(1+2+3+...+N) = 10 * N*(N+1)/2
sleep_sum = 2^0 + 2^1 + ... + 2^(N-1) = 2^N - 1
total = 10*N*(N+1)/2 + 2^N - 1
```

- N=3: total = 60 + 7 = 67s
- N=5: total = 150 + 31 = 181s
- N=10: total = 550 + 1023 = 1573s (~26 minutes)

### Hit 2.2: `2 ** attempt` (line 25) — exponential coupling

Already noted in Hunt 1.3. The exponential backoff grows doubly with N: both the per-attempt sleep and the number of attempts compound.

### Hit 2.3: `data.get('version')` and `get_local_version(account_id)` (line 17) — loop exit coupling

The `break` on line 18 (version check) and line 21 (success) mean the loop can exit early. The number of actual fetches depends on data, not just N. But N is the upper bound on how many times the version comparison is evaluated. If N increases, stale data may be written more times before the version check catches up.

---

## Hunt 3: Closed-Form Latent Invariants — Solve for the Break Point

### Hit 3.1: Lock TTL (300s) vs. total sync time

The Redis lock is set with a 300-second TTL (line 13). The total worst-case time for one sync_account call is:

```
total_time(N) = sum(10*(i+1) for i in range(N)) + sum(2**i for i in range(N))
              = 10*N*(N+1)/2 + 2^N - 1
```

Solving `total_time(N) = 300`:

- N=3: 67s < 300s (safe, 233s headroom)
- N=4: 115s < 300s (safe, 185s headroom)
- N=5: 181s < 300s (safe, 119s headroom)
- N=6: 279s < 300s (safe, 21s headroom)
- N=7: 431s > 300s (BROKEN — lock expires at ~300s, ~131s before sync finishes)

**Break point: N >= 7 causes the lock to expire mid-sync.**

When the lock expires:
1. A second `sync_account` call can acquire the lock (line 10).
2. Two concurrent syncs for the same account will run simultaneously.
3. Both will call `upstream.fetch`, potentially getting different data.
4. Both will call `db.write` — the second write may overwrite the first with stale data.
5. Both may emit `account.synced` events — duplicate events.
6. When the first sync finishes and calls `redis.delete`, it releases the lock that the second sync is still using.
7. A third sync can then start, compounding the inconsistency.

This is the single most critical coupling: **N=7 is the hard upper bound unless the lock TTL is also increased.**

### Hit 3.2: Lock ownership and `redis.delete` (line 26) — no ownership token

`redis.setnx` does not set an ownership token. The `redis.delete` at the end releases the lock unconditionally. If a non-`UpstreamError` exception (e.g., `ConnectionError`, `ValueError`, `KeyError`) escapes the try/except block, the function exits without reaching `redis.delete`. The lock persists until TTL (300s).

If N is increased and the sync takes longer, the probability of hitting a transient error that causes an early exit increases. The lock will block all future syncs for that account for 300 seconds — a denial-of-service for that account.

### Hit 3.3: `force=True` bypasses the lock (line 11-12)

When `force=True`, the lock is acquired but the guard is skipped. Two forced syncs can run concurrently. With N=3 this is a known risk. With larger N, the window for concurrent execution widens significantly, increasing the chance of data corruption.

---

## Hunt 4: Provenance — External Contracts

### Hit 4.1: Lock TTL = 300s — upstream SLA or infrastructure contract?

The 300-second lock TTL could be:
- An infrastructure constraint (Redis max key TTL, cluster configuration)
- An upstream service's session/connection timeout
- A deliberate design choice to balance between "long enough for sync" and "short enough to not block recovery"

**Risk:** If 300s is an external contract (e.g., a load balancer timeout, a Redis cluster max TTL, or an SLA), it cannot be changed without coordination.

### Hit 4.2: `timeout = 10 * (attempt + 1)` — upstream service contract?

The base timeout of 10 seconds could be:
- The upstream service's expected response time
- A network timeout configured in the infrastructure
- A value negotiated with the upstream service team

**Risk:** If the upstream service has its own timeout (e.g., a 30-second gateway timeout), increasing the fetch timeout beyond that is pointless — the upstream will cut the connection first.

### Hit 4.3: `emit_event("account.synced", ...)` and `emit_event("account.sync_failed", ...)` — event contract?

These events are consumed by downstream systems. Changing the retry count affects:
- **Frequency:** More retries = fewer `sync_failed` events (the sync has more chances to succeed)
- **Timing:** `sync_failed` fires later (at attempt N-1 instead of attempt 2)
- **Volume:** More retries = more `synced` events if the extra retries succeed

**Risk:** Downstream consumers may have expectations about event timing, frequency, or ordering. A consumer that triggers an alert after 3 consecutive failures would need to be updated if N changes.

### Hit 4.4: `2 ** attempt` backoff — is this a rate-limiting contract?

The exponential backoff may be designed to respect upstream rate limits. Increasing N increases total backoff time, which could be beneficial (less rate-limiting pressure) or harmful (longer sync times).

**Risk:** If the upstream service has a rate limit of X requests per minute, the backoff formula `2 ** attempt` was likely chosen to stay under that limit with N=3. Changing N changes the total request rate.

### Hit 4.5: `data.get('version') <= get_local_version(account_id)` — version contract?

The version comparison uses `<=` (less-than-or-equal). This means:
- If the upstream version equals the local version, the loop breaks (no re-write).
- This is an idempotency guard: if the data hasn't changed, don't write.

**Risk:** With more retries, the same data may be fetched and written multiple times before the version check catches up. If `db.write` has side effects beyond the database (e.g., triggers, indexes, audit logs), these side effects fire on every write, not just on data changes.

---

## Hunt 5: Substitute Degenerate and Extreme Values

### N=0: Silent no-op

- `range(0)` produces no iterations.
- The lock is acquired and released immediately.
- No fetch, no write, no event.
- **Behavior:** The function becomes a lock-acquire-and-release with no actual work. This is likely not a valid operational mode — callers expect sync to happen.

### N=1: Single attempt, no retry

- `range(1)` produces only attempt=0.
- `attempt == 2` never fires — the failure event is never emitted.
- `2 ** 0 = 1` — only 1 second of sleep (but no sleep happens because the loop exits after one iteration).
- `timeout = 10 * 1 = 10` — only 10s timeout.
- **Behavior:** The failure event is completely broken. If the single attempt fails, no `sync_failed` event fires. This is a silent failure.

### N=2: Two attempts

- `attempt == 2` never fires (attempts are 0, 1).
- Same problem as N=1: the failure event is never emitted.
- **Behavior:** Same silent failure as N=1.

### N=3: Current default (baseline)

- All expressions work as designed.
- Lock TTL (300s) >> total time (67s). Safe.

### N=4 through N=6: Gradual degradation

- N=4: total time = 115s, lock headroom = 185s. Safe but tighter.
- N=5: total time = 181s, lock headroom = 119s. Getting close.
- N=6: total time = 279s, lock headroom = 21s. Dangerous — any slow network or slow upstream pushes this over.

### N=7+: Lock expiration and data corruption

- Lock expires mid-sync. Concurrent syncs run. Data corruption.
- This is the critical break point.

### N=10: Extreme case

- Total time = 1573s (~26 minutes).
- Lock expires ~1273s before sync finishes.
- Maximum timeout per fetch = 100s.
- Maximum backoff = 512s per attempt.
- The function is effectively unusable in production.

---

## Summary of All Couplings Found

| # | Coupling | Location | Type | External Contract? |
|---|----------|----------|------|-------------------|
| 1 | `attempt == 2` | Line 23 | Algebraic alias (off-by-one) | No |
| 2 | `2 ** attempt` backoff | Line 25 | Scaling coupling (exponential) | Possibly (rate limit) |
| 3 | `10 * (attempt + 1)` timeout | Line 16 | Scaling coupling (linear) | Possibly (upstream timeout) |
| 4 | Lock TTL 300s vs. total sync time | Lines 13, 14-26 | Latent invariant (break at N=7) | Possibly (infrastructure) |
| 5 | `redis.delete` without ownership | Line 26 | Race condition (lock steal) | No |
| 6 | `force=True` bypasses lock | Lines 11-12 | Concurrency risk (widens with N) | No |
| 7 | `emit_event("account.sync_failed")` | Line 24 | Event contract (timing/frequency) | Yes (downstream consumers) |
| 8 | `emit_event("account.synced")` | Line 20 | Event contract (volume) | Yes (downstream consumers) |
| 9 | `data.get('version') <= ...` | Line 17 | Idempotency coupling (writes per retry) | No |
| 10 | `range(3)` loop bound | Line 14 | Primary declaration | No |
| 11 | Non-`UpstreamError` exception path | Lines 15-25 | Lock leak (no delete on unexpected error) | No |
| 12 | `setnx` without atomic TTL | Line 10 | Race condition (crash between setnx and expire) | No |

---

## Questions That Must Be Answered Before Making the Change

1. **What is the maximum reasonable value for N?** Based on Hunt 3, N=6 is the absolute maximum before lock expiration. N=7+ causes data corruption. Is there a use case for N > 3?

2. **Is the lock TTL (300s) an external contract?** Can it be increased if N is increased? Or should the lock TTL scale with N?

3. **Who consumes `account.synced` and `account.sync_failed` events?** Do downstream systems have SLAs or expectations about event timing?

4. **Does the upstream service have its own timeout?** If so, is the `10 * (attempt + 1)` formula bounded by that external timeout?

5. **Is the exponential backoff (`2 ** attempt`) designed to respect upstream rate limits?** If N increases, does the total request rate stay within the upstream's rate limit?

6. **What is the default value for the configurable parameter?** It must default to 3 to preserve current behavior.

7. **Where should the configurable value come from?** Environment variable? Config file? Database? API parameter?

8. **Are there existing tests for `sync_account`?** If so, they must be updated. If not, characterization tests should be written first.

9. **What does `git log` / `git blame` say about why 3 was chosen?** Was it a deliberate design decision or a guess?

10. **What happens if N=0 or N=1?** Should these be rejected with an error, or are they valid (if unusual) configurations?

---

## Recommended Change Strategy

1. **Add a parameter `retries=3`** to the function signature.
2. **Replace `range(3)`** with `range(retries)`.
3. **Replace `attempt == 2`** with `attempt == retries - 1`.
4. **Add a guard:** reject `retries < 1` (or `retries < 0` if N=0 is valid).
5. **Consider scaling the lock TTL** with N: `redis.expire(f"sync:{account_id}", max(300, total_time_estimate(retries)))`.
6. **Add ownership to the lock:** use `redis.set(key, value, nx=True, ex=ttl)` instead of separate `setnx` + `expire`.
7. **Add a try/finally** around the entire function to ensure `redis.delete` is always called.
8. **Update or write tests** covering N=1, N=3 (default), N=6 (boundary), and N=7 (lock expiration).