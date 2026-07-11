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
   deletes the very thing the task tests. Fixtures that intentionally contain bugs,
   vulns, or bad code need a guard (a header comment "DO NOT FIX — eval fixture", and
   ideally read-only perms during a run).

8. **File-mutating tasks need per-arm isolation.** Tasks that say "fix the bug" or "build
   the app" have the arm agent editing a shared path — arm B corrupts the fixture arm C
   then reads. Read-only tasks (review, plan, scope) are safe. Fix: copy each task's
   `context/` into a per-arm temp dir, or run mutating arms in worktrees.

9. **Build the eval as a workflow, not by hand.** 36 agents (18 arms + 18 blind graders)
   ran deterministically in parallel, arms label-stripped and forbidden from reading the
   tells or skills. Reproducible with one re-invoke. Hand-running three arms for the POC
   was useful once to prove the machinery; past that, automate.

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
