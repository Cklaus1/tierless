# GRADER-ONLY — Task 07 build-loop process rubric

## Why this task is different
build-loop's claim is about STRUCTURE across a multi-step build, not any single
artifact. A one-shot tell can't capture it. So this is a PAIRED eval:
- **Arm A (no loop skill)**: same small model, just the task.
- **Arm B (loop skill)**: same small model + build-loop.md (+ deconstruct.md).
- **Arm C (reference)**: strong model, no skills — the structure bar.
We score the PROCESS the work reveals, plus whether the code actually works. The
question is not "did code appear" (all arms produce code) but "was it built as a
phased, verifiable, recoverable sequence or as one undifferentiated dump."

## Process tells (score each HIT / PARTIAL / MISS)
- **P1 — walking skeleton first**: does the build start with a thin end-to-end slice
  that RUNS (e.g. add+list persisting to file, exercised) before piling on summary/
  filters? Or does it write all modules then run nothing until the end? Skeleton-first
  = HIT.
- **P2 — explicit phases with boundaries**: is the work broken into named, ordered
  phases (each a shippable increment), rather than a flat "here's everything"? A stated
  phase plan = HIT; incidental ordering = PARTIAL.
- **P3 — verification per phase**: does each phase get exercised/checked before moving
  on (ran the CLI, showed output, a test), rather than one big "should work" at the
  end? Evidence of run-as-you-go = HIT.
- **P4 — a trail / state you could resume from**: is there a record of what's done and
  what's next (a plan file, a checklist, phase-exit notes) — the thing that survives a
  session boundary? build-loop's whole point. Present = HIT.
- **P5 — demonstrable end state**: does it end by actually running the finished tool and
  showing real output (add a few expenses, list, summarize), not just asserting done?
- **P6 — the code actually works**: read the code — does it satisfy all five
  requirements and hang together (persistence really persists, summary math right,
  filters applied)? Functional correctness, independent of process. HIT/PARTIAL/MISS.

## Scoring
rate = mean(P1..P6). Report per arm. The build-loop hypothesis is supported if
**B's process tells (P1–P5) are meaningfully higher than A's** — even if P6 (does the
code work) is similar. That would be the finding: the loop skill improves STRUCTURE and
recoverability, which is exactly what it claims and what a single-output eval misses.
If B ≈ A on P1–P5, the loop skill isn't changing behavior for a task this size (also a
valid finding — maybe the loop only pays off on larger builds; note it).

## Grader hygiene
Grade the transcript/process narration, not just the final code block. Quote evidence.
Grade blind to arm where possible. A single run per arm is directional only — the
process signal (P1–P4) tends to be more stable than tell-coverage, but still run ≥2×
before concluding.
