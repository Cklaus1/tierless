---
name: user-docs
description: User-docs skill — READMEs, guides, API references, and changelogs written for the reader's task, verified by executing every instruction
metadata:
  type: user
---

# User Docs — Documentation-for-Readers Skill

## Why

Smaller models document what they just built, in the order they built it, from the author's seat: a feature inventory instead of a task path, examples that were never run, install steps that skip the prerequisite the author already had. The result reads fine and fails in the reader's hands — the copy-pasted command errors on line one, and the doc's credibility (and the product's) dies with it. tech-doc covers design documents for decision-makers; this skill covers documentation for *users* — README, getting-started, how-to guides, API reference, changelog — where the test of quality is not "is it complete" but "did the reader's task succeed."

## The Rule

**Write for the reader's task, not the code's structure — and execute every instruction and example yourself before shipping it.** An untested code block is a bug you're publishing.

## How to Apply

### 1. Pick the doc type deliberately — they don't mix

- **Getting started / tutorial**: one guaranteed-success path, zero choices, working result in minutes — teach by doing
- **How-to guide**: recipe for one real task the reader already wants ("rotate an API key"), assuming basic familiarity
- **Reference**: complete, accurate, lookup-oriented (every option, every error) — no narrative
- **Explanation / concepts**: why it works this way — for the reader who needs the model, not the steps

A README is a routing page: what this is (one paragraph), the 5-minute quickstart, links into the four types. The most common failure is a tutorial that keeps lapsing into reference ("you could also pass --format, --output, --verbose...") — cut the options, keep the path.

### 2. Start from the reader, not the feature

For each doc, one line before writing: *who arrives here, knowing what, to do what?* Then write only what serves that. The curse of knowledge is the enemy — the author knows which directory to run from, which env var is already set, which error is ignorable; the reader knows none of it. Every prerequisite stated, every step from an actually-clean starting point.

### 3. Examples are the documentation

- Readers execute examples and skip prose — lead with the example, explain after
- Every example: complete (runs as pasted, no invisible setup), realistic (real-shaped values, not `foo`/`bar`), and current (re-verified when the code changes)
- Show the expected output — the reader's only way to know it worked
- Document the errors too: the three most likely failures per task, what they look like, what fixes them (the empty/error path is UX here just as in ui-design)

### 4. Changelogs and versioned docs

- Changelog entries state user-visible impact, not commit summaries: "uploads over 10MB no longer time out", not "refactored upload handler"
- **Breaking changes**: flagged loudly, with the migration path inline — every breaking entry answers "what do I change in my code"
- Docs version with the code: the PR that changes behavior updates the docs in the same PR (a lane concern for verify), or the docs lie by the next release

### 5. Maintenance is part of shipping

Every code change that alters user-visible behavior carries a docs diff — grep the docs for the touched command/endpoint/option and update the hits. Docs with no owner rot into anti-documentation: worse than nothing because they're trusted.

## Anti-Patterns (gaming behaviors)

- Writing examples from memory of the API and marking the doc done without running them ("it's obviously right")
- Testing instructions in the author's already-configured environment and calling the from-scratch path verified
- Restructuring the docs to mirror the module tree because it was easy to generate — the reader's task doesn't follow your imports
- The changelog entry written from `git log` instead of from user impact — technically complete, communicating nothing
- Answering a known doc gap with "the code is self-documenting"
- Padding a thin tutorial with pasted reference tables to look thorough — length signaling completeness the doc doesn't have

## Verification

Done means evidence, not vibes:
- [ ] Every code block and command executed from a clean environment (fresh clone / clean shell) — transcript or output attached to the verify artifact; UNMEASURED with a reason where a clean environment is genuinely unavailable
- [ ] Expected output shown for every example
- [ ] Each doc's one-line reader statement (who / knows what / doing what) exists — written before the doc
- [ ] For changes: grep of docs for touched surfaces attached, all hits updated or justified
- [ ] Breaking changes: migration path present in the changelog entry

Verdict is PASS/FAIL; a doc whose examples were never run is a FAIL regardless of prose quality.
