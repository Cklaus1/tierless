---
name: performance-optimization
description: Performance-optimization skill — profile-before-optimize as a loop: measure, find the actual bottleneck, fix one thing, measure again; no speculative tuning
metadata:
  type: user
---

# Performance Optimization — Measure-First Skill

## Why

Smaller models optimize by vibes: they see a loop and unroll it, see a query and cache it, see an allocation and pool it — usually in code that accounts for 2% of runtime, while the actual bottleneck (one N+1 query, one accidental O(n²), one sync call in a hot path) sits unmeasured. Intuition about where time goes is wrong so reliably that acting on it has negative expected value. This skill is the debugging skill's twin: hypothesis-driven, evidence-gated, one change at a time.

## The Rule

**No optimization without a profile showing the bottleneck, a target number defining "fast enough," and a before/after measurement proving the change worked.** An optimization without all three is a refactor with extra risk and a story attached.

Artifact: `.claude/plans/{task-name}-perf.md`:

```markdown
## Perf: {task-name}
**Target number:** {the "done" number, from requirements}
**Profile evidence:** {tool, workload, where the time/memory goes}
**Bottleneck named:** {the debugging-style hypothesis}
**Change made:** {one change per cycle}
**Before / after:** {same load, same data, same environment}
```

## The Loop

1. **Define done.** A number, from requirements: "p95 < 300ms at 200 rps", "import completes in < 5 min for 1M rows", "60fps on the mid-tier device." Without a target, optimization never terminates — it just stops when someone gets bored.
2. **Measure the real workload.** Profile production or a production-shaped load (realistic data sizes, realistic concurrency — see database-design on empty-DB fiction). Microbenchmarks of suspected functions come *later*, if ever; the system profile comes first.
3. **Find the bottleneck, name it.** Where does the time/memory actually go? State it like a debugging hypothesis: "62% of request time is in `resolve_permissions`, called 40× per request because nothing memoizes per-request." If the profile surprises you — and it usually does — that's the skill working.
4. **Fix ONE thing.** The biggest bar in the profile. One change per measurement cycle, or you can't attribute the result.
5. **Measure again, same conditions.** Improvement is real only under the same load, same data, same environment. Keep the harness in the repo so the measurement is repeatable.
6. **Stop at the target.** Hitting "done" ends the loop. Further optimization is spending complexity budget on a solved problem.

## Optimization Order (cheapest wins first)

1. **Do less work**: N+1s, redundant calls, fetching unneeded columns/fields, recomputing invariants inside loops
2. **Better algorithm/data structure**: the O(n²) hiding in a `list.contains` inside a loop beats any micro-tuning of it
3. **Batch and cache**: with invalidation designed at cache-introduction time, not patched after the first staleness bug
4. **Parallelize**: after the serial path is sane — parallelizing waste just wastes faster
5. **Micro-optimize**: last, rarely, only with a profiler proving the hot loop and a benchmark guarding the win

## Regression Defense

- Performance targets that matter get CI benchmarks with failure thresholds — perf regressions arrive silently, one innocent commit at a time
- Record each optimization in `.claude/plans/{task-name}-perf.md` (the artifact above): bottleneck found, change made, before/after numbers. Six months later, "why is this code weird" has an answer with data (see code-archaeology's scar tissue).

## Anti-Patterns

- Optimizing without profiling ("this loop looks slow" — the profiler disagrees, always)
- Caching as the first move instead of asking why the computation is expensive at all
- Benchmarking on the dev laptop with 100 rows, shipping to 10M rows (measure at production shape)
- Five optimizations in one PR — unattributable, unreviewable, unbisectable
- Sacrificing correctness or readability for a win nobody measured (complexity is a cost you pay forever)
- Average latency as the metric (users live in the tail — p95/p99)
- "Premature optimization is evil" as an excuse to skip the *architecture-level* performance thinking that's cheap now and impossible later (data model, sync-vs-async — see software-architecture)
