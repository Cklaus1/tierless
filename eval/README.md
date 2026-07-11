# Tierless Eval Harness

The project's core claim is: **the discipline skills make a cheaper model perform closer to a frontier model on real coding work — closing the tier gap.** This harness exists to prove or disprove that claim with data instead of faith. It is the project dogfooding its own `qa-testing` and `ai-building` skills — both of which say "no feature ships without an eval."

## The design principle: objective tells

You cannot grade LLM coding output on "quality" — it's a vibe, and every arm produces plausible-looking work. So every task here is built around one or more **tells**: a specific, checkable thing that *only the disciplined process catches*. The bug task has one actual root cause; a shotgun fix changes the wrong line. The ambiguous-ask task has a hidden interpretation fork; the disciplined arm asks about it, the bare arm guesses. Grading a tell is binary — hit or miss — which is what makes the numbers trustworthy.

## The grid: model × skills (v2)

The first version baked the model into the arm (Haiku-bare / Haiku-skills / Opus-bare), which could only answer "does Haiku+skills reach Opus?" — not the questions that drive a deployment decision. v2 makes **model and skill-state independent dimensions**:

- **Models (the ladder):** Haiku (cheap), Sonnet (mid), Opus (frontier)
- **Skill-state:** bare (task only) vs skills (relevant skill files provided, instructed to follow)
- **Tasks:** the 6 (soon 7) tell-based tasks
- **Runs:** N=3 per cell for a spread (single runs inverted results *twice* in v1 — never trust N=1)

Grid = 3 models × 2 states × 6 tasks × 3 runs = **108 arm-runs + 108 blind graders**. Each cell records `(model, skills?, task, run) → tell-hit rate`.

### The questions this grid answers (that the old arms couldn't)

1. **Per-model skill lift:** `skills − bare` for each model. Does discipline help Haiku more than Opus (the "cheap models have more to gain" hypothesis)?
2. **Does the frontier model benefit too,** or is the skill effect only at the bottom of the ladder?
3. **The money question:** what is the *cheapest model + skills* whose score matches a *pricier model bare*? If Haiku+skills ≈ Sonnet-bare or Opus-bare, that number **is** the product — quantified.
4. **Where skills backfire:** any cell where `skills < bare` (v1 found one on task 03). Tunnel-vision risk, per-model.

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
