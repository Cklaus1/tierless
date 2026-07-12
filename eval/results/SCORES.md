# Scores Roll-Up

## v3 — task 07 build-loop, process-scored (2026-07-11) ⭐ THE HEADLINE RESULT

The single-shot grid (v2 below) couldn't discriminate — a strong small model one-shots
bug hunts and reviews. Task 07 is different: a multi-feature BUILD, scored on PROCESS
(P1–P6), where discipline shapes something a single response can't fake. 3 models × 2
states (bare / build-loop+deconstruct skills) × 2 runs = 12 isolated builds, blind
process-graded. Deterministic rate from verdicts.

### Overall process-rate (mean of P1–P6) per (model, state)

| model | bare | skills | lift |
|---|---|---|---|
| haiku | 0.333 | 0.708 | **+0.375** |
| sonnet | 0.333 | 0.958 | **+0.625** |
| opus | 0.417 | 1.000 | **+0.583** |

**Every model, every run, skills > bare. This is the first clean, unambiguous signal that
the discipline works.** Unlike v2, there is no near-ceiling confound: bare models sit at
0.33–0.42, so there is real headroom and the skill fills it.

### Per process-tell — fraction HIT, bare vs skills (pooled across models & runs)

| tell | bare | skills | delta |
|---|---|---|---|
| P1 walking skeleton first | 0.00 | 0.75 | **+0.75** |
| P2 explicit phases | 0.17 | 0.92 | **+0.75** |
| P3 verify per phase | 0.00 | 0.83 | **+0.83** |
| P4 resumable trail | 0.00 | 0.83 | **+0.83** |
| P5 demonstrable end state | 1.00 | 1.00 | +0.00 |
| P6 code actually works | 1.00 | 1.00 | +0.00 |

### The key decomposition: process vs. outcome

| dimension | bare | skills | lift |
|---|---|---|---|
| **process** (P1–P5) | 0.23 | 0.87 | **+0.63** |
| **outcome** (P6 code works) | 1.00 | 1.00 | +0.00 |

**This is the sharpest finding of the whole eval.** Both bare and skills arms produce
*working code* (P6 = 1.00 for everyone — the expense tracker is easy enough that any modern
model gets it right). But on *process* — walking skeleton first, phasing, verifying each
step, leaving a resumable trail — bare models score 0.23 and the skills arms score 0.87.

The bare model's universal pattern (quoting graders): *"I built three files in this order…"*
then one verification block at the end. No phases, no incremental verification, **no trail
that survives a session boundary** (P4 = 0.00 bare — not a single bare run left a plan/state
file). The skills arms wrote `.claude/plans/build-loop.md` with phase goals, exit criteria,
and a completed exit record.

### Why this matters more than the code-works tie

On a toy expense tracker, "process" looks like overhead — the code works either way. But
process is the ONLY thing that scales to real projects: a bare model that writes everything
then runs it once is fine at 200 lines and catastrophic at 20,000, or across a session
boundary where the untracked work is simply lost. **The build-loop skill changes the failure
mode from "works now, unrecoverable later" to "phased, verified, resumable" — exactly its
claim.** The single-shot tasks couldn't see this because they have no horizon; task 07 does.

### Caveats (honest)
- N=2 per cell; one haiku-skills run scored 0.42 (the skill's trail didn't fully take that
  run — real variance, shown not hidden). Sonnet/opus skills were rock-solid (0.92–1.00).
- The task is easy on P6 by design (isolates process from correctness). A harder build would
  test whether the process lift also protects *correctness* at scale — the natural next task.
- Process tells are somewhat correlated (a phased build tends to hit P1–P4 together), so
  +0.63 is one effect seen four ways, not four independent wins. Still a large, real effect.

---

## v2 — the model × skills grid (2026-07-11)

3 models (haiku/sonnet/opus) × 2 states (bare/skills) × 6 tasks × 3 runs = 108 cells,
each blind-graded against the task's tells. Run via `tierless-eval-grid`.

**Grading integrity note:** the first grade pass had a bug — graders returned un-normalized
`rate` values (raw sums like 6, and impossible values like 1.75). Detected before drawing any
conclusion. Fixed by removing `rate` from the grader schema and computing it deterministically
in JS from the HIT/PARTIAL/MISS verdicts (`HIT=1, PARTIAL=0.5, MISS=0, ÷ tell count`), then
re-grading (arms replayed from cache). All 108 rates below are in [0,1] and verified against
their verdicts. See LESSONS #12.

**Task 01 caveat:** the bug-hunt fixture (`cart.py`) was corrupted mid-run by an arm that "fixed"
the planted bug in place (the very bug the isolation fix now prevents). Task-01 numbers are
contaminated this run and EXCLUDED from all aggregates below. The isolation fix lands for the next run.

### Per (model, state, task) — mean tell-hit rate over 3 runs

| task | haiku bare | haiku skills | sonnet bare | sonnet skills | opus bare | opus skills |
|---|---|---|---|---|---|---|
| 01-bug-hunt ⚠️ | 0.46 | 0.58 | 0.33 | 0.58 | 0.75 | 0.75 |
| 02-ambiguous-ask | 0.97 | 1.00 | 1.00 | 0.90 | 1.00 | 1.00 |
| 03-mvp-scope | 1.00 | 1.00 | 0.90 | 1.00 | 0.90 | 0.97 |
| 04-migration-plan | 0.97 | 0.97 | 0.89 | 1.00 | 1.00 | 1.00 |
| 05b-security-hard | 0.97 | 0.83 | 0.77 | 1.00 | 0.93 | 1.00 |
| 06-decompose | 0.86 | 1.00 | 0.81 | 0.64 | 0.83 | 1.00 |

⚠️ task 01 contaminated — excluded from aggregates.

### Per-model skill lift (mean across 5 clean tasks)

| model | bare | skills | lift |
|---|---|---|---|
| haiku | 0.953 | 0.961 | **+0.008** |
| sonnet | 0.872 | 0.908 | **+0.036** |
| opus | 0.933 | 0.993 | **+0.060** |

### The "money" comparison

- haiku+skills = 0.961 · sonnet-bare = 0.872 · opus-bare = 0.933
- sonnet+skills = 0.908 · opus-bare = 0.933

**haiku+skills (0.961) exceeds BOTH sonnet-bare (0.872) AND opus-bare (0.933)** on these 5 tasks.
Read carefully before celebrating — see interpretation.

### Backfire cells (skills < bare)

| model | task | bare | skills | delta |
|---|---|---|---|---|
| haiku | 05b-security-hard | 0.97 | 0.83 | −0.13 |
| sonnet | 02-ambiguous-ask | 1.00 | 0.90 | −0.10 |
| sonnet | 06-decompose | 0.81 | 0.64 | −0.17 |

## Honest interpretation

**1. The directional finding matches the thesis — skill lift grows down… no, UP the ladder.**
Lift was +0.008 (haiku), +0.036 (sonnet), +0.060 (opus). That's the *opposite* of the naive
"cheap models have more to gain" hypothesis — here the strongest model gained most. But read it
with the ceiling in mind: haiku-bare was already 0.953 on these tasks (little room to improve),
so its small lift is a ceiling effect, not evidence skills don't help it. The tasks are too easy
to separate the arms cleanly — see #3.

**2. haiku+skills ≥ opus-bare is real in these numbers but OVERSTATED by task difficulty.**
Every arm scores 0.85–1.0 on tasks 02–06 because a modern small model already does clarifying
questions, expand/migrate/contract, IDOR-catching, etc. When everyone is near ceiling, tiny grading
differences flip the ranking. This is suggestive, not conclusive: the product claim ("cheap+skills
matches frontier") is *consistent with* the data but not *established* by it — the tasks lack the
headroom to prove it.

**3. Task discrimination is the real bottleneck (bare-mean across all models):**
02=0.99, 04=0.95, 03=0.93, 05b=0.89, 06=0.83, 01=0.51(contaminated). Only 06-decompose and
(a cleaned) 01-bug-hunt have enough headroom to separate arms. **The tasks are too easy.** The next
investment isn't more runs — it's *harder tasks* that a bare small model fails, so skills have room
to show a real gap. This is the single most important finding.

**4. Skills backfired in 3 of 15 (model,task) cells — a real, repeating risk.**
Consistent with v1's task-03 backfire. sonnet+deconstruct on task 06 dropped 0.17; haiku+security on
05b dropped 0.13. The mechanism (from v1 analysis): a skill narrows attention onto its own frame and
can crowd out coverage the bare model had. Worth a "domain-risk scan" line in the affected skills.

## What this run establishes vs. doesn't

- **Establishes:** the grid harness works end-to-end (216 agents, blind, deterministic grading);
  skills produce a small positive lift on average (+0.008 to +0.060); backfires are real and
  repeat; the tasks are near-ceiling and under-discriminating.
- **Does NOT establish:** the headline product claim at significance. The near-ceiling scores mean
  the numbers can't distinguish "skills close the gap" from "these tasks are too easy to tell."
  N=3 helped (no single-run inversions survived aggregation) but can't fix easy tasks.

## Next (in priority order)
1. **Harder tasks** — the top lever. Add tasks a bare haiku scores <0.5 on, so there's a gap to close.
   Candidates: multi-bug hunts, subtle concurrency bugs, migrations with hidden ordering traps,
   security reviews with 2nd-order vulns buried in more code.
2. Re-run task 01 with the isolation fix (fixture no longer corruptible) for a clean bug-hunt number.
3. Run the build-loop paired eval (task 07) — process-scored, still pending.
4. Human-grader spot-check on ~10 cells to validate the Sonnet grader's verdicts.
