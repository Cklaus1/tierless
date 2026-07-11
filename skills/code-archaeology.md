---
name: code-archaeology
description: Code-archaeology skill — understanding unfamiliar or legacy code before changing it; evidence over assumption
metadata:
  type: user
---

# Code Archaeology — Legacy Understanding Skill

## Why

Smaller models "understand" unfamiliar code by reading a few files and pattern-matching to codebases they've seen before. In legacy code that's fatal: the weird parts are weird for reasons — a workaround for a production incident, a contract with a system you can't see, a bug other code now depends on. This skill replaces assumption with excavation: gather evidence about why the code is the way it is before deciding what it should be.

## The Rule

**Before changing code you didn't write and don't fully understand, produce a dig report. Chesterton's Fence is the law: you may not remove or change anything until you can explain why it's there.**

## The Dig

Work these layers in order — each is cheap and constrains the next:

1. **Boundaries first.** Map inputs, outputs, and side effects of the target area before reading its internals: what calls it, what it calls, what it reads/writes (DB, files, network, globals). `grep` for callers; the call graph is evidence, the code comments are hearsay.
2. **History is data.** `git log --follow` on the target files. Look for: high-churn lines (bug magnets), commits titled "fix"/"hotfix"/"revert" (scar tissue), the commit that introduced the weird part and its message/PR. A one-line oddity with a linked incident ticket is load-bearing; treat it as such.
3. **Tests are the spec that runs.** What do the existing tests assert? What do they conspicuously *not* test? Untested behavior that callers depend on is the minefield — mark it.
4. **Find the invariants.** Every legacy system has unwritten rules ("this ID is always set by the time we get here", "these two tables are updated together"). Hunt them: assertions, defensive checks, ordering dependencies, comments containing "must", "always", "never", "DO NOT".
5. **Probe before believing.** For each assumption you're forced to make, test it cheaply: add a temporary log line, run the code with a crafted input, check production data for counterexamples. One probe beats an hour of confident reading.

## The Dig Report

Write `.claude/plans/{area}-dig.md`:

```markdown
## Dig: {area}
**Question:** {what change prompted this dig}

### Boundaries
- Called by: {list, with grep evidence}
- Calls / touches: {DB tables, APIs, files, globals}

### History highlights
- {file:line} — introduced in {commit}: {why, per the commit/PR}
- Scar tissue: {hotfixes, reverts, "temporary" code with a birthday}

### Invariants found
- {invariant} — enforced by {code/convention/nothing but luck}

### Fences I can now explain
- {weird thing}: exists because {evidenced reason}

### Fences I still can't explain
- {weird thing}: {what probe would explain it} — DO NOT TOUCH until probed

### Safe-change assessment
{what can change freely, what needs characterization tests first, what needs a human who was there}
```

## Anti-Patterns

- "This code is bad, I'll clean it up while I'm here" — the dig is for understanding, not judging; route changes through refactoring
- Trusting comments over call sites (comments describe the code that used to be there)
- Deleting dead-looking code without checking dynamic call sites (reflection, string-built routes, cron configs, feature flags)
- Assuming the tests describe intended behavior (they may enshrine a bug — check the history)
- Skipping the dig because the change "is only one line" — one line in code you don't fully understand is Tier 2 per fable-discipline
