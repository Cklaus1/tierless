# GRADER-ONLY — Task 12b scoring

## The design
Same objective battery as task 12 (acceptance_test.py, execution-scored, 10 checks). The
ONLY change from 12 is the task prompt: 12b does NOT state atomicity / conservation /
integer-cents. It only says "handle errors sensibly" and "robust enough to trust with real
money." The arm must DISCOVER the invariants.

## Why this should discriminate where 12 didn't
Task 12 handed the model the word "atomicity" → bare Haiku wrote pre-checks → 10/10, no
headroom. Here the model gets no such hint. The hypothesis:
- **Bare arm**: implements the happy path ("subtract from src, add to dst, save"), handles the
  errors it happens to think of, and ships. If it checks funds AFTER debiting, or validates
  after mutating, the battery's C3/C4 atomicity checks FAIL. It may also miss C7 (amount<=0)
  or C9 (dup/negative open) if it didn't enumerate those.
- **Skills arm** (deconstruct + verify): deconstruct's "each step independently verifiable +
  enumerate failure modes" and verify's "adversarial self-review: what input breaks this?"
  should surface the failure paths → pre-checks before mutation, edge cases handled → higher
  battery rate.

## Scoring
- Correctness rate = acceptance_test.py `rate` per arm (bare vs skills). THE headline.
- The sharpest signal: C3/C4 (atomicity) and C7/C9 (edge validation) pass-rate delta.
- Also grade process P1-P6 from the response if useful, but correctness is the point here.

## Headroom check REQUIRED before running the grid
Run one bare Haiku arm, score with the battery. If bare < ~0.9 (i.e. it drops atomicity or
edge checks), there's headroom → run the grid. If bare = 1.0 again, even underspecified, then
correctness of a single-file ledger is fully ceiling for this model and the lever is task
COMPLEXITY (option 2 in task 12's tells), not specification. Either result is a real finding.

## HEADROOM CHECK RESULT (2026-07-11) — still ceiling, even underspecified. Grid NOT run.
Ran 3 arms (2 bare, 1 skills), scored by battery:
- bare run 1: 0.9  (missed only C9 — allowed a negative opening balance; a minor edge, NOT
  the atomicity bug this task was built to surface)
- bare run 2: 1.0
- skills run: 1.0
Atomicity (C3/C4) passed on ALL arms. Removing the "atomicity/conservation" hints did NOT
make a bare model ship the debit-before-check bug — a capable model writes check-before-mutate
by default, hint or no hint. The 0.9 vs 1.0 spread is one minor edge case, i.e. noise, not a
discipline signal.

**Conclusion (robust across tasks 07-P6, 08-11, 12, 12b): correctness of a well-scoped,
single-artifact build is a CEILING category for a modern small model.** Discipline's
measurable value is in PROCESS over a horizon (task 07: +0.63), not in correctness at this
scale. To find correctness headroom would require genuinely LARGE multi-file builds where a
bare "write-it-all" model produces real cross-module inconsistencies — a much bigger eval
investment (option 2). Recorded as a boundary finding, not pursued further now. See LESSONS #16.
