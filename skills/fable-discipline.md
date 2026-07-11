---
name: fable-discipline
description: Fable-discipline router — classifies task weight and prescribes which skills to layer; the entry point to the whole system
metadata:
  type: user
---

# Fable Discipline — The Router Skill

## Why

The other skills only help if they're invoked at the right time. A smaller model doesn't know when to plan versus when to just edit — it either skips discipline entirely or applies all of it to a typo fix. This skill is the decision tree: classify the task first, then load exactly the discipline the task weight demands. This is the entry point; every session should start here.

## The Rule

**Before touching any code, classify the task into a tier. The tier determines which skills are mandatory.**

Before classifying: if the ask is ambiguous — multiple readings, no clear done-condition — run requirements-elicitation first. You can't classify a task you've misunderstood.

### Tier 0 — Trivial
One file, no logic change, no new behavior: typos, config values, comment fixes, renames within a file.
- **Skills required:** none
- **Still required:** read the file before editing it; state what you changed

### Tier 1 — Medium
1–2 files, follows an existing pattern in the codebase, no new architecture: add a field, extend a handler that mirrors a neighboring one, add a test case.
- **Skills required:** deconstruct → verify
- **Skip compose/plan-mode** — the pattern already encodes the design

### Tier 2 — Hard
3+ files, OR any new pattern/interface/dependency, OR code you don't fully understand (see code-archaeology), OR anything touching auth, payments, data migration, or concurrency.
- **Skills required:** compose → plan-mode → deconstruct → verify → adversarial-review
- **No exceptions for "I understand this codebase already"** — the artifacts are the point

### Tier 3 — Project
A new project, major feature, or anything the user describes in outcome terms ("build X") rather than change terms ("edit Y").
- **Skills required:** roadmap → build-loop; each task inside a phase gets its own tier classification

## Conditional Lanes

Tiers set the floor; the *shape* of the task adds skills on top. Whichever tier applies, add:

| The task involves | Add |
|---|---|
| Code you didn't write and don't understand | code-archaeology (before compose) |
| A bug to diagnose | debugging (the fix is then its own tiered task) |
| Production actively broken | incident-response FIRST, debugging after |
| Restructuring without behavior change | refactoring |
| Framework/language/platform port | code-migration |
| Schema or data change | data-migration (always Tier 2; two clean passes) |
| New endpoint, interface, or library surface | api-design (before implementation) |
| Adding or upgrading a dependency | dependency-management |
| "Make it faster" | performance-optimization |
| New or changed behavior (Tier 2+) | qa-testing (test plan before deconstruct completes) |
| Auth, input handling, secrets, user data | security-review (in addition to adversarial-review) |
| New trust boundary at design time (external interface, auth surface, user-data store, 3rd-party integration) | threat-modeling (alongside compose) |
| Cutting a release, bumping a version, flipping a flag | release-management |
| User-visible behavior change | user-docs (docs diff in the same change) |
| Any commits shipping (Tier 1+) | version-control (checked during verify) |
| Ambiguous ask, no clear done-condition | requirements-elicitation (BEFORE tier classification) |
| A design doc / RFC to write | tech-doc |
| A hard-to-reverse system decision | software-architecture (ADR) |
| UI screens | ux-design (flow first) → ui-design |
| A PR reviewed by / authored for humans | human-code-review |
| Any new/renamed identifiers shipping | naming (as part of verify) |
| LLM calls | ai-building; + ai-safety the moment it gets tools |
| Sizing or roadmap questions | estimation (after deconstruct, never before) |

## Which Review?

Four skills review; they answer different questions — don't substitute one for another:

- **verify** — did I build what I planned? (self, every Tier 1+, includes a 3-vector self-attack)
- **adversarial-review** — where does this diff break? (independent 6-vector hunt, Tier 2+)
- **security-review** — who can abuse this? (depth pass on touched security surfaces)
- **human-code-review** — the social/PR loop (labels, altitude, tone) when humans are involved

## Escalation Triggers

Reclassify UPWARD immediately (never downward) when any of these fire mid-task:
- The diff is growing past what the tier predicted (Tier 1 exceeding ~2 files → stop, reclassify Tier 2)
- You discover an undocumented dependency or side effect
- A pass condition fails twice for the same reason — the model of the problem is wrong; return to compose (entering it if the tier previously skipped it)
- You're tempted to say "while I'm here, I'll also..." — that's a new task; classify it separately

## Loop-Until-Dry

For Tier 2+, verification is not one pass — it repeats until dry:

1. Run verify (pass conditions + 3-vector self-attack)
2. Fix everything found
3. Run verify again on the fixes
4. Repeat until a full pass finds **zero new issues**
5. Only then is the task complete

Two consecutive clean passes for anything touching auth, payments, or data migration.

## Conventions (all skills inherit these)

- **Artifacts** go to `.claude/plans/{task-name}-{skill}.md` (e.g. `login-cache-compose.md`, `login-cache-verify.md`)
- **Verdict vocabulary**: reviews conclude `SHIP` / `FIX FIRST` / `BLOCKED`; verifications conclude `PASS` / `FAIL`
- A skill's "when to apply" defers to this router; local thresholds in older skills are superseded by the tiers

## How to Apply

At the start of every task, declare the classification before acting — and write the same line at the top of the task's first artifact (or state it in your reply for Tier 0/1, where no artifact exists):

```
Tier: 2 (touches 4 files, introduces new cache interface)
Lanes: api-design, qa-testing
Pipeline: compose → plan-mode → deconstruct → verify → adversarial-review
```

This declaration is cheap and makes the discipline auditable — the user can see the tier and object before work begins, and a skipped skill is visible rather than silent.

## Anti-Patterns

- Classifying by effort estimate instead of blast radius — a 5-line change to auth middleware is Tier 2
- Downgrading a tier mid-task because the work "turned out to be easy"
- Running the full pipeline on a typo to look diligent — discipline theater erodes trust in the system
- Skipping the tier declaration and back-filling it after the code is written
- Declaring the tier but skipping the lane scan — the lanes are where security-review and qa-testing get skipped silently
- Treating loop-until-dry as done after one clean-ish pass with "minor" findings ignored
