---
name: code-migration
description: Code-migration skill — framework/language/platform ports at scale: strangler over rewrite, mechanical loop over artisanal effort, old and new proven equivalent
metadata:
  type: user
---

# Code Migration — Port & Rewrite Skill

## Why

"Migrate to the new framework" is where codebases go to die twice: the big-bang rewrite stalls at 80% for a year while the old system keeps changing underneath it, and the team maintains both forever. Smaller models make it worse by treating migration as *translation* — porting file by file on vibes, losing the undocumented behaviors that were the actual product. This skill is the discipline for moving a living codebase: incremental strangulation over big-bang, a mechanical loop over artisanal effort, and equivalence proven rather than assumed. (Data moves are **data-migration**; this skill is for code — frameworks, languages, major-version ports, platform moves.)

## The Rule

**The system stays shippable throughout — old and new run side by side, slices move one at a time behind a seam, and each slice is proven equivalent before the old path dies.** A migration you can't pause indefinitely at any point is a bet the roadmap can't cover.

## How to Apply

### 1. Scope it like a project (because it is one)

- **Inventory first**: enumerate what must move — modules, endpoints, call sites (`grep` the actual usages; the count is the scope). Route through roadmap/estimation: migrations are the reference class with the worst overrun history, and the long tail (the last 10% of weird call sites) is where the estimate dies.
- **Freeze the why**: one paragraph on what the migration buys (EOL runtime? unhirable stack? blocking feature?). "The new thing is nicer" funds nothing; scope creep gets measured against this paragraph.
- **Pin behavior before moving it**: the test suite is the safety net — where coverage is thin over code being ported, write characterization tests *first* (same law as refactoring). For user-facing paths, capture golden request/response pairs.

### 2. Build the seam, then strangle

- Establish the boundary where old and new coexist: routing layer, adapter interface, module facade. Traffic/callers flow through the seam and can be pointed at either implementation per-slice, per-flag.
- Migrate in **vertical slices** (one endpoint, one feature, one module — end to end), not horizontal layers ("all the models first"). A vertical slice ships and proves the pipeline; a horizontal layer proves nothing until everything moves.
- First slice is the **walking skeleton** (see build-loop): the smallest real slice through the full new stack, deployed to production. It flushes out the integration unknowns while the stakes are one endpoint, not forty.

### 3. Make the loop mechanical

Migrations are hundreds of similar changes — the discipline is industrialization:
- Write the **recipe** after the first 2–3 slices, in `.claude/plans/{migration}-recipe.md`: the step-by-step transformation, the gotchas, the checklist. The recipe is what makes slice 40 take an hour instead of a day (and is what you'd hand a fleet of agents).
- **Automate the mechanical part** where the pattern is regular: codemods, structured find-replace, scripted rewrites — with each automated batch still passing the same per-slice verification
- Track progress visibly: a checklist of slices (in the build-loop artifact) with owner and status — "how far along is the migration" must have a numeric answer

### 4. Prove equivalence per slice

- Old tests pass against the new implementation (via the seam), plus golden pairs match
- Where feasible, **shadow-run**: send real traffic to both, compare outputs, log divergences — divergence is either a migration bug or an undocumented behavior you almost lost; investigate before flipping
- Flip the flag per slice; watch the metrics (infra-ops signals); keep the old path warm until the slice has served real traffic

### 5. Kill the old path — actually

A migration is done when the old code is *deleted*, the seam is removed, and the flags are gone — not when the new code works. The two-systems tax (double maintenance, double on-call surface, "which one does X live in?") is the real cost of stalling, and it compounds monthly. Schedule the deletions as slices too; celebrate deletions, not just launches.

## Anti-Patterns

- The big-bang rewrite on a branch, integrated "when it's done" (it's never done; the trunk moved)
- Migrating by horizontal layer — six months of work, zero shippable slices, unknown integration risk
- Improving the design while porting ("while I'm here") — port faithfully first, improve in a separate pass; mixing them makes divergence undiagnosable
- No characterization tests because "the new version will be better anyway" (the undocumented behavior *was* the product)
- Declaring victory at 90% and living with both stacks forever (the last 10% is the assignment)
- The migration nobody can pause: half-moved, seam leaking, neither side fully works — strangler discipline exists exactly to prevent this state
