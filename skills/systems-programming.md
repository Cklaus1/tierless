---
name: systems-programming
description: Systems-programming skill — discipline for OS, kernel, embedded, and other close-to-metal work: invariants explicit, concurrency proven, failure injected
metadata:
  type: user
---

# Systems Programming — Close-to-Metal Skill

## Why

Application code that's wrong throws an exception. Systems code that's wrong corrupts memory, deadlocks under load, or works for six months and then loses data during a power cut. Smaller models write systems code with application habits: trusting the happy path, ignoring partial failure, treating concurrency as a library detail. This skill is the discipline for code where the machine's real behavior — races, reordering, torn writes, resource exhaustion — is the problem domain.

## The Rule

**Every shared resource, every ownership transfer, and every failure point is documented before the code is written — and each one gets a test that forces the bad case.** In systems code, "it passed the tests" means nothing unless the tests include contention, exhaustion, and crash.

## How to Apply

### 1. State the invariants in writing

Before implementing, list in the plan (plan-mode artifact):
- **Ownership**: who allocates, who frees, who may hold a reference when (even in GC'd languages: who closes the fd, who releases the lock)
- **Concurrency**: what is shared, what lock/atomic protects it, and the *lock ordering* (deadlock is a design bug, not a runtime surprise)
- **Lifetimes**: what may outlive what; what happens to in-flight work at shutdown

Use the invariant table — one row per shared resource:

```markdown
| resource | protected by | lock order | outlives |
|---|---|---|---|
| conn pool | pool_mutex | 1st (before per-conn) | worker threads |
```

### 2. Design the failure envelope

For each external interaction (syscall, allocation, I/O, IPC): what does the code do when it fails? "It won't fail" is not an answer — allocation fails, disks fill, `write()` returns short, signals interrupt. Every error path is either handled or explicitly `abort()`-ed with a reason; silent fallthrough is the bug factory.

### 3. Test what application code doesn't

- **Contention**: run the concurrent paths under stress (thread sanitizer, loom-style model checking, or at minimum a hammer test with N threads × M iterations)
- **Exhaustion**: inject allocation failure, fd exhaustion, full disk — fault-injection hooks are part of the design, not an afterthought
- **Crash consistency**: for anything persistent, kill -9 mid-write and verify recovery; if you haven't tested the recovery path, you don't have one
- **Sanitizers always on in CI**: ASan/UBSan/TSan (or the ecosystem equivalent) — a clean sanitizer run is a pass condition, not a nice-to-have

### 4. Measure, don't guess

Performance claims require numbers from the *target* environment — the full process is the **performance-optimization** skill. Systems-specific addendum: the metrics that matter here are cache behavior, syscall counts, and allocation rates, not wall-clock alone.

### 5. Respect the platform contract

Systems bugs live in the gap between what a primitive plausibly does and what it actually does (`fsync` guarantees, mutexes across `fork`, signal-safety). The process: in the plan artifact, list the primitives used and cite the guarantee relied on for each — from the man page or spec, not from memory.

## Anti-Patterns

- Locks added until the race "goes away" (races hide; they don't go away — prove the protection, or restructure to share less)
- Ignoring return values of close/write/fsync (that's where the data loss is)
- "It works on my machine" for timing-dependent code — your machine is one interleaving of millions
- Optimizing based on intuition about "fast" and "slow" without a profile
- Rolling your own lock-free structure when a mutex would do (lock-free is a research project wearing a performance costume)
- Testing shutdown never, then discovering the deadlock lives there

## Verification

Done means evidence, not vibes:
- Sanitizer run output (ASan/UBSan/TSan or ecosystem equivalent) attached to the verify artifact — clean, with the command that produced it
- For anything persistent: kill-9 recovery test log attached, showing the crash point and the successful recovery
- The invariant table from §1 exists in the plan artifact; verdict is PASS/FAIL against these three
