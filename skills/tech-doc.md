---
name: tech-doc
description: Tech-doc skill — the discipline for writing design docs, RFCs, and technical specs that survive contact with reviewers and implementation
metadata:
  type: user
---

# Tech Doc — Technical Writing Skill

## Why

Smaller models write tech docs that are long, confident, and hollow: they describe the solution without stating the problem, list one option as if no alternatives existed, and bury the decision the reader needs to make. A great tech doc is not prose about code — it's a decision-making instrument.

**When:** Tier 2 work introducing a new interface, any Tier 3 work, or whenever a design doc/RFC is requested (per fable-discipline's Conditional Lanes).

**Where it goes:** shipped designs land in the repo's docs directory; internal working designs go to `.claude/plans/{task-name}-techdoc.md`.

## The Rule

**No design section is written until the problem statement stands alone and at least two real alternatives (including do-nothing) exist.**

## The Mental Disciplines

1. **Audience first.** Name who this doc is for and what decision or action you want from them. A doc for approvers leads with the recommendation; a doc for implementers leads with the contract. One doc, one primary audience.
2. **Problem before solution.** The problem statement must stand alone — a reader should agree the problem is real and worth solving *before* seeing your answer. If the problem section secretly describes your solution ("we lack a caching layer"), rewrite it as the user-visible pain ("p95 latency is 2.1s on the dashboard").
3. **Steelman the alternatives.** At least two real alternatives, each presented well enough that a smart person could pick it. Include "do nothing" — it has zero cost and zero risk, and your proposal must beat it. A doc with one option is a memo, not a design.
4. **Commit to numbers.** Vague claims rot: "fast" → "p95 < 200ms at 500 rps"; "soon" → a date; "scales" → the number it scales to and the number where it breaks. Every claim a reviewer could ask "how much?" about gets a number or an explicit "unknown, will measure by X".
5. **Say what you're NOT doing.** Non-goals are load-bearing. Every scoping fight during implementation traces back to a non-goal that wasn't written down.
6. **Surface the risks yourself.** List the ways this design fails and what you'll do about each. A reviewer finding a risk you didn't list costs credibility; a risk you listed with a mitigation builds it.
7. **Write to be skimmed.** The busy reader reads: title → summary → section headers → decision table. That path alone must carry the argument. Details live under headers for the reader who drills in.

## The Structure

```markdown
# {Title: the decision, not the topic — "Move session storage to Redis", not "Session storage"}

## Summary
{3-5 sentences: problem, recommendation, cost, main risk. Written LAST.}

## Problem
{The pain, with numbers. Who is affected, what it costs today, why now.}

## Goals / Non-goals
{Bulleted. Non-goals are as important as goals.}

## Proposed design
{The contract first: APIs, data shapes, invariants. Then the mechanism.
 Diagrams for anything with 3+ moving parts.}

## Alternatives considered
| Option | Cost | Risk | Why not |
{Including "do nothing". Honest rows — no strawmen.}

## Risks & mitigations
{Each risk: likelihood, blast radius, mitigation or accepted-because.}

## Rollout
{Phases, feature flags, migration, rollback plan, success metrics.}

## Open questions
{What you genuinely don't know. Empty = you haven't thought hard enough.}
```

## The Process

1. **Compose first** (same as code): read the existing systems the doc touches; a design doc written without reading the code it changes is fiction
2. Draft the problem + goals/non-goals; get a sanity check on those alone before designing (cheapest possible course-correction)
3. Write the design, alternatives, risks
4. Write the summary last
5. **Adversarial self-review — a gate, not a suggestion**: read it as the most skeptical senior engineer you know. Write the three questions they'd ask, and put both the questions and their answers in the doc verbatim (an "Anticipated objections" subsection or woven into Risks). The doc is not done until all three appear. For the deeper version of this attack, see adversarial-review.
6. Freshness gate: every number in the doc traceable (measured, quoted, or estimated-and-labeled)

## Anti-Patterns

- Solution masquerading as problem ("we need Kubernetes")
- Alternatives section written after the decision, as decoration
- "Should be fast enough" — no numbers, no commitment
- Ten pages before the reader learns what you're recommending
- No rollback section — every design that touches production data needs one
- Open questions section deleted instead of answered
