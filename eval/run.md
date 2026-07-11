# Running the Eval

## The grid (v2)

Model and skill-state are independent dimensions (see README.md):

- **Models:** haiku, sonnet, opus (the ladder)
- **States:** `bare` (task only) / `skills` (task + the skill files named in `skills.md`)
- **Tasks:** the tell-based tasks under `tasks/`
- **Runs:** N≥3 per cell (single runs are untrustworthy — v1 inverted twice)

Run it with the `tierless-eval-grid` workflow: it fans out every (model × state × task × run)
cell in a pipeline (arm → blind grader) and returns per-cell tell-hit rates. `tierless-eval-matrix`
is the older 3-arm workflow, kept for reference.

## Fixture isolation — READ THIS (the v1 corruption bug)

Some tasks reference code under `tasks/NN/context/` (e.g. `cart.py`, `routes.py`). Some tasks ask
the model to *change or build* code (01 fix-the-bug, 07 build-the-app). Naively, a mutating arm
edits the shared `context/` file in place — and with N arms running that task concurrently, they
clobber the fixture other arms are still reading. In v1 this corrupted task 01 mid-run.

**The fix is a convention, not a copy: fixtures are READ-ONLY reference; the solution lives in the
response, never on disk.** The grader scores the arm's *response text* (the tells quote the model's
output), so no arm ever needs to write a file. Two enforcement layers:

1. **Fixture guard header** — every mutable fixture file starts with a comment:
   `DO NOT EDIT — eval fixture. Put your solution in your response, not in this file.`
   This stops a "helpful" agent (or a linter) from silently fixing the planted bug.
2. **Arm-prompt convention** — mutating-task prompts say: "Do not modify any files. Provide the
   corrected code / the built code in your response." The grid workflow's arm prompts already
   forbid reading outside the task dir; they also must forbid *writing*.

If a task genuinely needs on-disk mutation (rare), the arm must run against a **per-arm copy** of
`context/` (a temp dir, or `isolation: 'worktree'` in the workflow), never the shared fixture.

**Guard integrity:** before any grid run, verify the fixtures are pristine —
`git status --short eval/tasks/*/context/` must be empty. A dirty fixture means a prior run corrupted
it; restore with `git checkout eval/tasks/`.

## Fair-play rules

- Identical task text and context across all cells. Only `model` and `state` vary.
- Fresh context per arm — no bleed between cells.
- Blind grading: the grader never sees the model, the skill-state, or `tells.md`-as-answers for the
  arm (it reads tells.md as the key, but scores the response cold, unlabeled).
- Never show any arm `tells.md`.

## Grading & roll-up

Each cell → `(model, state, task, run, rate)`. Aggregate in `results/SCORES.md`:
- Per (model, state): mean tell-hit rate across tasks/runs
- **Skill lift** per model: `mean(skills) − mean(bare)`
- **The money number:** the cheapest model whose `skills` mean ≥ a pricier model's `bare` mean
- Flag any cell where `skills < bare` (backfire), per the v1 task-03 finding
