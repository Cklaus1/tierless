# Scores Roll-Up

Tell-hit rate per task per arm. Full 6×3 matrix, single run per cell, blind grader
(Sonnet-class) scoring each output against the task's tells with no arm label.
Arms: A = Haiku bare, B = Haiku + relevant skills, C = Opus bare (reference bar).
Run date: 2026-07-11. Matrix executed via `fable5-eval-matrix` workflow (36 agents).

| Task | A (bare-small) | B (skills-small) | C (reference) | B−A | Notes |
|---|---|---|---|---|---|
| 01 bug-hunt | 0.75 | 1.00 | 1.00 | **+0.25** | B & C caught reproduction (T4); A skipped it |
| 02 ambiguous-ask | 1.00 | 1.00 | 1.00 | 0.00 | all three at ceiling — task doesn't discriminate |
| 03 mvp-scope | 0.90 | 0.80 | 0.80 | **−0.10** | A caught HIPAA (T4); B missed it. See note. |
| 04 migration-plan | 1.00 | 1.00 | 1.00 | 0.00 | all three nailed expand/migrate/contract |
| 05b security-hard | 1.00 | 1.00 | 1.00 | 0.00 | all three caught both subtle IDORs — hard task, no gap |
| 06 decompose | 0.92 | 0.92 | 0.92 | 0.00 | identical: A/C missed boundary (T5), B caught it but missed pass-conditions (T2) |
| **Average** | **0.928** | **0.953** | **0.953** | +0.025 | |

## Honest reading

**The clean win: Task 01 (bug-hunt).** Bare Haiku found the bug and fixed it correctly
but skipped constructing a reproduction first (T4 MISS). Haiku+debugging did the repro
(T4 HIT) — "reproduce before fixing" is exactly what the skill mandates, and it's the
behavior that changed. B reached C's score; gap fully closed. This is the single
cleanest piece of evidence that a skill moved the small model's process.

**The uncomfortable result: Task 03 (mvp-scope), B scored BELOW A.** Bare Haiku flagged
HIPAA/PHI as the domain risk (T4 HIT); Haiku+roadmap+estimation produced a cleaner
MVP/v1/v2+ structure but never mentioned health-data compliance (T4 MISS). The roadmap
skill focused attention on scope-phasing and, on this run, crowded out the domain-risk
instinct the bare model had. Notably C (Opus) ALSO scored 0.80 here — it inflated the
MVP with calendar sync + reminders (T1 MISS) while catching HIPAA. So on task 03 the
reference bar itself was below bare Haiku. Real finding, not noise to hide: **a skill
can narrow attention onto its own frame and cost coverage elsewhere.**

**The dominant result: no discrimination on 4 of 6 tasks.** 02, 04, 05b, 06 all landed
A = B = C. Two readings, both partly true:
1. The tasks are at/near ceiling for a modern small model — Haiku is genuinely strong,
   and even the "hard" security task didn't separate the arms.
2. The skills encode process a strong small model now does anyway (ask clarifying
   questions, phase a migration) — so the marginal instruction adds nothing on top.

## What this run does and does NOT show

- **Does NOT prove the headline claim** ("skills make a small model match Fable 5")
  in general. Average lift was +0.025 — inside single-run noise. One run per cell.
- **DOES show a real, legible mechanism on 01**: the skill changed the process (repro-
  first) and that closed the gap. That's the existence proof the skills CAN work.
- **DOES surface a real risk (03)**: skills can tunnel attention and cost coverage.
- **DOES validate the harness**: blind grading, objective tells, clean execution,
  36/36 agents, and it caught its own designer's task at ceiling (02) and a skill
  backfiring (03) — an eval that only flattered the skills would be worthless.

## Caveats (from rubric.md, reaffirmed)
- **Single run per cell.** 03's inversion and 01's win both need ≥3 runs to trust the
  spread. This is directional, not conclusive.
- **Grader is one Sonnet-class agent.** Spot-check against a human grader before citing.
- **Small model is strong.** Haiku-4.5 may be too capable for these tasks to
  discriminate; a smaller/older model would likely show a wider A→C gap and more room
  for B to close. Worth re-running with a weaker A/B model.
- **Task 01 fixture caveat:** during the run the fixture file was auto-edited (a linter/
  agent "fixed" the planted bug); restored, but arm agents that mutate shared fixtures
  in place is a harness bug — see LESSONS.md. Read-only tasks (02–06) unaffected.

## Next to raise the signal
1. Re-run at N=3 per cell; report mean ± spread. Cheap (workflow already written).
2. Add a genuinely weaker A/B model to widen the A→C gap the skills can close.
3. Harder-ceiling tasks on 02/04/05b (they don't discriminate at current difficulty).
4. Isolate file-mutating tasks (01, 07) per-arm so they can't corrupt shared fixtures.
