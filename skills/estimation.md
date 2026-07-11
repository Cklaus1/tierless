---
name: estimation
description: Estimation skill — reference-class sizing for tasks and roadmap items; ranges not points, risk surfaced not hidden
metadata:
  type: user
---

# Estimation — Honest Sizing Skill

## Why

Smaller models estimate the way optimistic engineers do: they imagine the happy path of the implementation and report that. The 2x-5x blowups come from what the happy path excludes — integration, unknowns discovered mid-task, review cycles, the environment fighting back. This skill replaces "how long does the plan feel like" with reference-class estimation: what did *similar work actually take*, and what specifically could make this one worse?

## The Rule

**Estimates are ranges with named risks, derived from the deconstruction — never a single number, never produced before the task is decomposed.** An estimate without a decomposition is a mood.

## How to Apply

### 1. Decompose first

Run deconstruct (or roadmap for project-scale). You estimate *steps*, not vibes. If the task can't be decomposed yet, the honest estimate is "unknown — needs a spike," and the spike gets a timebox instead.

### 2. Size each step against reference classes

For each step, ask: "when work of this shape was done before in this codebase, what did it take?" Shape matters more than size — "add a field through API+DB+UI" has a known cost; so does "touch the auth middleware" (always worse than it looks). Use the project's own history (`git log`, past build-loop exit records) as the reference library.

### 3. Apply the multipliers honestly

For each step, tag the conditions that historically blow up estimates, and widen the range accordingly:

- Touches code nobody understands (needs code-archaeology first)
- Crosses a team/service/API boundary (waiting + contract mismatch)
- First time doing this *shape* of work in this codebase (no reference class = widest range)
- Requires migration of live data (see data-migration — rehearsal time counts)
- "Just needs tests" (tests routinely cost ≈ the implementation)
- Depends on an external party's response time

### 4. Report as a range with the risk attached

Write the estimate to `.claude/plans/{task-name}-estimate.md`:

```markdown
## Estimate: {task}
**Range:** {best} – {likely} – {worst}
**The range is wide because:** {the 1–3 named risks}
**Shrinks to {narrower} if:** {the spike/answer that removes the biggest unknown}
**Explicitly excluded:** {deploy? review cycles? the v2 part?}
```

The "shrinks if" line is the most useful sentence in the estimate — it tells the reader what information is worth buying.

### 5. Close the loop

When the task finishes, record actual vs. estimated in the build-loop exit record, with one line on *why* it diverged. This is where the reference library comes from; without it, every estimate starts from zero.

## Anti-Patterns

- Point estimates ("3 days") — the point will be wrong; the range can be right
- Estimating the coding and silently excluding review, testing, integration, and deploy
- Padding everything 2x instead of naming the specific risks (hides information instead of surfacing it)
- Letting the desired answer shape the estimate (the deadline is input to *scoping*, not to *sizing*)
- Re-estimating downward mid-task to avoid reporting a slip — escalate the slip, keep the data honest
- Refusing to estimate at all ("it's done when it's done") — a timeboxed spike is always available

## Estimate Checklist

Before delivering the estimate, verify:
- [ ] Derived from a deconstruction (or timeboxed spike declared instead)
- [ ] Reported as a range (best – likely – worst), never a point
- [ ] 1–3 risks named, with a "shrinks if" line
- [ ] Exclusions stated explicitly
- [ ] Written to `.claude/plans/{task-name}-estimate.md`
