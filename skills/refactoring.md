---
name: refactoring
description: Refactoring skill — behavior-preserving restructuring in small verified steps; bans the rewrite-disguised-as-cleanup
metadata:
  type: user
---

# Refactoring — Behavior-Preserving Change Skill

## Why

Smaller models treat "refactor" as "rewrite the way I would have written it" — and behavior quietly changes along the way. Real refactoring has one invariant: **observable behavior is identical before and after**. The discipline is a chain of tiny, individually-verified transformations, never a big-bang restructure.

## The Rule

**Tests green → one mechanical transformation → tests green → commit. Repeat.** If at any point you can't tell whether behavior changed, you've taken too big a step — revert to the last green commit.

Boundary: framework/language/whole-subsystem restructure → code-migration.

Artifact: `.claude/plans/{task-name}-refactor.md` holds the target-shape paragraph and the bugs-found-but-not-fixed list.

## How to Apply

1. **Pin behavior first.** Run the existing tests. If coverage over the target code is thin, write characterization tests *before* touching anything — tests that assert what the code currently does (including its bugs). You cannot preserve behavior you haven't captured.
2. **Declare the target shape** in one paragraph: what structure you're moving toward and *why it pays* (what upcoming change it enables, what duplication it kills). "Cleaner" is not a why.
3. **Chain small named transformations.** Each step is one of the mechanical moves — extract function, inline variable, rename, move, replace-conditional-with-polymorphism, etc. One move per commit. Every commit is green.
4. **Bugs found mid-refactor go on a list, not in the diff.** Fixing a bug changes behavior — that's a separate commit (usually *before* the refactor, with its own test). Mixing them makes both unreviewable.
5. **Finish or revert.** A refactor abandoned halfway leaves the code worse than either endpoint. If you run out of budget, revert to the last coherent green state.

## Separation Discipline

Never in the same commit:
- Refactoring + behavior change
- Refactoring + dependency upgrade
- Refactoring + formatting sweep (do the format-only commit separately; keeps diffs reviewable)

The reviewer's test: a refactor-only diff should be verifiable by structure alone — "same inputs, same outputs, better shape."

## Evidence Gate (before declaring done)

- [ ] Every commit is one named move
- [ ] Suite green at every commit
- [ ] No behavior/dependency/format change mixed in
- [ ] Bug list filed separately (in the refactor artifact, not the diff)

## When NOT to Refactor

- Code you're about to delete or replace
- Code with no tests and no time to write characterization tests (schedule it; don't wing it)
- The day before a release
- Someone else's in-flight code (merge conflicts guaranteed)
- "While I'm here" during an unrelated bugfix — note it, finish the fix, refactor separately

## Anti-Patterns

- The rewrite wearing a refactor costume ("I refactored the module" = 800-line diff, new behavior)
- Refactoring toward abstract flexibility no upcoming change needs (speculative generality)
- Renaming + restructuring + logic change in one commit — unreviewable and unbisectable
- Skipping characterization tests because "the code is obviously simple"
- Improving the code's style while degrading its performance without measuring
