---
name: dependency-management
description: Dependency-management skill — vetting before adopting, pinning with lockfiles, deliberate upgrade cadence, and the exit plan for every dependency
metadata:
  type: user
---

# Dependency Management — Supply Chain Skill

## Why

Every dependency is code you now ship but don't control: its bugs are your bugs, its CVEs are your CVEs, its maintainer's burnout is your 2am incident. Smaller models add dependencies the frictionless way — `npm install whatever-solves-it` — and never look again, until an upgrade breaks everything at the worst time or a supply-chain attack ships through the lockfile nobody reviews. This skill treats the dependency tree as an owned asset: additions vetted, versions pinned, upgrades scheduled, and every dependency carrying an exit plan.

## The Rule

**Adding a dependency is an architectural decision — vetted before adoption, pinned by lockfile, and upgraded on a schedule you chose rather than a schedule that chooses you.**

## How to Apply

### 1. Vet before adopting

Before adding anything non-trivial, answer in writing — one paragraph in the PR description or `.claude/plans/{task-name}-deps.md`, or an ADR via software-architecture if it's load-bearing. The paragraph must exist BEFORE install:

- **Build vs buy honestly**: what would writing the needed 20% ourselves cost? A 5MB library for one function is a bad trade; re-implementing crypto is a worse one. (Never hand-roll: crypto, auth protocols, timezone math, parsers for standard formats.)
- **Health check**: recent releases and commits, issue-tracker responsiveness, more than one maintainer, download trend, open CVEs
- **Blast radius**: what does *it* depend on? Ten transitive maintainers you've never heard of are part of the deal
- **License**: compatible with how you ship (copyleft in a proprietary binary is a legal incident)
- **Exit cost**: if this dies tomorrow, what's the migration? A dependency used behind your own thin interface at 3 call sites is replaceable; one woven through every module is a marriage.

### 2. Pin everything, reproducibly

- Lockfile committed, always — builds must be byte-reproducible from the repo (see infra-ops: if it isn't in version control, it doesn't exist)
- CI installs *from* the lockfile (`npm ci`, `pip install -r` with hashes, `cargo --locked`); an install that resolves versions at build time is a supply-chain lottery ticket
- Internal version ranges are for libraries you publish; applications pin exact

### 3. Upgrade on a cadence, not in a crisis

- **Scheduled small upgrades** (monthly-ish): patch/minor batches, changelogs skimmed, full test suite as the gate. Many small upgrades are strictly cheaper than one giant one — the 3-years-behind major-version jump is a code-migration project wearing a chore's clothes.
- **Security patches**: out-of-band, immediately, via automated advisories (Dependabot/Renovate/audit tooling) — this is the one upgrade class that doesn't wait for the cadence. CVE/advisory handling routes through security-review.
- **Major versions**: each is a mini-project — read the migration guide *before* starting, route through tierless-router tiering, upgrade one major thing per PR
- Never upgrade + refactor + feature in one change (same separation law as refactoring)

### 4. Prune

Quarterly or per build-loop phase exit: remove unused dependencies (they still carry CVEs and install-time attack surface), replace the deprecated, and check whether that polyfill is now in the standard library. The best dependency count is the lowest one that doesn't have you hand-rolling crypto.

## Evidence Gate (before declaring done)

- No dependency lands without the written vet answers
- No upgrade lands without green suite + lockfile diff reviewed

## Anti-Patterns

- Installing the first search result to solve one function (left-pad was real)
- No lockfile, or a lockfile in .gitignore ("it works on my machine" — different machine, different tree)
- Ignoring advisory bots until the list hits 200 and everyone scroll-past-clicks (that's alert fatigue; fix the cadence)
- Upgrading everything at once when something finally forces it — 40 changed dependencies, one broken app, zero attribution
- Wrapping *every* dependency in an abstraction layer reflexively (pay the seam cost for the risky/replaceable ones, not for the framework)
- Vendoring/forking to "fix one thing" without a plan to get back on mainline (congratulations, you're the maintainer now)
