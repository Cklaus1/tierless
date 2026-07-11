---
name: deconstruct
description: Deconstruct skill for smaller models — breaks complex tasks into atomic, independently-verifiable steps to prevent over-scoping
metadata:
  type: user
---

# Deconstruct — Discipline Skill

## Why

Smaller models regularly over-scope tasks, producing large diffs that hide bugs and make review impossible. Decomposing problems into their smallest possible units before acting prevents this. This skill enforces that decomposition.

## The Rule

**Every non-trivial task must be decomposed before implementation begins.** A proper deconstruction:

1. **Identifies the boundary** — what is in scope vs out of scope. Explicitly list what you will NOT touch.
2. **Breaks into atomic steps** — each step must be:
   - Self-contained (can be understood in isolation)
   - Verifiable independently (has a pass/fail condition)
   - Reversible (can be undone without side effects)
   - Under 50 lines of changed code
3. **Orders by dependency** — each step lists what it depends on. No step should block another.
4. **Assigns a pass condition** — each step has a concrete way to verify it works (command, test, output format). The pass conditions here are exactly what verify executes.

## How to Apply

When to apply: every Tier 1+ task, per fable-discipline's tier classification:

1. Read the relevant source files first. Understand the existing patterns.
2. Write a deconstruction to `.claude/plans/{task-name}-deconstruct.md`:

```markdown
## Task: {name}
**Boundary:** In scope: {list}. Out of scope: {list}.

### Step 1: {title}
- **Changes:** {file:line} — {what}
- **Depends on:** nothing
- **Pass condition:** {exact verification}

### Step 2: {title}
- **Changes:** {file:line} — {what}
- **Depends on:** Step 1
- **Pass condition:** {exact verification}
```

3. Present to user for approval (Tier 2+; Tier 1 deconstructions may be lighter or inline, no approval gate required).
4. Implement one step at a time, verifying before moving to the next.

## When to Defer to Plan-Mode

If the deconstruction reveals a new architectural decision (choosing a pattern, designing a new interface), escalate to plan-mode first. Deconstruct is for implementing known designs; plan-mode is for creating the design.

## Dependency Ordering

Steps must be ordered so each one can be verified before the next begins. A correct ordering looks like:

```
Step 1: Add type definition (no deps)
Step 2: Implement function using type (depends on Step 1)
Step 3: Add caller that uses function (depends on Step 2)
Step 4: Add test for the caller (depends on Step 3)
```

An incorrect ordering would put Step 4 before Step 3 — you can't test something that doesn't exist yet.

## Anti-Patterns

- Steps that say "test the implementation" without specifying what to test
- Steps that modify more than 50 lines
- Steps that depend on something that hasn't been verified yet
- Deconstructions that don't list out-of-scope items (this is where scope creep happens)
- Steps that are "add tests" without specifying which functions/scenarios

## Deconstruction Checklist

Before implementation begins, verify:
- [ ] Boundary stated, with an explicit out-of-scope list
- [ ] Every step has a pass condition
- [ ] Every step changes fewer than 50 lines
- [ ] Dependency order verified — no step depends on an unverified later step