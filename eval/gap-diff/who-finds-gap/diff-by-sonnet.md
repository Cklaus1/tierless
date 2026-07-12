# What B Caught That A Missed — and the Disciplines That Produced It

## The Gap

A (frontier) produced a deep **internal** analysis: it found the disguised constant (`attempt == 2`), the lock-TTL math, the wasted final sleep, the `force=True` lock-trampling, the `redis.delete` unowned release, the `range(0)` no-op path, the task-queue serialization contract, and the `for/else` restructuring suggestion.

B (cheaper) produced a broad **external** analysis: it found that `upstream.fetch` and `db.write` may have their own retry logic (double-retry), that `get_local_version` can raise unhandled, that `emit_event` is sync/async with no dead-letter queue, that downstream consumers depend on event ordering, that callers may implement their own retries, that `sync_account` may be called in a loop causing cascade starvation, and what the `force` parameter actually means.

A missed B's catches because A stayed inside the function's four walls. B's extra catches came from five repeatable process disciplines.

---

## Five Repeatable Process Disciplines

### 1. Trace Every External Dependency to Its Definition

**Instruction:** For every function call inside the target code (`upstream.fetch`, `db.write`, `emit_event`, `get_local_version`), locate its definition and read its signature, docstring, error surface, and internal retry logic. Do not assume the call is a simple pass-through.

**What this surfaces:** Nested retry loops (compound exponential backoff), unexpected exception types bubbling up, sync-vs-async behavior, idempotency guarantees, and whether the call itself has a timeout or rate limit. A assumed these were known; B explicitly questioned each one.

### 2. Map the Caller Ecosystem and Execution Contexts

**Instruction:** Find every call site of the target function. For each caller, determine: what execution context it runs in (web request, background worker, cron, CLI), whether it already implements its own retry or locking logic, and whether it calls the target in a loop over many items.

**What this surfaces:** Double-retry behavior (caller retries AND the function retries), cascade starvation (one slow call in a loop blocks all others), parameter semantics that only make sense in certain contexts (e.g., `force=True` meaning different things to a web handler vs. a backfill script), and serialization contracts (task queue signatures that must remain backward-compatible). A mentioned "who calls" but did not explore the implications of each caller's context.

### 3. Trace Event and Data Mutations Downstream

**Instruction:** For every event emitted and every data mutation inside the target code, follow the consumer chain. Ask: is delivery synchronous or asynchronous? Is there a dead-letter queue? Do consumers depend on ordering? What happens if the event is lost or duplicated?

**What this surfaces:** Silent event loss (data written but event not emitted), ordering violations (events arriving out of sequence), missing failure paths (no dead-letter queue), and alerting blind spots (consumers tuned to current event rates that go quiet or noisy after the change). B asked about event ordering and dead-letter queues; A did not.

### 4. Question Every Parameter's Actual Semantics

**Instruction:** For every parameter in the function signature, verify its documented and actual semantics. Do not infer meaning from context or naming. Ask: what does this parameter do in every code path? What does it mean when combined with other parameters? Is its behavior consistent across all callers?

**What this surfaces:** Semantic mismatches (a parameter named `force` that actually means "trample another process's lock" rather than "skip the lock"), edge-case behaviors (what happens when `force=True` and the lock is already held by another process), and parameters that should be renamed or restructured. B questioned `force=True`; A assumed it was about the lock without verifying.

### 5. Plan the Deployment and Rollout Story

**Instruction:** Before making any change, ask: how will this be rolled out? Is there a feature flag, A-B test, or gradual rollout mechanism? What is the rollback plan? Can the change be reverted without a code deploy? Are there mixed-version deployment risks (e.g., old workers receiving new-signature task invocations)?

**What this surfaces:** Deployment risk (no rollback path means any wrong config value requires a redeploy), mixed-version incompatibility (task queue serialization contracts during rolling deploys), and the absence of guardrails (no feature flag means the change is all-or-nothing). B asked about feature flags, A-B testing, and rollback; A did not.

---

## Summary

A's discipline was **deep static analysis of the function body** — finding every constant, every code path, every race condition inside the four walls. B's discipline was **broad external tracing** — following every dependency, caller, event consumer, and deployment path outward from the function.

The repeatable insight: when reviewing legacy code, static analysis of the function body alone is insufficient. You must also trace outward along every dependency, caller, event, and deployment path. The five disciplines above are the instructions that produce that outward tracing reliably, in any legacy codebase.