# Running the Eval

## Arms

| Arm | Model | Skills provided |
|---|---|---|
| A — bare-small | smaller model (Haiku / Sonnet-class) | none |
| B — skills-small | SAME smaller model as A | the skill files named in the task's `skills.md` |
| C — reference | strongest available (Fable 5 / Opus-class) | none |

Keep A and B on the identical model — the whole experiment is "what do the skills add,"
so the model must be the only-held variable between them. C uses the strong model to
set the bar the skills are trying to reach.

## Procedure per task

1. **Arm A**: new session/context. Paste `task.md` (and any `context/` files). Nothing
   else. Save the full response to `results/{task}-A.md`.
2. **Arm B**: new session/context. Paste the full text of each skill file named in
   `skills.md`, then: "Follow the discipline in these skills for the following task."
   Then `task.md` + context. Save to `results/{task}-B.md`.
3. **Arm C**: new session/context. Same as A (task only, no skills), strong model.
   Save to `results/{task}-C.md`.

Never show any arm the `tells.md` — it's the answer key.

## Fair-play rules

- Identical task text and context across all three arms. Only the model (A/B vs C) and
  the skills (B vs A/C) vary.
- Fresh context per arm — no bleed from a previous arm's answer.
- For ≥3 runs per arm (recommended once the harness proves out), vary nothing but the
  run; report mean and spread.

## Grading

Open `results/{task}-{arm}.md` and `tells.md` side by side. Fill a copy of
`results/template.md` per (task, arm). Score each tell per `rubric.md`. Roll the
task-hit-rates into `results/SCORES.md`.

## Automating later

This is written for a human (or an agent) driving it by hand — deliberately, so the
first pass is scrutable. Once the tells prove stable, the three arms and the grader
can each be an `agent()` call in a Workflow: fan out A/B/C per task in parallel, then a
grader agent scores each output against tells.md with a structured verdict. Keep the
human in the loop for grader spot-checks until the automated grader agrees with a human
grader on a full task.
