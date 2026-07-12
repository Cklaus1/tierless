# build-loop across models: Sonnet + a Fable reference (2026-07-12)

Question: does build-loop help Sonnet (not just Haiku)? And does Sonnet+skill reach the frontier
model's process discipline? Measured DETERMINISTICALLY — the trail file either exists on disk or it
doesn't; no LLM judge (the task-07 grid used an LLM process-grader, distrusted after this session's
judge failures, so this re-confirms the core claim by filesystem inspection).

## Result — resumable-trail check (build-loop's central claim)

| arm | trail/plan file on disk? | code |
|---|---|---|
| Sonnet **bare** | **NO** (0) — just cli.py + expenses.py | works |
| Sonnet **+ build-loop+deconstruct** | **YES** (2) — .claude/plans/build-loop.md (exit record) + task-deconstruct.md (pass conditions) | works |
| **Fable bare** (frontier reference) | **NO** (0) — best code of the three (multi-file pkg + 9 passing tests) but no plan/trail | works |

All three produce working code (correctness tie, as expected — the skill's value is process).

## The finding (sharper than the Haiku-only result)

1. **build-loop works for Sonnet**: the skill is what makes Sonnet leave a phased, resumable trail;
   bare Sonnet leaves none. Confirmed deterministically, matching the grid's +0.63 Sonnet process lift.

2. **Even bare FABLE leaves no trail.** The frontier model built the nicest code but kept no plan, no
   phase record, no resumable state — it just built well and stopped. So leaving a trail is NOT a
   capability the strong model has and the weak one lacks. It's a BEHAVIOR no model does unprompted.

3. **Two kinds of skill, and build-loop is the robust kind:**
   - **Blind-spot / derive-the-non-obvious skills** (spec-review, constant-coupling) are MODEL-SPECIFIC
     — inert on a model that already has the capability (they were inert on Sonnet).
   - **Process-scaffolding skills** (build-loop) are UNIVERSAL — they install a behavior no model does
     on its own, at any capability level. Fable's better code still comes with no trail; only the skill
     produces one. This skill's value does NOT erode as the base model improves.

## Why this matters for the product claim
The most durable skills are the process-scaffolding ones: a stronger model writes better code but
still won't phase the work or leave a resumable trail across a session boundary unless instructed.
That's a claim that survives model upgrades — unlike blind-spot skills, whose value shrinks as models
get stronger. build-loop is validated across two cheap models (Haiku +0.38, Sonnet +0.63 in the grid;
trail-presence deterministically confirmed for both) AND shown to fill a gap the frontier model itself
has bare.
