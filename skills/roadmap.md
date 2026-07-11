---
name: roadmap
description: Roadmap skill — structures product planning into MVP, v1, v2+ phases with explicit scope boundaries
metadata:
  type: user
---

# Roadmap — Product Planning Skill

## Why

Given "build X", smaller models implement features in encounter-order — whatever the prompt mentioned first — shipping nothing runnable. Without a scope boundary, the first version contains half of everything and all of nothing. A roadmap forces explicit scoping: what ships first, what waits, and why. This skill structures product planning into phased releases with clear boundaries and explicit exclusions.

## The Rule

**Every Tier 3 task (per tierless-router) gets a roadmap.** The roadmap contains:

1. **MVP** — the smallest thing that delivers value. Must be shippable in one iteration. Explicitly list what is NOT in the MVP.
2. **v1** — the first complete release. Builds on MVP with the features that make it production-ready.
3. **v2+** — nice-to-haves, optimizations, and stretch goals. Each item is independent and can be shipped or dropped without breaking v1.

## How to Apply

When starting a new project, feature, or major initiative:

1. Write the roadmap to `.claude/plans/{task-name}-roadmap.md`:

```markdown
## Roadmap: {project-name}

### MVP (this iteration)
**Goal:** {one sentence — what value does this deliver?}
**In scope:**
- {feature 1}
- {feature 2}
- {feature 3}

**Explicitly out of scope:**
- {what you're NOT building}
- {what is deferred to v1}

### v1 (next iteration)
**Goal:** {one sentence}
**Adds:**
- {feature that makes it production-ready}
- {feature that completes the core flow}

**Does NOT include:**
- {stretch goals that stay in v2}

### v2+ (future)
- {independent enhancement 1}
- {independent enhancement 2}
- {optimization or polish}

Each v2+ item must be independently shippable.
```

2. Present to user for approval before implementation begins.
3. Hand off execution to build-loop, which turns the phases into a persistent loop with entry/exit gates. Implement MVP first. Do not start v1 work until MVP is verified.
4. Use estimation to size the roadmap items (after each is deconstructed, never before).

## Scope Discipline

- **MVP must be shippable.** If it can't ship, it's too big. Cut it down.
- **v1 must be complete.** No "we'll add that later" in v1 scope.
- **v2+ must be independent.** Each item stands alone — no "this requires that other v2 item" dependencies.
- **Explicit exclusions are mandatory.** If you don't list what's out of scope, scope creep is inevitable.

## Anti-Patterns

- MVPs that include auth, settings, or other "we'll need this eventually" features
- Roadmaps where v1 items depend on v2+ items
- No explicit out-of-scope list
- v2+ items that are really just v1 features that got demoted
- Treating the roadmap as fixed — it should be a living document that changes as you learn

## Roadmap Checklist

Before handing off to build-loop, verify:
- [ ] MVP names the single command or flow that demonstrates it ships
- [ ] Every phase has an explicit out-of-scope list
- [ ] No v1 item depends on a v2 item
- [ ] Execution handed off to build-loop