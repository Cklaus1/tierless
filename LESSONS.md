# Lessons

What building and evaluating this project actually taught us. Written to be read by
the next person (or agent) who works on it — and updated as evidence accumulates.

## About the skills (from the first eval, 2026-07-11)

1. **Skills can change a small model's process — and that's the real product.** The
   cleanest result: on the bug-hunt task, bare Haiku fixed the bug correctly but skipped
   building a reproduction; Haiku + the `debugging` skill did the repro first, exactly as
   the skill mandates, and matched the reference model. The skill didn't make the model
   smarter — it made it *follow a step it would otherwise skip*. That is the entire
   thesis, demonstrated once, legibly.

2. **A skill can tunnel attention and make things worse.** The uncomfortable result: on
   the MVP-scoping task, bare Haiku flagged HIPAA/health-data risk; Haiku + `roadmap`
   produced a cleaner MVP/v1/v2+ structure but *dropped* the compliance flag. Focusing
   the model on the skill's frame (scope phasing) crowded out a domain instinct it had
   unaided. Lesson: skills should point at *what to also remember*, not just *how to
   structure*. Candidate fix — `roadmap` and `estimation` should carry a one-line
   "domain-risk scan" step so the frame doesn't eclipse the domain.

3. **Modern small models are strong; many disciplines are now table stakes.** Four of
   six tasks showed zero gap (bare = skills = reference), including the deliberately
   hard security task. Asking clarifying questions, phasing a migration expand→contract,
   catching an IDOR — Haiku-4.5 does these unprompted. The skills' value concentrates on
   the steps models still skip under time pressure (reproduction, out-of-scope lists,
   per-step pass conditions), not the ones they've absorbed. This should *reshape the
   library*: prune or merge skills whose discipline the model already exhibits; invest
   in the ones that still move behavior.

4. **The strong model is not a ceiling on every axis.** On MVP-scoping, Opus also scored
   below bare Haiku — it inflated the MVP with sync + reminders. "Reference" is a bar per
   *tell*, not a universal upper bound. Don't treat C as ground truth; treat it as
   another graded arm.

## About evaluating (harness lessons)

5. **Objective tells are what make LLM-output grading trustworthy.** Grading "quality"
   would have been noise. Grading "did it construct a reproduction / name the mechanism /
   catch the org_id-from-body vuln" gave binary, quotable, blind-gradable verdicts.
   Every future task must be built around a specific tell, or it can't be graded.

6. **Single runs lie.** The 05 POC had skills-B (0.80) scoring *below* bare-A (1.00) on
   one run purely from variance (B mis-praised a vulnerable endpoint). The full matrix
   had 03 invert too. Neither is trustworthy at N=1. The rubric's "≥3 runs, report the
   spread" rule is not optional; it's the difference between a finding and a coin flip.

7. **Eval fixtures are load-bearing and get "helpfully" corrupted.** Task 01's buggy
   `cart.py` was auto-fixed mid-run (a linter/agent saw a bug and repaired it) — which
   deletes the very thing the task tests. **FIXED:** `eval/scripts/guard-fixtures.sh`
   prepends a neutral `# READ-ONLY eval fixture — do not modify` header to every fixture.
   Neutral wording is deliberate — the arm agents *read* these files, so the guard must
   forbid editing without revealing what's planted (a "contains a planted bug" header
   would spoil the task). Run it only when no grid is in flight.

8. **File-mutating tasks need per-arm isolation — but the deeper fix was realizing they
   don't need to mutate at all.** Tasks like "fix the bug" / "build the app" had the arm
   editing a shared `context/` path, corrupting it for concurrent arms. The insight:
   **the grader scores the arm's RESPONSE TEXT, not files on disk** (tells quote the
   model's output), so no arm ever needed to write a file — the disk-mutation was
   incidental over-helpfulness. **FIXED** at the source: the grid workflow's arm prompts
   now say "context/ files are READ-ONLY; put your entire solution in your text
   response, do not modify/create/delete any files." No per-arm copying needed for these
   tasks. (If a task ever genuinely needs on-disk mutation, use a per-arm temp copy or
   `isolation: 'worktree'` — documented in run.md.)

9. **Build the eval as a workflow, not by hand.** 36 agents (18 arms + 18 blind graders)
   ran deterministically in parallel, arms label-stripped and forbidden from reading the
   tells or skills. Reproducible with one re-invoke. Hand-running three arms for the POC
   was useful once to prove the machinery; past that, automate.

12. **Never let the model compute the score.** The v2 grid's first grade pass had graders
    return a `rate` field — and they returned garbage: raw sums (6 instead of 1.0),
    impossible values (1.75, un-producible from HIT/PARTIAL/MISS). Mixing normalized and
    un-normalized rates makes every aggregate meaningless. **FIXED:** removed `rate` from
    the grader schema entirely; the model returns only per-tell verdicts (HIT/PARTIAL/
    MISS), and the *harness* computes the rate deterministically in JS. Lesson: an LLM
    grader's job is the judgment (did this tell hit?), never the arithmetic. Structure the
    output so the math happens in code. Corollary win: because the verdicts were
    structured and preserved in the journal, the bad run was salvageable by re-grading
    from cache — no need to re-run the 108 expensive arms.

13. **Near-ceiling tasks can't prove anything.** The clean v2 grid put every arm at
    0.85–1.0 on 5 of 6 tasks — a modern small model already does clarifying questions,
    expand/migrate/contract, IDOR-catching unprompted. When everyone's near ceiling, tiny
    grading noise flips the ranking, and "cheap+skills ≥ frontier" becomes an artifact of
    task-easiness, not evidence. The bottleneck for validating the product claim is NOT
    more runs (N=3 already killed single-run inversions) — it's HARDER TASKS with headroom
    a bare small model fails. Build tasks to the difficulty where the thesis can actually
    be falsified.

14. **The "harder tasks" attempt failed — and taught us WHERE headroom isn't.** Built four
    deliberately-hard single-shot tasks (TOCTOU race, multi-bug, second-order injection,
    migration with 5 hidden traps). Headroom-checked two against bare Haiku before trusting
    them (dogfooding `verify`): **Haiku aced both** — 5-6/6 on a classic check-then-act race
    AND a second-order shell-injection/XSS review, unprompted, even finding a bonus vuln I
    hadn't planted. The lesson isn't "make them more obscure." It's that **single-shot
    knowledge tasks — spot-the-bug, review-the-code, plan-the-migration — are a ceiling
    category for a strong small model.** Obscurity just tests trivia recall (which Haiku has
    deep), not whether discipline helps. Chasing harder gotchas is a dead end.

    **Where headroom actually lives** (the pivot): discipline pays off on dimensions a
    single response can't capture —
    - **Multi-step tasks over a long horizon** where a bare model loses the thread, skips a
      step, or declares done early (this is what `build-loop`/task-07 tests — process, not
      recall).
    - **Tasks with NO single right answer** where quality is in coverage/thoroughness
      (how many real edge cases, how many genuine risks) — gradeable by count, not by a
      binary tell, and where "the bare model stopped at 3, the disciplined one found 9."
    - **Tasks where the bare model is CONFIDENTLY WRONG** (not just incomplete) — needs a
      trap where the plausible answer is affirmatively incorrect, not merely shallow.
    - **Adversarial/verification tasks** — "here's a solution, find what's wrong with it,"
      where the disciplined loop-until-dry beats one-pass.
    The next eval investment is task-07 (build-loop, process-scored) and coverage-graded
    tasks, NOT more single-shot bug hunts.

15. **The thesis is real — but only where there's a horizon (task 07 / build-loop).** After
    four single-shot tasks showed no discrimination, the build-loop paired eval (a multi-
    feature build, process-scored) gave the first clean signal: **every model, every run,
    skills > bare.** Overall process-rate lift: haiku +0.375, sonnet +0.625, opus +0.583,
    off a bare baseline of 0.33–0.42 (real headroom, no ceiling confound). The decomposition
    is the point: **both arms produce working code (P6=1.00 for all), but on PROCESS (P1–P5)
    bare=0.23 vs skills=0.87.** Not one bare run left a resumable trail (P4=0.00); the skills
    arms wrote a phased plan with exit criteria every time. Lesson: **discipline's value is
    invisible on tasks with no horizon and decisive on tasks with one.** A bare model's
    "write everything, run once at the end" is fine at 200 lines, fatal at 20,000 or across a
    session boundary. Evaluate discipline where it acts — over a process, not a single answer.
    This also validates the whole pivot in #14: process/coverage tasks, not harder puzzles.

## About the build process (meta)

10. **Dogfooding surfaced the gaps faster than review did.** Applying the project's own
    `roadmap`/`ai-building`/`qa-testing` skills to the project revealed the biggest hole
    (no eval) more sharply than any code review — the skills say "no feature without an
    eval," and the project had none. Turn the discipline on itself early.

11. **Adversarial audit beats self-review at scale.** Five independent audit agents
    against a shared rubric found real defects across all 36 skills (router
    unreachability, missing evidence gates, a skill with zero enforcement) that reading
    my own work would have rationalized past. The system's own `adversarial-review`
    principle — never review your own code — held.

## Open questions for the next iteration
- Does the +0.25 on bug-hunt survive N=3? Does 03's backfire?
- With a genuinely weaker A/B model, does a wide A→C gap appear for B to close?
- Which skills never change behavior in any task, and should be pruned or merged?
- Run Task 07: does `build-loop` improve process structure on a real multi-step build?
