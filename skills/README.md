# Tierless Skills

Each `.md` file in this directory (except this index) is a Claude Code skill — a discipline framework that makes a smaller model follow the structured process a frontier model applies implicitly. Symlinks in `.claude/skills/` point here; run `./scripts/project-init` after adding a skill.

## Routing & Structure

- **tierless-router** — THE ENTRY POINT. Classifies task weight (tier 0–3) and prescribes which skills to layer; defines loop-until-dry and escalation triggers
- **build-loop** — the outer loop for multi-session projects: phased delivery with entry/exit gates, persisted in `.claude/plans/build-loop.md`

## Core Pipeline (in order)

0. **requirements-elicitation** — clarify the ambiguous ask BEFORE tier classification: restate with a done-condition, surface assumptions, ask the questions that fork the approach
1. **compose** — understand the problem: read the code, map architecture and data flow, mark assumptions, assess risk
2. **plan-mode** — design the solution: scope, file list, steps, edge cases, verification commands, rollback plan
3. **deconstruct** — break the design into atomic steps (<50 lines each), dependency-ordered, each with a pass condition
4. **verify** — the exit gate: run pass conditions, adversarial self-review (3 attack vectors), regression check

## Specialist Engineering

- **debugging** — hypothesis-driven root-cause hunting: reproduce → hypothesize → observe → fix once; bans shotgun fixes
- **refactoring** — behavior-preserving restructuring: green → one transformation → green → commit
- **code-archaeology** — understanding legacy/unfamiliar code before changing it: boundaries, git history, invariants, Chesterton's Fence
- **api-design** — contract-first endpoints and interfaces: consumer examples first, errors as part of the contract, additive evolution
- **data-migration** — expand → migrate → contract; reversible, rehearsed, verified by counting
- **code-migration** — framework/language/platform ports: strangler over rewrite, vertical slices behind a seam, equivalence proven, old path deleted
- **performance-optimization** — profile-before-optimize loop: target number, real workload, one change per measurement, stop at done
- **dependency-management** — supply chain: vet before adopting, pin by lockfile, scheduled upgrade cadence, exit plan per dependency
- **incident-response** — production-down discipline: mitigate first (revert!), diagnose second, fix third
- **tech-doc** — design docs and RFCs: problem before solution, steelmanned alternatives, numbers not adjectives
- **naming** — identifier and file-naming conventions; run before merge
- **version-control** — atomic commits with why-messages, branch hygiene, history as a debugging tool; checked during verify

## Domain Disciplines

Knowledge the model already has; these encode the *process* it skips in each domain:

- **ai-building** — LLM features: evals before prompt tuning, structured output at the boundary, cost/latency budgets, failure paths designed as features
- **ai-safety** — agentic systems: least privilege enforced by environment (not prompt), tiered action gates, bounded loops, injection assumed, failure-mode evals
- **software-architecture** — system design: hard-to-reverse decisions recorded as ADRs with rejected alternatives, boundaries by change-rate, boring by default
- **database-design** — data layer: constraints in the database, queries proven with EXPLAIN at realistic scale, changes routed through data-migration
- **systems-programming** — OS/kernel/embedded: invariants written first (ownership, lock ordering, lifetimes), fault injection, crash-consistency tests, sanitizers in CI
- **compiler-building** — languages/parsers/DSLs: spec before code, staged pipeline with per-stage contracts, testing as ~half the work, diagnostics as UX
- **shell-scripting** — Unix automation: strict mode, quoting as correctness, idempotency, escalate to a real language past plumbing
- **infra-ops** — servers/CI/CD/IT: everything as code, staged reversible deploys, observability and runbooks before incidents, rehearsed restores
- **release-management** — versioning as contract, enumerated release cuts, flags with removal dates, rollback decided before rollout
- **user-docs** — READMEs/guides/references/changelogs written for the reader's task, every instruction executed before shipping
- **cross-platform** — Unix/Windows/macOS/Android targets: differences cataloged per feature, platform code quarantined behind seams, every tier-1 target in CI

## Review & Quality

- **adversarial-review** — independent bug hunt over a diff using six attack-vector categories
- **human-code-review** — the social discipline of review: altitude first, blocking/should/nit labels, critique code not coders, author PRs to be reviewable
- **security-review** — vulnerability pass keyed to the surfaces the change touches; every finding needs an exploit path
- **threat-modeling** — design-time security: assets, attackers, trust boundaries modeled BEFORE code exists; the output is design changes
- **qa-testing** — test plans designed from behavior contracts (not implementation), validated by mutation

## Product & Design

- **roadmap** — phase a project into MVP / v1 / v2+ with explicit out-of-scope lists
- **estimation** — reference-class sizing: ranges with named risks, derived from the deconstruction, closed-loop against actuals
- **ui-design** — visual craft: token system, hierarchy, five component states, accessibility floor
- **ux-design** — flow design before screen design: journeys, friction audit, error recovery, interaction contracts
- **icp-onboarding** — the product's first-run experience: signup → the ideal customer's first win
- **onboarding** — developer onboarding: zero to first contribution in one session

## How to Layer Them

Start with tierless-router; it routes. The short version:

| Task | Skills |
|---|---|
| Ambiguous ask, no clear done-condition | requirements-elicitation (before anything else) |
| Trivial edit (typo, config value) | none |
| Medium (1–2 files, known pattern) | deconstruct → verify |
| Hard (3+ files, new architecture, auth/payments/migrations) | compose → plan-mode → deconstruct → verify → adversarial-review |
| New project / major feature | roadmap → build-loop, discipline pipeline per task inside each phase |
| Bug report | debugging (then the fix routes through its own tier) |
| Restructuring code without behavior change | refactoring |
| New/renamed identifiers shipping | naming (checked during verify) |
| New developer joining the project | onboarding |
| Production incident | incident-response (mitigate), then debugging (root cause), then normal pipeline (fix) |
| Unfamiliar / legacy code | code-archaeology before anything else |
| New endpoint / interface / library surface | api-design before implementation |
| Schema or data change | data-migration (always tier 2+) |
| Framework / language / platform port | code-migration (data moves via data-migration) |
| "Make it faster" | performance-optimization (profile first, always) |
| Adding or upgrading dependencies | dependency-management |
| Reviewing a teammate's PR / authoring one for humans | human-code-review (+ adversarial-review for the bug hunt) |
| Sizing work / roadmap items | estimation (after deconstruct, never before) |
| Design doc / RFC | tech-doc |
| System-level design decision | software-architecture (ADR), informed by tech-doc |
| LLM-powered feature | ai-building; + ai-safety the moment it gets tools |
| Schema / query work | database-design (changes via data-migration) |
| OS / kernel / embedded / concurrency-heavy | systems-programming |
| Parser / interpreter / DSL | compiler-building |
| Shell script beyond ~10 lines | shell-scripting |
| Servers, deploys, CI/CD, IT ops | infra-ops |
| Multi-OS or mobile target | cross-platform |
| Shipping a UI | ui-design + ux-design during build; qa-testing + security-review before exit |
| New trust boundary at design time | threat-modeling (alongside compose; security-review verifies the controls later) |
| Cutting a release / bumping a version / flipping a flag | release-management |
| Docs, README, changelog for users | user-docs (tech-doc is for design docs) |
| Commits going to review | version-control (checked during verify) |
| Launching to customers | icp-onboarding |

## Skill Anatomy

Each skill follows the same structure so they're cheap to learn and audit:

1. **Why** — the failure mode it prevents
2. **The Rule** — the non-negotiable principle
3. **How to Apply** — concrete steps and an artifact template (written to `.claude/plans/`)
4. **Anti-Patterns** — the specific ways the rule gets gamed

## Adding a Skill

1. Create `skills/{name}.md` with frontmatter (`name`, `description`, `metadata.type: user`) following the anatomy above
2. Run `./scripts/project-init` to refresh the `.claude/skills/` symlinks
3. Add it to this index under the right category
