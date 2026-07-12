# Code archaeology: making the retry count configurable in `sync_account`

The change looks like a one-liner (`range(3)` → `range(retries)`), but the constant `3` is
load-bearing in at least four places, only one of which is spelled "3". Below: the direct
couplings in the code, the questions I'd need answered, the hidden dependencies and risks, and a
concrete pre-change checklist.

---

## 1. Direct couplings to the constant `3` inside the function

1. **`for attempt in range(3)`** — the obvious one.

2. **`if attempt == 2:` (line 23)** — a second, disguised copy of the constant. This is
   `retries - 1`, the "last attempt" check that gates the `account.sync_failed` event. If you
   change the loop bound and miss this, then:
   - with `retries > 3`, `sync_failed` fires on attempt 3 while retries continue — a **false
     failure event** possibly followed by success (consumers see `sync_failed` then
     `account.synced` for the same account);
   - with `retries < 3`, `sync_failed` **never fires** — silent failures, dead alerts.
   This must become `attempt == retries - 1` (or better, restructured with a `for/else`).

3. **`timeout=10 * (attempt + 1)`** — per-attempt timeout scales linearly with the attempt
   index. It is implicitly bounded at 30s only because there are 3 attempts. With `retries=10`
   the final attempt waits up to 100s. Question: was "max 30s" an intentional contract with the
   upstream (LB timeout, server-side limit)? Does an unbounded per-attempt timeout even make
   sense, or should it be capped?

4. **`time.sleep(2 ** attempt)`** — exponential backoff with no cap. Total sleep is
   `2^retries - 1` seconds. At 3 retries that's 7s; at 10 it's ~17 minutes of blocking sleep. No
   jitter either (thundering-herd risk grows with retry count during an upstream outage).

5. **`redis.expire(..., 300)` — the lock TTL is silently sized to 3 attempts.** Worst-case
   runtime today is roughly `sum(10*(i+1)) + sum(2^i)` = 60s of timeouts + 7s of sleeps ≈ 67s,
   comfortably under 300s. Generalized, worst case ≈ `5·N·(N+1) + 2^N − 1` seconds:
   - N=6 → ~273s (already brushing the TTL)
   - N=7 → ~407s (**exceeds the lock TTL**)
   If the function outlives its lock, a second `sync_account` starts concurrently (defeating the
   lock entirely), and worse — see the `redis.delete` risk in §3. **The lock TTL must become a
   function of the retry count (or the retry count must be capped so worst case stays well under
   the TTL).**

6. **The wasted final sleep.** On the last failed attempt the code emits `sync_failed` and then
   *still sleeps* `2^(retries-1)` seconds before exiting — while holding the lock. Today that's a
   harmless 4s. At `retries=8` it's a pointless 128s of lock-holding after the outcome is already
   decided. Pre-existing inefficiency that the change amplifies; worth fixing in the same pass
   (skip the sleep on the final attempt).

---

## 2. Questions I'd need answered before touching it

### Semantics of the new knob
- **"Retries" or "attempts"?** Today `range(3)` means 3 total *attempts*. If the config is named
  `retries` people will expect 3 to mean "1 try + 3 retries" = 4 attempts. Off-by-one naming
  bugs here are classic. Pick a name (`max_attempts`?) and document it.
- **What are legal values?** `retries=0` makes `range(0)` a no-op: the function acquires the
  lock, does *nothing* — no fetch, no write, no `sync_failed` event — and releases the lock. Is
  0 valid ("disable sync")? Should it raise? Negative values? Is there a sane upper cap (given
  the TTL math above)?
- **Where does the value come from?** A new function parameter, a module/global setting, env
  var, per-account config, feature flag? Each has different blast radius:
  - *Function param with default 3*: safest, but only helps callers that pass it.
  - *Global config*: changes behavior for every caller at once, including ones you haven't found.
  - *Per-account*: now the lock TTL / worst-case runtime varies per account.
- **Can it change at runtime** (hot-reloaded config)? If so, can it change *mid-loop*? Read it
  once at function entry.

### Callers and execution context
- **Who calls `sync_account`, and from where?** Web request handler, cron, Celery/RQ task,
  Kafka consumer, CLI backfill script? I need every call site because:
  - If it's a **queued task**, the signature is part of a serialization contract. During a
    rolling deploy, old workers may receive new-signature invocations (or vice versa). A
    keyword-only param with a default is the safe shape; a positional param is not.
  - If it runs in a **request path**, the caller's timeout (gateway, uWSGI harakiri, ALB idle
    timeout) bounds how many retries are even survivable. Today's ~67s worst case may already be
    marginal; raising retries could turn slow failures into worker kills — which, because
    there's no `try/finally`, **leak the Redis lock** for up to 300s.
  - Does any caller pass `force=True`, and why? (See lock semantics below.)
- **Is `time.sleep` real or monkey-patched?** Under gevent/eventlet it yields; under plain
  threads it pins a worker. During an upstream outage, worker-pool exhaustion scales linearly
  with total retry duration. How many concurrent `sync_account` calls happen in practice?
- **Is anything else keyed to the number 3?** Grep the whole codebase and configs for retry
  assumptions: tests asserting `fetch` called exactly 3 times, mocks with 3 canned responses,
  runbooks/docs saying "we retry 3 times", dashboards computing "attempts per sync = 3 ×
  failures", upstream rate-limit budgets sized for 3× traffic amplification.

### The lock (mostly pre-existing bugs the change can trip)
- **`setnx` + `expire` is not atomic.** A crash between lines 10 and 13 leaves a lock with **no
  TTL — a permanent deadlock** for that account until someone deletes the key manually. Not
  caused by my change, but if I'm increasing runtime/failure surface I'm increasing the odds of
  hitting it. (Modern fix: `SET key val NX EX 300`.)
- **`force=True` is not "skip the lock", it's "trample the lock."** With `force=True` and the
  lock already held by another process:
  1. `redis.expire` **resets the other holder's TTL** to 300s;
  2. two syncs now run concurrently for the same account;
  3. `redis.delete` at the end **deletes the other process's lock**, letting a *third* sync in.
  Do the people who call with `force=True` know this? Does anything depend on it?
- **`redis.delete` is unconditional and unowned.** No lock token / compare-and-delete. If my run
  exceeds the TTL (which longer retry counts make possible — §1.5), the lock expires, someone
  else acquires it, and my `delete` at the end frees *their* lock. This is the concrete
  mechanism by which "just bump retries to 8" causes cascading concurrent syncs.
- **No `try/finally`.** Any exception other than `UpstreamError` (see below) exits the function
  with the lock held for the remaining TTL — up to 5 minutes of sync outage for that account per
  incident. More retries = more wall-clock time in the danger zone.
- **Does anything else read or write `sync:{account_id}`?** Health checks, admin tooling, other
  services sharing the Redis instance/namespace?

### Exception and data-shape surface
- **What actually raises `UpstreamError`?** Presumably `upstream.fetch`, but the `try` block
  also covers `get_local_version`, `db.write`, and `emit_event`. If any of *those* can raise
  `UpstreamError` (e.g., wrapped errors), then a retry after a successful `db.write` re-fetches,
  the version check now sees `version <= local`, breaks, and **`account.synced` is never
  emitted** for a write that happened — an event silently lost. Conversely, if `db.write`
  raises `UpstreamError` *after* partially writing, retries could double-write / double-emit. Is
  `db.write` idempotent? Is `emit_event` at-least-once safe for consumers? Raising the retry
  count raises the number of chances to hit these windows.
- **`data.get('version')` can be `None`** (missing key) → `None <= int` is a `TypeError` in
  Python 3 → uncaught → lock leaked until TTL. Also `data['version']` on line 20 vs
  `data.get('version')` on line 17 — inconsistent trust in the payload. Not my bug, but I should
  know whether malformed payloads occur before I increase how long we hold locks.
- Exceptions from `db.write` / `emit_event` that are *not* `UpstreamError` abort the loop
  entirely — the retry knob does **not** retry those. Worth stating in the config's docstring so
  nobody sets `retries=10` expecting it to paper over DB flakiness.

### Events and their consumers
- **Who consumes `account.sync_failed` and `account.synced`?** Alerting rules, downstream
  materializers, billing, audit? Changing retry count changes:
  - **failure latency**: `sync_failed` currently arrives ≤ ~67s after start; at N=7 it could be
    ~7 minutes. Any consumer with a "sync should complete within X" watchdog?
  - **failure frequency**: more retries → fewer `sync_failed` events. If an SLO/alert is tuned
    to the current rate, it goes quiet (or, with fewer retries, noisy) without the underlying
    reality changing.
  - Note `sync_failed` carries no version and there's no event at all when the loop exhausts —
    the function returns `None` in every path, so **callers cannot distinguish**
    success / skipped-due-to-lock / version-already-current / total failure. Anyone who wants
    per-attempt visibility after this change won't get it.
- Is `emit_event` synchronous and can *it* fail? (Covered by the try — see above.)

### Upstream contract
- **Rate limits / SLA on `upstream.fetch`?** During an upstream incident, every account's sync
  goes from 3 requests to N requests, with per-request timeouts growing to `10·N` seconds —
  amplified load exactly when the upstream is least able to handle it. Is there a rate-limit
  budget, and does the upstream team need to sign off on the new ceiling?
- Does the upstream have a server-side timeout that makes `timeout=40, 50, ...` pointless
  (connection cut at 30s regardless)?
- Are `fetch` calls billed/metered?

---

## 3. Hidden dependencies & risks (summary table)

| # | Dependency / risk | Trigger | Blast radius |
|---|---|---|---|
| 1 | `attempt == 2` last-attempt check | Any change to loop bound | False or missing `sync_failed` events; broken alerting |
| 2 | Lock TTL 300s sized for N=3 (~67s worst case) | N ≥ 7 (worst case > 300s); marginal at N=6 | Concurrent syncs; unconditional `delete` frees the next holder's lock → cascade |
| 3 | Per-attempt timeout `10·(attempt+1)` unbounded | Large N | 100s+ socket waits; worker starvation; possibly moot vs upstream's own timeout |
| 4 | Uncapped, unjittered `2^attempt` backoff | Large N | Minutes of blocking sleep per call; synchronized retry storms |
| 5 | Final-attempt sleep after `sync_failed` | Any N | Wasted `2^(N-1)`s lock hold after outcome decided |
| 6 | `range(0)` no-op path | `retries=0` misconfig | Sync silently disabled, no event, no error |
| 7 | Non-atomic `setnx`/`expire` | Crash between them | Permanent per-account lock (no TTL) |
| 8 | `force=True` resets/deletes another holder's lock | Concurrent force + normal sync | Duplicate concurrent syncs, triple-entry after delete |
| 9 | No `try/finally` around lock release | Any uncaught exception (`TypeError` on `version=None`, DB errors, worker kill) | Account sync blocked up to 300s |
| 10 | `try` block covers `db.write`/`emit_event`, not just `fetch` | Those raising `UpstreamError` | Lost `account.synced` events or double writes on retry |
| 11 | Task-queue / RPC signature contract | Adding a positional param; mixed-version rolling deploy | Task deserialization failures |
| 12 | Tests/mocks/docs/dashboards assuming 3 | Any change | Broken tests, misleading runbooks, mis-tuned alerts |
| 13 | Upstream load amplification | Raising N fleet-wide during upstream outage | Rate limiting, cascading upstream failure |
| 14 | Caller-side timeouts (gateway, harakiri, task `time_limit`) | Longer worst-case runtime | Killed workers → leaked locks (see #9) |
| 15 | Config source & mutability | Global/hot-reloaded config | Behavior change for unaudited callers; mid-loop value drift |

---

## 4. What I'd actually check before making the change (checklist)

1. **Find every call site** of `sync_account` (grep, plus dynamic dispatch: task registries,
   URL routes, cron definitions, `getattr` calls). Classify each by execution context (request /
   worker / cron / CLI) and note which pass `force=True`.
2. **Grep for the lock key pattern** `sync:` across the codebase, ops scripts, and runbooks —
   anything else that reads, writes, monitors, or manually clears these keys.
3. **Find consumers of `account.synced` and `account.sync_failed`** (event schema registry,
   subscribers, alert definitions, dashboards). Ask owners whether failure *latency* and
   *frequency* changes matter to them.
4. **Read `upstream.fetch`**: what raises `UpstreamError` (is it only network/5xx, or also 4xx,
   auth, rate-limit responses — retrying a 401 forever is pointless), whether it's idempotent,
   and any client-side or server-side timeout ceilings and rate limits. Same for `db.write`
   (idempotency, can it raise `UpstreamError`) and `emit_event` (sync/async, failure modes).
5. **Check production telemetry** for the current distribution of: attempts per sync, sync
   duration, lock contention (how often does `setnx` fail), `sync_failed` rate, and whether any
   syncs already approach the 300s TTL. This tells you real headroom, not theoretical.
6. **Run the TTL math** for the intended maximum retry value (`≈ 5N(N+1) + 2^N − 1` seconds
   worst case) and decide: cap N, scale the TTL with N, or (properly) fix the lock (atomic
   `SET NX EX`, token + compare-and-delete, `try/finally`).
7. **Inventory the tests**: which assert call counts, sleep sequences, timeout values, or event
   emission on "attempt 3"? They encode today's contract and will (correctly) fail.
8. **Check the deploy story** if the function is a serialized task: keyword-only param with
   default `3`, deployed workers-first, so mixed fleets stay compatible.
9. **Decide scope with the requester**: strictly "make 3 configurable" (default 3, cap it,
   keep behavior at default bit-identical), vs. bundling the safety fixes the change exposes
   (timeout/backoff caps, jitter, skip final sleep, `try/finally`, atomic lock). My
   recommendation: land the config knob behavior-preserving, and file/fix the lock issues as an
   explicit follow-up — but *cap the knob* (e.g., ≤ 5) so the TTL invariant can't be violated in
   the meantime.
10. **Validate the new config at the boundary**: integer, `>= 1` (or explicitly define 0),
    `<=` cap; read once at function entry; log the effective value on failure paths so incidents
    are debuggable.

## 5. The minimal-correct edit (once the above is answered)

- Signature: `def sync_account(account_id, force=False, *, max_attempts=3)` (keyword-only,
  defaulted — behavior-identical for all existing callers, deploy-safe for task queues).
- Replace `range(3)` → `range(max_attempts)`.
- Replace `attempt == 2` → `attempt == max_attempts - 1` (or restructure with `for/else` so the
  failure event can't drift from the loop bound again).
- Skip the `time.sleep` on the final attempt.
- Validate `max_attempts` (int, `1 <= max_attempts <= CAP`) where `CAP` is derived from the lock
  TTL via the worst-case formula, with comfortable margin.
- Update tests that encode "3", and add tests for: `max_attempts=1` (fail event fires on first
  failure), `max_attempts=N` success-on-last-attempt (no fail event), and the invalid-value
  guard.
