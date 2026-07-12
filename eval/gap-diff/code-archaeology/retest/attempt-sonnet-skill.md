# Constant-Coupling Skill Application: sync_account retry count (N=3)

## The Constant

N = 3, the hardcoded retry count in `range(3)` on line 14 of `sync_account`.

---

## Hunt 1: Algebraic Aliases (Off-by-One Shadows)

### Hit 1: `attempt == 2` (line 23)

- **Location:** `if attempt == 2:`
- **Why it is a copy of N:** This is `attempt == N - 1`. It fires the failure event only on the final attempt. It is correct only because the loop runs exactly 3 times.
- **Must become:** `attempt == N - 1` (or `attempt == retries - 1` once configurable)

### Hit 2: `range(3)` (line 14)

- **Location:** `for attempt in range(3):`
- **Why it is a copy of N:** The direct, named declaration.
- **Must become:** `for attempt in range(retries):`

No other algebraic aliases found. N+1=4 and N-1=2 do not appear elsewhere as standalone magic numbers.

---

## Hunt 2: Trace the Induction Variable into Every Expression It Feeds

The induction variable `attempt` takes values 0, 1, ..., N-1. Every expression it feeds:

### Hit 3: `timeout = 10 * (attempt + 1)` (line 16)

- **Value at final iteration:** 10 * N
- **Cumulative timeout budget across all attempts:** sum of 10*(i+1) for i=0..N-1 = 10 * N*(N+1)/2 = 5*N*(N+1)
- **Coupling:** The maximum per-request timeout scales linearly with N. At N=3, max timeout is 30s. At N=10, it is 100s. At N=30, it is 300s.
- **Risk:** If N is increased, the timeout on the last attempt grows proportionally. A caller waiting for this function will be blocked longer.

### Hit 4: `time.sleep(2 ** attempt)` (line 25)

- **Value at final iteration:** 2^(N-1)
- **Cumulative sleep across all attempts:** sum of 2^i for i=0..N-1 = 2^N - 1
- **Coupling:** The sleep on the final attempt grows exponentially with N. At N=3, final sleep is 4s. At N=10, it is 512s (8.5 minutes). At N=20, it is 524,288s (~6 days).
- **Risk:** Exponential growth means even moderate increases in N cause the function to hang for impractically long periods on repeated failures.

### Hit 5: Total worst-case wall-clock time

- **Formula:** 5*N*(N+1) + (2^N - 1)
- **At N=3:** 60 + 7 = 67 seconds
- **At N=5:** 150 + 31 = 181 seconds
- **At N=6:** 210 + 63 = 273 seconds
- **At N=7:** 280 + 127 = 407 seconds
- **At N=10:** 550 + 1023 = 1573 seconds (~26 minutes)

---

## Hunt 3: Closed-Form Latent Invariants; Solve for the Break Point

### Invariant 1: Redis lock TTL must outlast total work

The Redis lock is set with a 300-second TTL (line 13). The lock must survive until the function releases it via `redis.delete()` on line 26. If total worst-case time exceeds 300s, the lock expires by TTL, and a concurrent call with `force=False` will acquire a stale lock and run a second concurrent sync for the same account.

- **Break point:** 5*N*(N+1) + (2^N - 1) > 300
- **N=6:** 273s -- safe
- **N=7:** 407s -- **breaks**
- **Conclusion:** The lock TTL of 300s is safe for N up to 6. Beyond N=6, the lock can expire mid-execution.

### Invariant 2: Per-request timeout vs. lock TTL

The timeout on the last attempt is 10*N. If this single request takes longer than the lock TTL, the lock expires while the request is still in flight.

- **Break point:** 10*N > 300, i.e., N > 30
- **At N=30:** The last attempt's timeout equals the lock TTL.
- **At N>30:** The last attempt could outlive the lock by itself.

### Invariant 3: Cumulative timeout budget vs. lock TTL

The total timeout budget (sum of all per-request timeouts) must not exceed the lock TTL, otherwise the lock expires before all retry attempts can complete.

- **Break point:** 5*N*(N+1) > 300
- **N=7:** 280 -- still under 300
- **N=8:** 360 -- **breaks**
- **Conclusion:** The timeout budget alone exceeds the lock TTL at N=8.

### Invariant 4: Cumulative sleep vs. lock TTL

The total sleep time must not exceed the lock TTL.

- **Break point:** 2^N - 1 > 300
- **N=8:** 255 -- under
- **N=9:** 511 -- **breaks**
- **Conclusion:** Sleep alone exceeds the lock TTL at N=9.

### Summary of break points

| Constraint | Breaks at N= |
|---|---|
| Total time > lock TTL | 7 |
| Timeout budget > lock TTL | 8 |
| Sleep > lock TTL | 9 |
| Last-attempt timeout > lock TTL | 31 |

The tightest constraint is total time at N=7.

---

## Hunt 4: Provenance — External Contracts

### `300` (Redis TTL, line 13)

- **Classification: Likely external contract.** 300 seconds = 5 minutes is a standard timeout value used by many infrastructure components: HAProxy default timeout, nginx proxy_read_timeout default, common load balancer cutoffs, and typical SLA boundaries. Chesterton's fence applies: this value was likely chosen to match an upstream or middleware timeout, not arbitrarily.
- **Risk of scaling:** If N increases and total work exceeds 300s, the lock expires. Simply increasing N without also increasing the TTL would cause stale-lock concurrency bugs.

### `10` (base timeout multiplier, line 16)

- **Classification: Possible external contract.** The base timeout of 10 seconds may reflect an upstream service's expected response time or a negotiated SLA. It could also be a proxy/load balancer timeout boundary.
- **Risk of scaling:** If N increases, the per-request timeout on later attempts grows (10*N at the last attempt). This could exceed upstream service limits or proxy timeouts.

### `2` (sleep base, line 25)

- **Classification: Convention, possibly arbitrary.** Exponential backoff with base 2 is a standard pattern (AWS SDK, gRPC, etc.). The base of 2 is a design choice, not necessarily a negotiated value.
- **Risk of scaling:** The exponential growth is the primary driver of the lock-TTL break point. Changing the base or the retry count together has compounding effects.

### `3` (retry count, line 14)

- **Classification: Unknown -- needs investigation.** Could be an SLA requirement (e.g., "retry up to 3 times before escalating"), a protocol requirement, or an arbitrary operational choice.
- **Risk:** Without knowing the provenance, any change to N is risky. If it is an external contract, changing it requires coordination with the other party.

---

## Hunt 5: Substitute Degenerate and Extreme Values

### N = 0

- `range(0)` is empty -- the loop body never executes.
- The function acquires a Redis lock, sets a 300s TTL, and immediately releases the lock.
- **Bug:** The lock is held for ~0 seconds but the TTL is 300s. This creates a "zombie lock" that blocks all other `sync_account` calls for 5 minutes. Any caller with `force=False` will silently skip for 5 minutes.
- **Conclusion:** N=0 is not a valid configuration. The function should guard against N<=0.

### N = 1

- One attempt. `attempt == 0`, which equals `N-1`, so the failure event fires on the first (and only) failure.
- Timeout = 10s, sleep = 1s.
- Total worst-case time = 10 + 1 = 11s. Well within the 300s lock TTL.
- **Conclusion:** N=1 is safe and valid.

### N = 2

- Two attempts. Failure event fires on attempt 1.
- Timeout: 10s, then 20s. Sleep: 1s, then 2s.
- Total worst-case time = 30 + 3 = 33s. Safe.

### N = 5

- Five attempts. Failure event fires on attempt 4.
- Timeout: 10+20+30+40+50 = 150s. Sleep: 1+2+4+8+16 = 31s.
- Total worst-case time = 181s. Within 300s lock TTL. Safe.

### N = 6

- Six attempts.
- Timeout: 210s. Sleep: 63s.
- Total worst-case time = 273s. Within 300s lock TTL. Safe, but only 27s of headroom.

### N = 7

- Seven attempts.
- Timeout: 280s. Sleep: 127s.
- Total worst-case time = 407s. **Exceeds 300s lock TTL.** Lock expires mid-execution. Stale-lock concurrency bug.

### N = 10

- Ten attempts.
- Timeout: 550s. Sleep: 1023s.
- Total worst-case time = 1573s (~26 minutes). Lock expired 1273s ago.

### N = 20

- Twenty attempts.
- Sleep alone = 2^20 - 1 = 1,048,575s (~12 days).
- The function would hang for over 12 days on repeated failures.

---

## Complete Enumeration of All Disguised Copies of N

| # | Location | Line | Disguised Form | Must Become |
|---|---|---|---|---|
| 1 | `range(3)` | 14 | Direct N | `range(retries)` |
| 2 | `attempt == 2` | 23 | N-1 | `attempt == retries - 1` |
| 3 | `timeout = 10 * (attempt + 1)` | 16 | Scales with N: max = 10*N | No change needed if N is configurable; the formula is already correct as a function of attempt |
| 4 | `time.sleep(2 ** attempt)` | 25 | Scales with N: max sleep = 2^(N-1) | No change needed if N is configurable; the formula is already correct as a function of attempt |

## Coupled Constants That Must Change in Lockstep

| Constant | Location | Relationship to N | Must change if N changes? |
|---|---|---|---|
| 300 (Redis TTL) | Line 13 | Must exceed total worst-case time: 5*N*(N+1) + 2^N - 1 | **Yes, if N >= 7** |
| 10 (timeout base) | Line 16 | Per-request timeout = 10*(attempt+1); max = 10*N | Consider if N increases significantly |
| 2 (sleep base) | Line 25 | Sleep = 2^attempt; max = 2^(N-1) | Consider if N increases significantly |

## External Contract Classification

| Constant | Likely External Contract? | Confidence | Action Required |
|---|---|---|---|
| 300 (TTL) | Yes | High | If N >= 7, increase TTL or cap N |
| 10 (timeout base) | Possible | Medium | Investigate upstream service config |
| 2 (sleep base) | No (convention) | High | Safe to keep |
| 3 (retry count) | Unknown | Low | **Must investigate before changing** |

## Risks and Hidden Dependencies

1. **Stale lock concurrency (N >= 7):** The Redis lock TTL of 300s is the tightest coupling. If N is increased to 7 or above, the lock expires before the function completes on repeated failures. A second concurrent call with `force=False` will acquire the stale lock and run a duplicate sync, potentially causing data corruption or duplicate events.

2. **Zombie lock at N=0:** Setting retries to 0 creates a 300-second lock that blocks all other syncs for the same account, with no actual work performed.

3. **Unbounded wall-clock time:** The exponential sleep (2^attempt) means total sleep time grows as 2^N. At N=10, total sleep is 17 minutes. At N=20, it is 12 days. There is no upper bound on N in the function.

4. **Upstream service impact:** Each retry sends a fetch request to the upstream service. Increasing N increases the load on the upstream proportionally. At N=10 with exponential backoff, the total timeout budget is 550s and total sleep is 1023s -- the upstream service sees 10 requests over ~26 minutes.

5. **Event semantics change:** The failure event fires on the last attempt. If N changes, the number of successful attempts before a failure event changes. Downstream consumers of `account.sync_failed` may have expectations tied to the current N=3 behavior.

6. **Version comparison semantics:** `data.get('version') <= get_local_version(account_id)` breaks the loop on success or on seeing an old version. This is independent of N but interacts with it: if the upstream version is always behind, the function succeeds on the first attempt regardless of N. If the upstream version is always ahead, it retries N times.

7. **Force flag bypass:** The `force=True` flag allows a second concurrent sync even while a lock exists. This is a separate code path that does not depend on N, but the interaction between force and retries is worth noting: force bypasses the lock but does not change the retry behavior.

## Recommended Guardrails Before Making N Configurable

1. **Add a minimum bound:** `if retries < 1: retries = 1` (or raise an error). N=0 is a zombie-lock bug.
2. **Add a maximum bound:** Cap N at 6 to stay within the 300s lock TTL, or increase the TTL in lockstep.
3. **Increase TTL if N increases:** If N >= 7, the TTL must be increased to at least 5*N*(N+1) + 2^N - 1.
4. **Investigate provenance of N=3:** Determine if 3 is an external contract before changing it.
5. **Investigate provenance of TTL=300:** Determine if 300 is an external contract before changing it.
6. **Consider adding a total timeout or deadline:** Instead of relying on per-request timeouts and sleeps, add an overall deadline to prevent unbounded execution.