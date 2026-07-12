# Skill Triage — plan

Goal: for each of the 42 skills, a MEASURED verdict — does bare Haiku already match Fable in
this skill's domain (ceiling → prune candidate), or is there a real gap the skill can close
(keep), and is that gap process (distillable) or knowledge (not)?

## Method: screening gap-probe (per skill)
For each probe-able skill: generate a rich, discriminating task in its domain → Haiku-bare and
Fable each do it → a diff agent classifies the gap: NONE / PROCESS / KNOWLEDGE, with size.
This is a SCREENING pass (N=1, auto-generated task) — its job is to SORT skills into buckets and
prioritize which deserve a full validated gap-diff cycle (like spec-review got). It is not a
final per-skill verdict; a "keep" here means "measured gap, worth a full cycle."

## Category A — verdict from existing evidence (NOT probed)
These don't fit a single self-contained task, or are already measured:
- **tierless-router** — pure routing/meta; no task. Verdict: KEEP (infrastructure — makes all
  others reachable; its value is structural, not task-measurable).
- **build-loop** — already measured: +0.63 process lift, task 07. Verdict: KEEP (validated).
- **compose, plan-mode, deconstruct, verify** — pipeline steps that only manifest over a
  horizon; validated as a family via task 07 (the skills arm that phased+verified+trailed used
  exactly these). Verdict: KEEP (validated as family) — but a full cycle isolating each is future work.
- **spec-review** — just validated via full gap-diff cycle (Haiku 8→13). Verdict: KEEP (validated).
- **naming** — a sub-check that runs inside verify; not standalone-task-shaped. Verdict: DEFER
  (probe as part of a coding task, not in this pass).
- **onboarding, icp-onboarding** — deliverable-template skills (produce a walkthrough / a
  first-run plan); probe-able but lower priority. Verdict: DEFER to a later pass.

## Category B — probed this pass (~32)
adversarial-review, ai-building, ai-safety, api-design, code-archaeology, code-migration,
compiler-building, cross-platform, data-migration, database-design, debugging,
dependency-management, estimation, human-code-review, incident-response, infra-ops,
performance-optimization, qa-testing, refactoring, release-management, requirements-elicitation,
roadmap, security-review, shell-scripting, software-architecture, systems-programming, tech-doc,
threat-modeling, ui-design, user-docs, ux-design, version-control

## Prior expectation (to be confirmed or refuted by measurement)
From earlier evals: single-shot bug/review/plan tasks tended to be CEILING (bare Haiku ≈ Fable).
If most of Category B comes back NONE/ceiling, that's the finding — it means the library's real
value concentrates in the horizon/process skills (Category A), and many domain skills are
documentation more than leverage. If several show real PROCESS gaps (like spec-review did), those
are the keepers and each earns a full cycle. Either way: measured, not asserted.
