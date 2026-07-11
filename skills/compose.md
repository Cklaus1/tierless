---
name: compose
description: Compose skill for smaller models — forces composition of understanding before implementation, preventing premature coding
metadata:
  type: user
---

# Compose — Discipline Skill

## Why

Smaller models' most common failure mode is jumping to implementation without fully understanding the problem space. They read one file and start coding, missing dependencies, edge cases, and existing patterns. The `compose` step forces synthesis of all available information before acting. This skill enforces that synthesis.

## The Rule

**Before implementing anything, compose a structured understanding.** The composition must contain:

1. **Problem statement** — one sentence. Not "fix the bug" but "X fails when Y because Z."
2. **Existing architecture** — which files interact, what data flows where. Reference specific files and line numbers.
3. **Constraints** — what CANNOT change (API contracts, data formats, external dependencies).
4. **Known variables** — what you know for certain vs what you're assuming. Mark assumptions explicitly.
5. **Failure modes** — what could go wrong, specific to this codebase. Not generic "network error" — specific to the patterns in this project.
6. **Proposed approach** — one paragraph, referencing the architecture and constraints above.

## How to Apply

When to apply: Tier 2+ tasks, per tierless-router's tier classification. When it applies, run it before any plan or deconstruction:

1. Read all relevant files. Don't guess at file locations — search for imports, grep for function names.
2. Write the composition to `.claude/plans/{task-name}-compose.md`:

```markdown
## Problem: {one sentence}

## Architecture:
- {file}: {role} (lines X-Y)
- {file}: {role} (lines X-Y)
- Data flow: {how data moves between components}

## Constraints:
- {cannot change}
- {external dependency}

## Knowns:
- {facts}

## Assumptions:
- {things to verify}

## Failure modes:
- {specific to this codebase}
  - Risk: likelihood {low/med/high} × impact {low/med/high} — mitigation: {what prevents or detects it}
- {failure mode 2}
  - Risk: likelihood {low/med/high} × impact {low/med/high} — mitigation: {...}

## Approach:
{one paragraph}
```

3. Review the composition. If you can't fill in a section, that's a gap — go read more files.
4. Only after composition is complete, proceed to plan-mode or deconstruct.

## The Composition Checklist

Before moving to implementation, verify:
- [ ] Every file that will be modified has been read and understood
- [ ] Every file that will be read (but not modified) has been identified
- [ ] Data flow is mapped — where does input come from, where does output go
- [ ] At least 2 failure modes are identified
- [ ] No assumptions are left unmarked
- [ ] The approach references specific files and line numbers, not vague descriptions
- [ ] Risk assessment included: likelihood × impact for each failure mode

## Risk Assessment

For each failure mode, estimate:
- **Likelihood** (low / medium / high) — how probable is this in practice?
- **Impact** (low / medium / high) — what breaks if this happens?
- **Mitigation** — what prevents it, or how do we detect it?

This turns vague "what if" into actionable tradeoffs.

## Anti-Patterns

- Compositions that are just a restatement of the user's request
- Compositions with empty sections (that means you didn't read enough)
- Skipping composition because "it's a small change" — small changes have the least margin for error
- Compositions that don't reference specific line numbers (means you didn't actually read the code)
- Using composition as a formality rather than a genuine understanding check
- Describing data flow as "it goes from A to B" without specifying the mechanism (HTTP, DB, event, shared state)

## Relationship to Other Skills

Compose is the first step of the Tier 2 pipeline; the full pipeline and tier definitions live in tierless-router.