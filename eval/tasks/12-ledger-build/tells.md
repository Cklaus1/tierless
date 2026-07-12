# GRADER-ONLY — Task 12 scoring

## What makes this task different from 07 and from the single-shot tasks
Task 07 proved discipline lifts PROCESS but the toy was too easy on correctness (everyone
got P6). The single-shot tasks proved a strong model one-shots isolated puzzles. Task 12 is
the bridge: a build with **real invariants (conservation, atomicity, durability)** where the
bare "write it all, run the happy path once" approach leaves LATENT correctness bugs the
author never exercises. Correctness is measured by EXECUTION against a hidden battery —
zero LLM judgment.

## Two scored dimensions

### A. CORRECTNESS (objective, the headline) — run `acceptance_test.py <build_dir>`
It imports the arm's `ledger.py` and runs 10 adversarial checks; the scorecard's `rate`
(passed/total) IS the correctness score. The checks target exactly the invariants a rushed
build gets wrong:
- **C2 conservation** — money conserved across 60 transfers (a float or an off-by-one in
  the debit/credit breaks this)
- **C3/C4 atomicity** — a rejected transfer (insufficient funds / bad account) must leave
  ALL state unchanged. The classic bare bug: debit src, THEN discover dst is bad / check
  funds too late → partial mutation. This is the money check.
- **C5 durability** — reopen the file, state persists
- **C7 invalid amount, C8 missing account, C9 open validation, C10 integer-cents** — the
  edge cases the happy-path author skips
- C1/C6 — basic transfer + history shape (most arms get these)

Hypothesis: bare arms pass C1/C5/C6 and often C2, but FAIL C3/C4 (atomicity — they check
funds after debiting, or mutate then validate) and skip C7–C10. Skilled arms (deconstruct
forces "each step independently verifiable"; build-loop forces per-phase verification and
a walking skeleton that exercises transfer-then-fail early) should catch the atomicity and
edge cases because the discipline makes them ENUMERATE and TEST the failure paths.

### B. PROCESS (P1–P6, same rubric as task 07) — grade from the arm response + build dir
Reuse task 07's P1–P6 process tells (walking skeleton, phases, verify-per-phase, resumable
trail, demonstrable end, code-works). Here P6 ("code works") should be read from the
acceptance rate, not eyeballed.

## The finding this task is built to surface
If skills lift CORRECTNESS (not just process) — i.e. skilled arms pass the atomicity/edge
checks that bare arms fail — that converts "process discipline" into "ships fewer bugs,"
the claim that actually sells. If correctness is equal (all arms pass), the task is still
too easy on correctness and needs harder invariants. Either way it's measured, not asserted.

## Grading
- Correctness rate = acceptance_test.py `rate`, per arm. Report bare vs skills.
- Process rate = mean(P1..P6) as in task 07.
- Watch specifically: the C3/C4 atomicity delta (bare vs skills) — that's the sharpest
  single signal of "discipline prevents a real bug."
