---
name: build-loop
description: Build-loop skill — the phased delivery loop that strings all other skills together for multi-session project builds
metadata:
  type: user
---

# Build Loop — Phased Delivery Skill

## Why

Individual skills discipline individual tasks. But a project is many tasks over many sessions, and smaller models lose the thread between sessions: they forget what phase they're in, redo finished work, or start phase 3 while phase 1 is unverified. The build loop is the outer structure — a persistent, phased plan with hard entry and exit gates that survives across sessions.

## The Rule

**Every project runs as a loop over phases. A phase cannot begin until the previous phase has exited, and a phase cannot exit without passing its gate.**

## The Loop

```
roadmap → [for each phase: enter → build → verify → exit] → ship
```

Each iteration of the loop:
1. **Enter** — read `build-loop.md`, confirm the previous phase's exit was recorded, state this phase's goal
2. **Build** — run each task through fable-discipline (tier classification → compose/plan-mode/deconstruct/verify as the tier requires)
3. **Verify** — run the phase's exit criteria; loop-until-dry
4. **Exit** — record the exit in `build-loop.md`: what shipped, what was deferred, what surprised you

## How to Apply

At project start, after roadmap, write `.claude/plans/build-loop.md`:

```markdown
## Build Loop: {project}
**Current phase:** 1

### Phase 1: {name — usually the MVP walking skeleton}
**Goal:** {one sentence}
**Tasks:** {list, each will get its own tier classification}
**Exit criteria:**
- [ ] {demonstrable behavior — a command to run, a flow to walk}
- [ ] All tasks verified (verify skill), adversarial-review clean
**Exit record:** {filled at exit: date, deviations, deferrals, surprises, actual vs estimated — with one line on why it diverged}

### Phase 2: {name}
...
```

Session discipline:
- **Every session starts by reading `build-loop.md`** — it is the single source of truth for "where are we"
- **Every session ends by updating it** — even mid-phase: check off tasks, note partial state
- One phase in progress at a time. Found something phase-3-shaped while in phase 1? Write it into phase 3's task list and keep moving.

## Phase Design Rules

- Phase 1 is always a **walking skeleton**: the thinnest end-to-end slice that actually runs (UI stub → API → DB and back). Integration risk dies first.
- Each phase ends in a **demonstrable state** — something you can run and show, not "backend 80% done"
- 3–7 phases for most projects. More means phases are tasks; fewer means phases are projects.
- Exit criteria are executable or walkable — never "code is clean"

## Anti-Patterns

- Starting a session by looking at the code instead of the loop file ("I'll figure out where I was")
- Exit criteria written as effort ("finish the API") instead of evidence ("curl X returns Y")
- Letting a phase exit with 2 of 5 criteria checked "for momentum"
- Rewriting the whole loop file mid-project because plans changed — amend phases, keep the history and exit records
- Skipping the exit record — the surprises list is what makes the next phase's estimates honest

## Phase-Exit Checklist

Before a phase exits, verify:
- [ ] Every exit criterion executed or walked, not asserted
- [ ] All tasks in the phase verified; adversarial-review clean where the tier required it
- [ ] Exit record written: shipped, deferred, surprises, actual vs estimated with why it diverged
- [ ] `build-loop.md` updated with the next phase marked current
