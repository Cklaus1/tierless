---
name: debugging
description: Debugging skill — hypothesis-driven root-cause hunting; bans shotgun fixes and "try this" loops
metadata:
  type: user
---

# Debugging — Root Cause Skill

## Why

Smaller models debug by pattern-matching the symptom to a plausible fix, applying it, and hoping. When it doesn't work they try the next plausible fix — mutating the code with every guess. Three guesses in, the codebase has three speculative changes and the bug is still there. This skill replaces guessing with the scientific loop: reproduce → hypothesize → test the hypothesis *without changing code* → fix once, at the root.

## The Rule

**No fix until the bug is reproduced and the root cause is demonstrated.** "Demonstrated" means you can predict the bug's behavior: when it fires, when it doesn't, and why.

Production actively broken? incident-response first — mitigate before diagnosing. This skill is the calm loop after.

The hypothesis log lives in `.claude/plans/{task-name}-debug.md` — hypotheses appended as tested; the final one-liner goes there too.

## The Loop

1. **Reproduce first.** A command or sequence that triggers the bug on demand. Can't reproduce → that IS the task now (add logging, capture state, bisect inputs). Never fix what you can't reproduce — you won't know you fixed it.
2. **State the hypothesis in writing** before touching anything:
   ```
   Hypothesis: {X causes Y because Z}
   Prediction: if true, then {observable thing} when {condition}
   Test: {read/log/breakpoint — NOT a code change}
   ```
3. **Test by observation, not mutation.** Read the code path, add a log line, inspect state at the boundary. The only code changes allowed during diagnosis are observability changes — and they get removed after.
4. **Bisect when lost.** No hypothesis? Halve the search space: git bisect across commits, binary-search the input, disable half the pipeline. Each halving is cheap; guessing is not.
5. **Fix the root, prove it, then re-run the reproduction** — and the surrounding tests. The reproduction becomes a regression test where feasible.
6. **Write the one-liner**: `Root cause: {Z}. Fix: {change}. Regression test: {test}`. If you can't fill in Z precisely, you patched a symptom. The fix is its own task — classify its tier via fable-discipline.

## Evidence Standards

- The stack trace's top frame is where it *died*, not where it *broke* — walk backwards to where the bad value was born
- "It works on my machine" = environment is part of the repro; diff the environments
- Timing-dependent bugs: never "fixed" by a sleep — that's the symptom-patch tell
- Two bugs can share a symptom; after fixing one, re-run the full reproduction, not just the failing step

## Anti-Patterns

- Changing code to "see if it helps" (mutation-as-diagnosis)
- Stacking speculative fixes — revert each disproven hypothesis's changes before testing the next
- Fixing where the exception surfaced instead of where the state went bad
- Declaring victory because the error message changed
- Closing without a regression test for anything that took more than 30 minutes to find
- "Cannot reproduce, closing" without capturing what evidence *would* be needed next time it fires
