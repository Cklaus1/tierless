# Fable 5 Eval Harness

The project's core claim is: **the discipline skills make a smaller model perform closer to Fable 5 on real coding work.** This harness exists to prove or disprove that claim with data instead of faith. It is the project dogfooding its own `qa-testing` and `ai-building` skills — both of which say "no feature ships without an eval."

## The design principle: objective tells

You cannot grade LLM coding output on "quality" — it's a vibe, and every arm produces plausible-looking work. So every task here is built around one or more **tells**: a specific, checkable thing that *only the disciplined process catches*. The bug task has one actual root cause; a shotgun fix changes the wrong line. The ambiguous-ask task has a hidden interpretation fork; the disciplined arm asks about it, the bare arm guesses. Grading a tell is binary — hit or miss — which is what makes the numbers trustworthy.

## The three arms

Each task is run three ways:

- **A — bare-small**: a smaller model (e.g. Haiku/Sonnet-class), no skills, just the task
- **B — skills-small**: the same smaller model, with the relevant skill files provided and instructed to follow them
- **C — reference**: the strongest model available (Fable 5 / Opus-class), no skills — the target bar

The claim is validated if **B closes a meaningful fraction of the A→C gap** on tell-hit rate. If B ≈ A, the skills are decoration. If B ≈ C, they're doing exactly what we promised.

## Structure

```
eval/
  README.md            this file
  rubric.md            how tells are scored (binary per tell + notes)
  run.md               how to run an arm and record results
  tasks/
    NN-name/
      task.md          the prompt given to the model (identical across arms)
      tells.md         the graded tells + the trap each targets (GRADER-ONLY)
      skills.md        which skills arm B is given
      context/         any code/files the task references
  results/
    template.md        one filled copy per (task × arm × run)
    SCORES.md          the roll-up table: tell-hit rate by arm
```

`tells.md` is the answer key — never shown to any arm, including B. Arm B gets the skills, not the answers.

## Grading

Per task, per arm: for each tell, mark HIT / MISS / PARTIAL with a one-line justification quoting the model's output. Sum to a tell-hit rate. Roll up in `results/SCORES.md`. A tell is HIT only if the output demonstrably contains it — "the model probably would have" is a MISS. Grade adversarially; this eval is worthless if it flatters the skills.

## Honest limitations (state them, don't hide them)

- Small N (6 tasks) — directional, not publication-grade. Widen before drawing strong conclusions.
- Single run per arm invites variance; run each arm ≥3× and report the spread once the harness proves out.
- Grader bias is the main threat: the tells make it binary, but write justifications that quote output so a second grader can check you.
- Tasks here are the *seed set*. The point is a repeatable harness, not these six specific tasks.
