---
name: version-control
description: Version-control skill — atomic commits, messages that carry the why, branch hygiene, and history as a debugging tool you're building for future-you
metadata:
  type: user
---

# Version Control — History Craft Skill

## Why

Smaller models treat git as a save button: one commit per work session titled "fix", "updates", or "address feedback", mixing a bugfix, a rename, and a drive-by format sweep into one unbisectable blob. The cost lands later — `git bisect` can't isolate the regression, `git log` can't answer "why is this line here" (code-archaeology's raw material), and the reviewer gets one 900-line diff instead of five reviewable steps. History is not a byproduct; it's a debugging and comprehension tool you are either building or destroying with every commit.

## The Rule

**One logical change per commit, with a message that says why — and every commit leaves the tree in a working state.** If you can't title the commit without "and", it's two commits.

## How to Apply

### 1. Atomic commits

- One commit = one deconstruct step is the natural mapping — the pass condition ran green, commit
- Separation law (same as refactoring/dependency-management): behavior change, refactor, format sweep, and dependency bump are four different commits, always
- Every commit compiles and passes tests — a broken intermediate commit poisons bisect. Verify before committing, not after.
- Stage deliberately: `git add -p` or per-file, then read `git status` and the staged diff before committing — the accidental `.env`, debug print, or unrelated file gets caught here or ships

### 2. Messages that carry the why

```
component: imperative summary under ~70 chars

Why this change (the problem, not the code — the diff shows the code).
What a non-obvious reader needs: the constraint honored, the alternative
rejected, the issue/ADR link.
```

- The summary line completes "if applied, this commit will ___"
- The body is where "why is this line here" gets answered two years from now — a commit whose message restates its diff ("change X to Y") has zero information the diff didn't
- Reference the artifact trail where it exists: the plan, the ADR, the incident

### 3. Branch hygiene

- Branch per task, named for the task (`fix-session-expiry`, not `dev2`), cut from a fresh default branch
- Sync by rebasing your unshared work or merging main in — never rewrite history others have pulled (force-push is for your own unshared branches only)
- Branches are short-lived: the longer a branch lives, the bigger the merge and the staler the review — a branch older than the build-loop phase that spawned it is a smell
- The PR is the branch's whole story: stacked small PRs over one omnibus (see human-code-review's 30-minute rule)

### 4. History as evidence

- Commit *during* the work, at each green step — not one archaeology-destroying squash at the end of the day
- Before any history-touching operation (rebase, reset, amend), know your escape hatch: `git reflog` exists, but the discipline is `git status` + stash before anything destructive
- WIP commits are fine on your branch; clean them up (interactive rebase / squash to logical units) before review — the reviewer and bisect see the curated history, not the diary

## Anti-Patterns (gaming behaviors)

- Committing "atomic" units that are atomic by file count, not by logic — the rename in one commit, its call-site updates in the next (both broken alone)
- Writing the why-message by paraphrasing the diff ("updated the handler") — technically a body, zero information
- Squashing an entire feature to one commit *after* review to "clean up" — destroying the very steps the reviewer approved
- `git commit -am` reflexes: staging everything blind, then describing what you hope is in there
- A working-state "guarantee" checked by memory ("it compiled a minute ago") instead of running the check on what's actually staged
- Branch named for the ticket number only — `JIRA-4821` forces every reader through another system to learn what the branch does

## Verification

Done means evidence, not vibes — before the branch goes to review:
- [ ] `git log --oneline main..HEAD` reads as a plan: each line one logical change, no "and", no "fix"/"wip" survivors
- [ ] Each commit's staged diff matched its message when committed (spot-check: `git show` on two commits — does the message explain the why the diff can't?)
- [ ] Tree state verified green at each commit that will be bisect-visible (`git rebase -x 'test-command'` where feasible)
- [ ] `git status` clean — nothing intended is unstaged, nothing accidental is committed

Verdict is PASS/FAIL; a log full of "fix" is a FAIL even if the code is perfect.
