---
name: adversarial-review
description: Adversarial-review skill — standalone code review focused on finding bugs, not confirming correctness
metadata:
  type: user
---

# Adversarial Review — Code Review Skill

## Why

Most code reviews (including self-reviews) confirm that the code works. They don't look for where it breaks. This skill inverts that: the goal is to find bugs, not confirm correctness. If the code survives the review, it's probably good.

This is one of four review skills — they answer different questions (see tierless-router's "Which Review?" table). Adversarial-review asks *where does this diff break*. Security depth on auth/input/secrets/user-data surfaces belongs to security-review ("who can abuse it"); the social/PR process — labels, altitude, tone — belongs to human-code-review. Don't substitute one for another.

## The Rule

**Every Tier 2+ change (per tierless-router) must undergo an adversarial review.** Review the diff cold, as if authored by someone else — fresh context, no memory of writing it; a separate agent when available. The reviewer's only job is to find problems.

## How to Apply

After a change is implemented, before it ships:

1. **Read the diff.** Not the code — the diff. Focus on what changed.
2. **Apply each attack vector below.** For each one, document your finding.
3. **Write the report** to `.claude/plans/{task-name}-adversarial.md`.

## Attack Vectors

### 1. Input Injection
- What if the input is {empty, null, very long, malformed, unicode, binary}?
- What if the input contains {SQL, HTML, script tags, template strings}?
- What if the input comes from an untrusted source?

### 2. State Corruption
- What if the database is in an unexpected state?
- What if a file is locked or missing?
- What if a network call returns {timeout, 500, 200 with wrong body}?

### 3. Concurrency
- What if two requests hit this at the same time?
- What if the function is called recursively or re-entrantly?
- What if there's a race between check and action?

### 4. Boundary Conditions
- What if the number is 0, -1, NaN, Infinity?
- What if the array is empty, has one element, or is huge?
- What if the date is in the past, future, or leap year?

### 5. Privilege Escalation
- Can a user do something they shouldn't be able to?
- Can the code access resources it shouldn't?
- Are there implicit trust assumptions?

### 6. Regression
- What existing functionality does this break?
- Are there callers of the changed function that expect different behavior?
- Are there integration points that assume the old behavior?

## The Review Report

Written to `.claude/plans/{task-name}-adversarial.md`:

```markdown
## Adversarial Review: {change-description}

### Date: {date}

### Findings:
1. {file:line} — {what breaks, how likely, impact}
   Trigger: {the concrete input or state that produces the failure}
2. {file:line} — {what breaks, how likely, impact}
   Trigger: {the concrete input or state that produces the failure}

### Severity:
- Critical: {count} — must fix before ship
- Medium: {count} — should fix, can ship with documented risk
- Low: {count} — nice to fix, can defer

### Verdict: {SHIP / FIX FIRST / BLOCKED}
```

Every finding needs the concrete input or state that triggers it — the same standard as security-review's exploit path. "This might race" is not a finding; "two concurrent POSTs to /jobs both pass the exists-check on line 42 and insert duplicates" is.

## Anti-Patterns

- Reviewing with the author's assumptions still loaded — the review must read the diff cold, as production will
- Reviews that say "looks good" without going through all six vectors
- Zero findings on a FIRST pass over a Tier 2 change (you didn't look hard enough — later clean passes are loop-until-dry terminating correctly)
- Treating low-severity findings as blockers
- Skipping the review because "it's a small change" — the smallest changes have the least review attention and the most bugs