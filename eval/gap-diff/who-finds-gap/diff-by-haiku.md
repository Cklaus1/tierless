# What B (Fable) Caught That A (Haiku) Missed — and the Disciplines Behind It

## Summary

B found 8 distinct issues that A did not surface. These fall into 5 repeatable process disciplines — general instructions a reviewer can follow on any legacy code to reliably find this class of issue.

---

## The 5 Disciplines

### 1. Enumerate Every Statement in the Try Block Against Its Except Clause

**What B found:** B asked whether `UpstreamError` could be raised by `get_local_version`, `db.write`, or `emit_event` — not just `upstream.fetch`. A only considered `upstream.fetch` as the source of `UpstreamError`.

**Discipline:** For every `except X` clause, list every statement inside the corresponding `try` block. Ask: "Can this statement raise X?" If the caught exception type is broad or aliased (e.g., a generic `NetworkError` wrapping multiple underlying errors), the risk of mis-attribution is higher. This catches hidden exception paths that change retry semantics.

### 2. Question Every Parameter's Semantics and Cross-Knob Interactions

**What B found:** B asked what `force` means and whether it should influence the retry count. A completely ignored the `force` parameter.

**Discipline:** For every function parameter, ask: "What does this parameter mean?" and "Should it affect other knobs in the function?" When making one parameter configurable, check whether other parameters already encode assumptions about its value. This catches cross-knob coupling that a single-knob change would break.

### 3. Check Whether Dependencies Already Implement the Same Pattern

**What B found:** B asked whether `upstream.fetch` has its own internal retry logic, which would create double-retry or compounding backoff. A did not check this.

**Discipline:** For each external call in the function, check whether the dependency already implements the same pattern (retry, backoff, timeout, rate limiting). This catches double-retry, compounding backoff, and hidden amplification that only appears when you change the outer loop.

### 4. Scan for Time-of-Check–Time-of-Use (TOCTOU) Gaps Between Sequential Reads

**What B found:** B identified the race between `upstream.fetch` and `get_local_version` — the local version could change between the fetch and the comparison. A did not flag this.

**Discipline:** For any sequence of read-check-modify operations, ask: "Could the state change between the read and the check?" This is especially relevant when the function holds a lock (distributed or otherwise) — the lock serializes entry but not the internal reads. This catches silent data corruption or unexpected control-flow branches.

### 5. Ask About Transactionality of Side-Effect Sequences

**What B found:** B asked whether `db.write` is transactional and what happens if the function crashes between `db.write` and `emit_event`. A did not ask this.

**Discipline:** For any sequence of side-effecting operations (write, emit, delete, update), ask: "Is the sequence atomic?" and "What happens if we crash between steps?" This catches partial-state scenarios where a retry change amplifies the window for inconsistency.

---

## Additional Findings (Single-Issue Observations)

These are things B found that A missed, but they are specific observations rather than generalizable disciplines:

- **`redis.setnx` deprecation** — B noted the method is deprecated in modern Redis clients, signaling potential version constraints. (A did not mention this.)
- **`get_local_version` exception propagation** — B noted it has no try/except and would propagate unhandled. (A did not call this out.)
- **No circuit breaker** — B explicitly noted the absence of a circuit breaker and recommended one. (A did not mention circuit breakers.)

---

## Why A Missed These

A's analysis was strong on the *direct* couplings to the constant `3` (it actually found more direct couplings than B, including the lock-TTL math and the wasted final sleep). But A's approach was more *local* — it stayed close to the function body and the constant `3`. B took a wider view: it questioned the parameters, the dependencies, the missing patterns, and the gaps between operations. The disciplines above encode that wider view as repeatable steps.