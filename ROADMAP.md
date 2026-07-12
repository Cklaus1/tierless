# Tierless Roadmap

Written with the project's own `roadmap` skill: MVP → v1 → v2+, each phase evidence-driven,
with explicit out-of-scope. Grounded in what the eval actually measured (`eval/`, `LESSONS.md`),
not the original pitch.

## The strategic reframe (why this roadmap looks different from "more skills")

The eval changed what the product is. It did NOT validate "43 skills make a cheap model senior" —
most skills measured ~0 gap against a strong cheap model. It DID validate two things:

1. **Scaffolding skills** (`build-loop`, the compose→verify pipeline) — install a behavior *no model
   does unprompted, at any capability level*. Value does not erode as base models improve. Durable.
2. **The gap-diff method** — a deterministic way to find *which* skills help a *specific* model.

The reframed value proposition: **"Tierless measures your model and installs the disciplines that
actually close its gaps."** The model-specificity finding — a weakness on its face — becomes the
differentiator: every competitor ships a fixed bundle and claims universal lift; we can prove which
skills help *your* model, and admit which don't.

**Critical economics (measured — `eval/gap-diff/who-finds-gap/`):** minting a skill and using a skill
have opposite cost profiles.
- **Minting is expensive and needs a frontier model.** Handed a cheap model the exact (weak, strong)
  attempt pair a frontier model had analyzed, and it could NOT recover the load-bearing discipline —
  seeing the gap is itself a derive-the-non-obvious act, the class cheap models are weakest at. So
  "hand a cheap model a pile of examples and it distills its own skills" **does not work**;
  frontier-in-the-loop is required for distillation.
- **Using is cheap.** Once the frontier model has distilled a skill, a cheap model applies it fine
  (Haiku + `constant-coupling` went 9/12 → 12/12).

This fixes the product shape: **distill centrally with a frontier model; ship cheap, validated skills
to users.** The distillation — not the skills themselves — is the moat, and it genuinely requires
capability the user's cheap model doesn't have. It also means Tierless is a *service/product with a
frontier model in its supply chain*, not a self-contained bundle a user could regenerate locally.

---

## MVP — validate the core and answer the one make-or-break question

**Goal:** know whether the product thesis holds for the ACTUAL ICP model, and ship the honest core.

In scope:
- **The small-local-model experiment (highest priority by far).** Run the two validated gap-diff
  cycles (spec-review, constant-coupling) + build-loop against a genuinely small model
  (Qwen-7B / Llama-8B class) — the model an adopter reaches for to cut cost. This is the biggest
  untested question in the whole eval (LESSONS #21). Outcome determines everything downstream:
  - Big gaps → the thesis is validated for the real ICP; skills matter; invest hard.
  - Small gaps → the value is narrower than hoped; pivot to the method-as-product framing only.
- **Split the library by evidence.** `skills/core/` = the validated few (build-loop, spec-review,
  constant-coupling, + the compose→verify pipeline). `skills/candidates/` = the rest, clearly marked
  "unvalidated — measured ~0 gap on strong cheap models; may help weaker ones." Stop implying all 43
  are proven.
- **A real getting-started path.** The ICP's first win in <10 minutes: install, run one scaffolding
  skill on a real task, see the resumable trail it produces. (We have `onboarding`/`icp-onboarding`
  skills — apply them to ourselves.)

Explicitly OUT of scope for MVP:
- Chasing skill count. No new standard-checklist skills (measured inert).
- Any "makes your model smarter" claim. The claim is process/scaffolding, stated honestly.

MVP ships when: the small-model number exists (validated or not), the library is split core/candidate,
and a new user can reach the first-win in one sitting.

---

## v1 — the differentiating feature: per-model gap measurement (match local, mint hosted)

**Goal:** turn the gap-diff method into a tool the user runs against their own model.

Adds:
- **`tierless measure`** — point it at (your cheap model, a task in your domain); it runs the gap-diff
  cycle (your model bare vs a reference, deterministic scoring) and reports which skills close gaps for
  YOUR model. This is the feature no competitor can match, and it makes the model-specificity finding a
  selling point instead of a caveat.
  - **Design constraint from the who-finds-the-gap result:** the *distillation* step (turning a
    measured gap into a new discipline) MUST use a frontier model — a cheap model can't derive the
    non-obvious discipline even with the strong example in front of it. So `tierless measure` has two
    modes: (a) **match mode** — score the user's model against the *existing* validated skills and
    report which lift (cheap, fully local-ish, the common case); (b) **mint mode** — when a gap exists
    that no current skill covers, run frontier-powered distillation *as a hosted service* (the frontier
    call is ours, not the user's). Do NOT promise a self-contained loop where the user's cheap model
    distills its own skills — that was tested and does not work.
- **Prune, with receipts.** Any candidate skill that measures ceiling across the tested models gets
  archived (kept in git history, out of the shipped set) with its eval linked. "N skills, each closing
  a measured gap" beats "43 skills."
- **More scaffolding skills** — the durable class. Derive them via gap-diff from horizon/process gaps
  (not single-shot puzzles). Candidates: a "session-handoff" skill (resumable state across context
  boundaries — the build-loop insight generalized), a "long-migration driver."

Does NOT include: per-model hosted registry, agent integrations (that's v2).

---

## v2+ — scale (each item independently shippable)

- **Per-model skill profiles.** A published registry: "for gpt-4o-mini, these 4 skills lift; for
  qwen-7b, these 9." Built from `tierless measure` runs. The data compounds; it becomes the reason to
  use Tierless over a static bundle.
- **Native agent integration.** One-command install into Claude Code / Cursor / Codex that wires only
  the skills validated for the model that agent is running.
- **Community task/checklist contributions.** The deterministic-checklist format is reusable; let users
  contribute domain tasks + oracles, expanding coverage without us hand-authoring.
- **CI-style regression:** re-run the validated cycles when a new model version ships, to catch when a
  skill goes inert (or a new gap opens) as models change.

---

## The one bet that gates everything

**Run the small-model experiment first.** Every downstream decision — how hard to invest, whether the
core is 3 skills or 15, whether the pitch is "skills" or "the method" — depends on whether real cheap
models (not the near-ceiling Haiku/Sonnet we've tested) show large gaps. It's one experiment, cheap to
run if a small model is reachable, and it either validates the thesis for the actual buyer or tells us
to narrow the claim. Do not build v1 features until this number exists.

## The moat, stated plainly
Not the skills (copyable) and not the count (a liability). Three things, in order of durability:
1. **The distillation capability.** Minting a validated skill requires frontier-model analysis to *see*
   the non-obvious gap — a user's cheap model provably cannot do it (`who-finds-gap/`). So the library
   of validated skills is not something a competitor's cheap-model pipeline can regenerate; it takes
   frontier intelligence applied with method. This is the hardest part to copy.
2. **Measured honesty + a deterministic method.** We can tell a buyer exactly which disciplines help
   their specific model and prove it, in a field where everyone else asserts universal lift.
3. **The scaffolding skills.** Universal, model-agnostic, value that doesn't erode as models improve.

Protect all three — and note they compound: every claim in this repo bottoms out in a deterministic
check (not an LLM judge), and that discipline is both the method and the brand.

## What the reflexive probes settled (don't re-litigate)
Two self-referential experiments both pointed the same way and are DONE:
- **Can we build an `eval-design` skill?** No — eval-design is at ceiling (a modern model designs a
  rigorous eval bare). No meta-skills to add. (`eval/gap-diff/eval-design/`)
- **Can a cheap model find its own gaps?** No — frontier-in-the-loop is required to distill; cheap
  models apply. (`eval/gap-diff/who-finds-gap/`)
Net: stop looking for more skill *value* in cheap self-improvement or meta-skills. The value is
(a) scaffolding skills and (b) the frontier-powered method. Invest there.
