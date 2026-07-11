---
name: human-code-review
description: Human-code-review skill — reviewing (and being reviewed by) humans: altitude first, blocking vs nit separated, critique the code not the coder, and PRs authored to be reviewable
metadata:
  type: user
---

# Human Code Review — Collaborative Review Skill

## Why

Adversarial-review finds bugs in a diff; this skill is the *social* discipline around review — where the failure modes are human, not technical. Reviews that nitpick formatting while an architectural mistake sails through. Feedback phrased so the author digs in instead of fixing. Twenty-file PRs that get a rubber-stamp "LGTM" because thorough review would take a day. An AI agent participating in a team's review loop — as reviewer or as author whose code humans review — needs this discipline as much as any engineer.

## The Rule

**Every review comment carries an explicit weight label — [blocking], [should], or [nit] — so the author never has to guess what blocks merge.**

## Reviewing: How to Apply

Review altitude-first (does this change make sense at all?) before line-by-line, and critique code, never authors.

### 1. Altitude first — three passes, stop when one fails

1. **Direction** (minutes): Does this change belong? Right approach for the problem? Fits the architecture (check ADRs)? If no — say so *now*, kindly, before critiquing details of code that shouldn't exist. Line comments on a wrong-direction PR are cruelty by thoroughness.
2. **Design** (the real pass): boundaries, data flow, error handling, tests match behavior contracts (qa-testing), no scope smuggled in
3. **Lines** (last): correctness details, naming, the stuff adversarial-review hunts — and if the diff touches auth, input handling, secrets, or user data, confirm a security-review pass exists (or run one)

### 2. Label every comment's weight

Three explicit tiers — the reader must never have to guess what blocks merge:
- **[blocking]** — correctness, security, data loss, contract breaks: must fix, with the *why* stated
- **[should]** — real improvement, author may defer with a reason (e.g., a follow-up ticket)
- **[nit]** — preference; author decides, zero follow-up if declined. Style that a formatter/linter could enforce belongs in the formatter (add a lint/formatter rule), not in review comments — every recurring nit is a missing lint rule.

### 3. Critique the code, ask about the intent

- "This function re-reads the file per iteration — was that intentional for freshness, or can we hoist it?" beats "why would you do this"
- Comments reference the code ("this loop"), never the person ("you always")
- Questions where you're unsure; statements where you're sure; never sarcasm anywhere
- Say what's *good*, specifically, when it is — "this test names the failure mode perfectly" teaches as much as any correction

### 4. Approve like it means something

- Approve when remaining items are nits — don't hold a PR hostage for preferences
- Never rubber-stamp what you didn't read: if you can't review it properly, say so and either timebox a partial review ("reviewed the migration, skipped the test fixtures") or hand off
- Review latency is a team SLA: a day-old unreviewed PR is a blocked teammate and a growing rebase. Reviews outrank starting new work.

## Being Reviewed: How to Apply

Author your own changes to be reviewable in under 30 minutes — reviewability is authored, not hoped for.

- **Size for review**: one concern per PR, reviewable in <30 min. The deconstruct steps are natural PR boundaries; a 2000-line "and also" PR *guarantees* shallow review — big change? Stack small PRs.
- **Description carries the context**: what, why, how verified (verify artifact link), what you're unsure about — flag your own doubts ("not sure this lock ordering is right") to aim the reviewer at the risk
- **Respond to every comment** — fix, or reply with reasoning; silent-ignore poisons the loop. Push back with arguments, not defensiveness: the reviewer read your code cold, which is exactly how production will read it.
- **Never merge over an unresolved [blocking]** — resolve it with the reviewer, or escalate; merging past it is a trust withdrawal you can't easily repay

## Pre-Merge Evidence Gate

Before merge, all four must be checkable:

- [ ] Every review comment carries a weight label ([blocking]/[should]/[nit])
- [ ] Every [blocking] is resolved or explicitly escalated — none merged over
- [ ] The PR is reviewable in <30 minutes, or was stacked into PRs that are
- [ ] The PR description links the verify artifact

## Anti-Patterns

- Nitpicking whitespace on a PR whose approach is wrong (altitude inversion — the worst review failure)
- Unlabeled comments where the author can't tell blocking from preference
- "LGTM" on 2000 lines after four minutes (say "didn't fully review" if that's the truth)
- Re-litigating settled architecture in a line comment (that's an ADR discussion — see software-architecture)
- Author treating every comment as an attack; reviewer treating every pushback as insubordination
- Style wars in comments that a formatter config would end permanently
- Using review to redesign the PR into the reviewer's pet approach when the author's approach also works
