---
name: requirements-elicitation
description: Requirements-elicitation skill — clarify the ambiguous ask before any work begins: surface hidden assumptions, ask the questions that change the answer, confirm the contract
metadata:
  type: user
---

# Requirements Elicitation — Understand-the-Ask Skill

## Why

Given an ambiguous request, smaller models pick the most statistically likely interpretation and sprint — building confidently toward a goal the user never stated. "Add caching" becomes Redis when the user meant memoization; "make it faster" gets an optimization pass when the user meant the startup time; "support teams" ships an entire RBAC system when the user wanted a shared workspace. The model's guess is often *plausible*, which makes the failure worse: the user discovers the misread only after the work is done. Compose clarifies the *code*; this skill clarifies the *ask* — and it comes before everything, including tier classification, because you can't classify a task you've misunderstood.

## The Rule

**Before classifying or composing, restate the ask in your own words with its acceptance criterion — and if any question could change the approach, ask it before building.** An assumption you didn't surface is a decision you made for the user without telling them.

## How to Apply

### 1. Restate the ask

One or two sentences: what you understand the user wants, and — critically — *what "done" looks like*. If you can't write the done-condition, the ask is ambiguous by definition.

### 2. Scan for the ambiguities that change the approach

Walk these five; note every hit:

- **Scope**: does "add X" mean minimal X or production X (auth? persistence? UI?)? What's explicitly NOT wanted?
- **Interpretation forks**: are there ≥2 readings where the work differs materially? ("export the data" — file download, API endpoint, or scheduled job?)
- **Context you're missing**: is there an existing convention, a previous attempt, a constraint (deadline, compatibility, no-new-dependencies) the user knows and didn't say?
- **The actual problem**: is the request a *solution* ("add a retry") to an unstated problem (flaky network? rate limit? bug?) where a different fix is better? Ask about the problem, not just the solution.
- **Stakes**: reversible experiment or production-bound? The answer changes the tier.

### 3. Decide: ask or assume

Not every ambiguity earns a question — batch judgment:

- **Ask** when the answer forks the approach, the work is expensive to redo, or the stakes are high. Ask ALL blocking questions at once (2–4, each with your default: "I'll assume X unless you say otherwise") — never one question per turn, dribbled.
- **Assume** when any reasonable reading lands in the same place, or the cost of guessing wrong is one small edit. State the assumption anyway — visibly, before the work: "Assuming you mean the CLI's startup time."

### 4. Record the contract

For Tier 2+ work, the restatement + answered questions + stated assumptions become the header of the compose artifact (or their own `.claude/plans/{task-name}-ask.md` when the elicitation was substantial). This is the contract verify checks against — "did I build what was asked" needs a written ask.

## Anti-Patterns (gaming behaviors)

- Asking zero questions ever ("bias for action") — and asking ten trivial ones (interrogation theater); both dodge the judgment in step 3
- Restating the ask by echoing the user's words verbatim — a restatement that can't be wrong is not a restatement
- Burying assumptions in the middle of a long plan where the user will never see them, then citing "I did mention it" after the misread ships
- Asking questions whose answers don't change what you'd build — signaling diligence, not reducing risk
- Writing the done-condition after the work is done, to match what got built
- Treating the user's silence on your stated assumption as confirmation for *later, bigger* bets it doesn't cover

## Verification

Done means evidence, not vibes:
- [ ] The restatement + done-condition exists in writing (reply for Tier 0/1; compose header or `-ask.md` artifact for Tier 2+) — written BEFORE implementation began
- [ ] Every assumption that survived to implementation is stated in it
- [ ] At completion, the work is checked against the done-condition — not against "what I built"

Verdict is PASS/FAIL; a done-condition that appeared after the code did is a FAIL.
