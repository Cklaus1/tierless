# Changelog

All notable changes to this project. Dates are absolute (YYYY-MM-DD).

## [Unreleased]

### Named
- **Project named "Tierless"** (2026-07-11) — "make a cheaper model perform a tier above its size."
  Chosen after collision-checking 34 candidate names across the AI-dev-tool namespace (two batched
  15-name workflow runs plus targeted checks). Nearly every self-evident name — Sensei, Prodigy,
  Understudy, Boost, TierUp, LevelUp, SkillForge, Skillstack — was already taken by a direct
  competitor in the "discipline skills for coding agents" space, which is confirmed crowded (Boost
  OS, Whetstone, Understudy Labs, Caliber, Skillsmith all ship near-identical pitches). Tierless
  came back CLEAR: no company, product, or trademark; only an unrelated academic "tierless
  programming" CS term as minor SEO noise. On-thesis (erase the model tier gap) and domain-viable.
- **Renamed the router skill** `fable-discipline` → `tierless-router` and scrubbed remaining "Fable"
  branding across all skill files, readme, and skills index (21 files touched, references updated,
  file history preserved via `git mv`).

### Added
- **Eval harness** (`eval/`) — the project's first evidence mechanism. Six tell-based
  tasks (bug-hunt, ambiguous-ask, mvp-scope, migration-plan, security-review + a hard
  variant, decompose), a binary-tell rubric with a gap-closure metric, three-arm run
  protocol (bare-small / skills-small / reference), and a blind-grading workflow.
- **Task 05b** (security-hard) — a discriminating security task where the auth is
  *present but wrong* (client-supplied org_id, unchecked related-object reattach),
  after 05 was found to be at ceiling (bare model scored 5/5).
- **Task 07** (build-loop paired eval) — a multi-feature build scored on PROCESS
  (walking skeleton, phases, per-phase verification, resumable trail) not just output,
  to measure the one skill a single-shot eval can't. Designed; not yet run.
- **First full 6×3 matrix run** (2026-07-11) — 36 agents, blind-graded. Results and
  honest analysis in `eval/results/SCORES.md`.
- **`LESSONS.md`** — what the build-and-eval process taught us, including where the
  skills helped, where one backfired, and harness bugs found.
- **Git repository** — project is now version-controlled (was a loose directory).
- **`.gitignore`** — excludes `cache/`, `.claude/plans/`, Python bytecode.

### Changed
- **All 36 skills audited and revised** (five independent audit agents + four parallel
  fix agents). Scrubbed model-specific branding ("Sonnet"/"Fable 5's"), added
  verification/evidence gates to every skill, wired orphan skills into the router via
  Conditional Lanes, added the "Which Review?" table, standardized artifact paths and
  verdict vocabulary, fixed the plan-vs-deconstruct boundary, added loop-until-dry to
  verify.md, rewrote naming.md from principles into an enforced pass.
- **`tierless-router` router** gained requirements-elicitation as step zero (before
  tier classification) and lanes for threat-modeling, release-management, user-docs,
  version-control.

### Skill count over time
- Round 1 (initial): 4 skills (compose, plan-mode, deconstruct, verify)
- Round 2: +5 (roadmap, onboarding, adversarial-review, naming, + router/build-loop)
- Round 3: tierless-router router, build-loop, security-review, qa-testing, ui/ux, icp
- Round 4: debugging, refactoring, code-archaeology, api-design, data/code-migration,
  performance, dependency-management, incident-response, tech-doc
- Round 5: 9 domain skills (ai-building, ai-safety, systems, compiler, architecture,
  database, shell, infra, cross-platform)
- Round 6: 5 gap skills (requirements-elicitation, version-control, user-docs,
  release-management, threat-modeling)
- **Current: 36 skills**, all wired and audited.

### Fixed
- **Eval fixture-corruption bug** (LESSONS #7, #8) — file-mutating tasks had arms editing
  shared `context/` fixtures in place, corrupting them for concurrent arms. Fixed at the
  source: grid arm-prompts now forbid file writes ("context/ is read-only; solution goes
  in your response"), since the grader scores response text, not disk. Added
  `eval/scripts/guard-fixtures.sh` (neutral, no-spoiler DO-NOT-EDIT headers) and a
  fixture-isolation section in `run.md`. Guard applied to fixtures after the in-flight
  grid completes.

### Known issues
- Eval single-run→ upgraded: the v2 grid (`tierless-eval-grid`) runs N=3 per cell across
  a full model×skills ladder. First grid run in flight.
- Task 07 (build-loop) designed but not yet executed.
- Core claim ("skills close the cheap→frontier gap") NOT yet validated at significance;
  v1 showed one clean mechanism (task 01) and one backfire (task 03).
