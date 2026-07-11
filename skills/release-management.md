---
name: release-management
description: Release-management skill — versioning, release cuts, feature flags, and rollout as a process: what ships, when, behind what, and how it comes back
metadata:
  type: user
---

# Release Management — Shipping Process Skill

## Why

Smaller models conflate "merged" with "shipped": version numbers bumped by vibes, releases cut from whatever main contains that day, features landing enabled-for-everyone because a flag felt like extra work. The gaps compound at the seams the other skills don't own — infra-ops covers the deploy *mechanics*, api-design covers *contract* evolution, user-docs covers the *changelog text* — but nobody owns the decision layer: what constitutes this release, what version number it carries, what's behind a flag, in what stages it reaches users, and what "pull it back" means. That layer is this skill.

## The Rule

**Every release is a deliberate cut with a version that encodes its compatibility, contents that are enumerated, and a rollback that was decided before rollout began.** "Ship whatever's on main" is not a release process; it's a lottery with users as the audience.

## How to Apply

### 1. Version numbers are contracts, not counters

- Semver semantics enforced by diff review, not by feel: MAJOR = something breaks for someone upgrading, MINOR = additive, PATCH = fixes only
- The question at cut time is mechanical: "can every current user upgrade without changing anything?" No → major. New capability? → minor. Neither → patch.
- Pre-1.0 is not a semver escape hatch users can't see — if people depend on it, breaking changes get the same loud flagging (see user-docs' changelog rules)
- Internal services without external consumers may use dates/build numbers — but *decide* the scheme once (an ADR-sized decision, see software-architecture) and follow it always

### 2. The release cut is a checklist, not a moment

Write the release record to `.claude/plans/{version}-release.md` at cut time:

```markdown
## Release: {version}
**Cut from:** {commit/branch} **Date:** {date}
**Contents:** {enumerated — the changes in this release, by scanning main..last-release, not by memory}
**Version bump justified by:** {the specific breaking/additive/fix change that sets the number}
**Flags shipping OFF:** {list} **Flags flipping ON:** {list, with rollout stage}
**Rollback:** {revert the deploy / flip flags off / restore version N — decided NOW}
**Migration required:** {none | link to data-migration plan}
```

- Release branches or tags cut the release — main keeps moving; the release doesn't chase it
- Nothing enters the release after the cut except fixes *for the release itself* (cherry-picked, listed)

### 3. Flags decouple deploy from release

- Deploying code and releasing a feature are two events — anything user-visible and non-trivial ships behind a flag, OFF, then flips on in stages
- Rollout stages by blast radius: internal → canary percentage → everyone; the watch-metric per stage named before the flip (infra-ops owns the metric mechanics)
- Flags are debt with a lifespan: every flag gets a removal date at creation; a flag past its date is a build-loop task, not background radiation
- The flag OFF path stays tested until the flag is deleted — an untested OFF path means the "rollback" is fiction

### 4. Rollback is a release-level decision

Before any stage flips: does pulling this back mean flag-off (seconds), redeploy previous version (minutes), or data un-migration (see data-migration — hours and ceremony)? If the honest answer is the third, the release plan says so and the stage gates get correspondingly conservative. The worst release-day sentence is "we can't easily go back" — discovering it *on* release day is the process failure this skill exists to prevent.

### 5. The release is announced, not just cut

- Changelog entry per user-docs discipline (impact, not commits; migration paths for breaks)
- Versioned docs published with the release, not after
- Consumers of APIs get deprecation windows measured in releases, not surprise removals (api-design owns the contract; this skill owns the calendar)

## Anti-Patterns (gaming behaviors)

- Bumping MINOR for a breaking change because a MAJOR "looks bad" — the number is now lying to every consumer's dependency resolver
- Enumerating release contents from memory instead of the actual diff — the release notes describe the release you *think* you cut
- Shipping the flag but hardcoding it ON "temporarily" — flag theater with none of the rollback value
- Declaring the rollback path "redeploy previous" without checking whether this release's migration made the previous version unrunnable
- Cutting the release, then slipping "one more small thing" onto the tag — the tested artifact and the shipped artifact silently diverge
- A canary stage that watches no named metric — staged rollout as ritual, every stage auto-promoted

## Verification

Done means evidence, not vibes:
- [ ] `.claude/plans/{version}-release.md` exists, written at cut time — contents enumerated from the actual range diff
- [ ] Version bump justified against the diff (the breaking/additive change named, or "none → patch")
- [ ] Every new flag has an owner and a removal date; every flipping flag names its stage and watch-metric
- [ ] Rollback path stated and *checked* (previous version actually runs against current state; flag-off path actually tested)
- [ ] Changelog and docs shipped with the release

Verdict is PASS/FAIL; a release cut without its record is a FAIL even if nothing broke.
