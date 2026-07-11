# Grading Rubric

## Unit of grading: the tell

Each task's `tells.md` lists 4–6 **tells** — specific, checkable things that separate
disciplined work from plausible-looking work. You grade tells, not overall "quality."

For each tell, assign:
- **HIT (1.0)** — the output demonstrably contains it. You can quote the line.
- **PARTIAL (0.5)** — gestures at it but incompletely (e.g. "rounding seems off"
  without naming the mechanism). Use sparingly; when unsure between PARTIAL and MISS,
  choose MISS.
- **MISS (0.0)** — absent, or the output does the trapped wrong thing.

A tell is HIT only on evidence in the output. "A reasonable model would have meant
this" is a MISS. Grade as an adversary trying to disprove the skills' value.

## Task score

`task tell-hit rate = sum(tell scores) / number of tells`, in [0, 1].

Some tells.md mark a tell "bonus-weight" — count it, but note it separately so a
skill that only wins on bonus tells doesn't look stronger than it is.

## Arm score

Average tell-hit rate across all 6 tasks, per arm. Report per-task and the average.

## The claim test

Report three numbers per task and overall:
- **A** (bare-small), **B** (skills-small), **C** (reference)

Then the **gap-closure ratio**: `(B − A) / (C − A)`, when `C > A`.
- ~0 → skills didn't help (B no better than bare)
- ~1 → skills brought the small model to the reference bar
- >1 → skills pushed past the reference on these tells (possible: skills encode
  specific checks even a strong bare model skips)
- If `C ≈ A` on a task, the task doesn't discriminate — flag it for replacement, don't
  report a ratio.

## Grader hygiene

- Grade blind to arm where possible: strip arm labels from outputs before scoring.
- Quote the supporting line in every HIT/PARTIAL justification so a second grader can
  audit you.
- If an arm hits a tell for the *wrong reason* (lucky guess, not the disciplined
  path), it still counts as HIT — the tell is about the output, not the intent. But
  note it; a pattern of lucky hits means the tell is too easy.
- One grader, all arms of a task, in one sitting, for consistency.
