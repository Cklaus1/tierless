---
name: plan-mode
description: Plan-mode skill for smaller models — forces structured planning before implementation
metadata:
  type: user
---

# Plan Mode — Discipline Skill

## Why

Smaller models tend to jump straight into code: the observable behavior is writing code in the first tool call of a task, then discovering missing files or contradicting constraints mid-edit. The result is fragile implementations with hidden edge cases. This skill forces the missing step — design decisions committed to a file before any code is written.

## The Rule

**Before writing ANY code, produce a plan file.** The plan must contain:

1. **Scope** — what changes, what stays untouched. One sentence each.
2. **File list** — every file that will be created, modified, or read. With line numbers for existing code that informs the change.
3. **Implementation steps** — numbered, sequential, each one small enough to verify independently. No step should be "implement the feature."
4. **Edge cases** — list at least 3 failure modes specific to this change. Not generic "what if X fails" — specific to the codebase.
5. **Verification** — exact commands or test patterns that prove correctness. Not "test it" — specific test inputs and expected outputs.
6. **Rollback** — per step, how to undo it if it fails:

```markdown
## Rollback:
- If step N fails: revert {file} at {commit/line}, re-run {command}
- If integration fails: {specific rollback procedure}
```

## How to Apply

When to apply: Tier 2+ tasks, per fable-discipline's tier classification. For Tier 2, compose precedes this skill — the plan builds on the composition's understanding.

1. Explore the codebase thoroughly first. Read the relevant existing files.
2. Write the plan to `.claude/plans/{task-name}-plan.md` in the project.
3. Present the plan to the user for approval.
4. Only after approval, implement step by step, checking off each item.

## Anti-Patterns to Avoid

- Plans that say "implement X" without specifying the exact function signatures
- Plans that don't list the files they'll read (not just write)
- Plans with fewer than 3 edge cases
- Plans where any single step would change more than 50 lines of code
- Skipping the plan entirely because "it's simple" — if you're tempted to skip, it's not simple
- Plans without a rollback strategy — if step 3 breaks, how do you undo it?

## Connection to Deconstruct

Plan-mode and deconstruct are separate Tier 2 artifacts with a clear boundary: plan-mode captures the **design decisions** — what approach, which files, what edge cases. Deconstruct then produces the **atomic step breakdown with pass conditions**. The plan informs the deconstruction; it does not replace it.

## Plan-Completeness Checklist

Before presenting the plan for approval, verify:
- [ ] All 6 rule items present (scope, file list, steps, edge cases, verification, rollback)
- [ ] Every implementation step changes fewer than 50 lines
- [ ] Every step has a rollback path