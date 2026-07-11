---
name: cross-platform
description: Cross-platform skill — discipline for code targeting multiple OSes (Unix/Windows/macOS/Android/iOS): platform differences cataloged, seams isolated, every target actually tested
metadata:
  type: user
---

# Cross-Platform — Multi-Target Skill

## Why

Smaller models write for the platform in their head (usually Linux) and call it portable. Then the paths break on Windows, the lifecycle kills the process on Android, the filesystem turns out case-insensitive on macOS, and line endings corrupt the first binary file. Platform differences aren't edge cases — they're a *dimension of the requirements*. This skill makes the targets explicit, the differences cataloged, and the platform-specific code quarantined behind seams.

## The Rule

**A platform you haven't tested on is a platform you don't support — you just haven't announced it yet.**

## How to Apply

Name the target platforms in the plan, catalog the differences that touch your feature, and isolate every platform-specific behavior behind a seam.

### 1. Declare targets and their floor versions

In the plan-mode artifact: which OSes, which minimum versions, and which are *tier 1* (CI-tested, release-blocking) vs *tier 2* (best-effort). This is a product decision (roadmap), not something discovered from bug reports.

### 2. Catalog the differences that touch this feature

The differences themselves are knowledge you have; the process is: walk the categories below for whatever the change touches, and write the hits into the compose artifact.

- **Filesystem** (e.g. case sensitivity: `Foo.txt` == `foo.txt` on macOS/Windows)
- **Text** (e.g. CRLF/LF line endings)
- **Processes & signals** (e.g. fork doesn't exist on Windows)
- **Lifecycle — mobile** (e.g. Android/iOS kill and restart your process at will)
- **Timing & locale** (e.g. wall clocks jump; use monotonic clocks for durations)
- **Environment** (e.g. HOME vs USERPROFILE, XDG vs AppData)

### 3. Quarantine the platform code

- One seam: a `platform` module/interface with per-OS implementations chosen at build- or run-time — platform conditionals (`#ifdef`, `if os ==`) appear *only inside* that module, never sprinkled through business logic
- Business logic is platform-free and unit-testable without any OS in the loop
- Prefer the ecosystem's abstraction (std lib path/process APIs, established cross-platform libs) over hand-rolled seams — but *verify* the abstraction covers your case; "cross-platform" libraries have Linux-shaped assumptions too

### 4. Test on the actual targets

- CI runs the tier-1 matrix (GitHub Actions and friends make Linux/macOS/Windows cheap; mobile gets emulator jobs) — a green Linux build says nothing about Windows
- Platform-specific bugs get platform-specific regression tests, run on that platform
- Test the ugly cases per platform: paths with spaces and unicode, case-collision filenames, process-death restore (mobile), non-UTF8 locale (Unix)

## Anti-Patterns

- Declaring a target tier-2 retroactively to excuse the failing CI job — tiers are decided in the plan, not negotiated with red builds
- Walking the difference catalog after the code is written and recording "no hits" — a post-hoc catalog audits nothing
- Platform conditionals scattered through business logic instead of quarantined at the seam
- Treating Android like a small Linux server (the lifecycle *is* the platform)
- Fixing a Windows bug blind because CI doesn't run Windows ("this should work" — it doesn't)
- Supporting platforms by accident: no declared tiers, so every user-found breakage is an implicit contract you never agreed to

## Verification

Done means evidence, not vibes:
- CI links attached: one green run per tier-1 target, for the change being shipped
- The difference-catalog hits from §2 are in the compose artifact
- Verdict is PASS/FAIL; a tier-1 target with no linked green run is unsupported, and the change is a FAIL
