---
name: verify
description: Verify skill for smaller models — enforces adversarial self-review before marking any task complete
metadata:
  type: user
---

# Verify — Discipline Skill

## Why

Smaller models routinely mark tasks as complete without actually verifying the result. They write code, run a single happy-path test, and declare success. The verify step is adversarial — it actively tries to break its own work. This skill enforces that adversarial self-review.

## The Rule

**Before marking any task complete, run a structured verification.** The verification must:

1. **Re-read the plan/deconstruction** — compare what was implemented against what was planned. Note every deviation.
2. **Run the pass conditions** — execute each pass condition from the deconstruction. Not "test it" — run the exact commands specified.
3. **Self-attack (3 vectors)** — read the diff and ask: "If I wanted to break this, how would I?" List 3 specific attack vectors:
   - Input that would cause an error
   - State that would cause unexpected behavior
   - Edge case that was overlooked
4. **Fix or document** — for each attack vector, either fix it or document why it's not a real risk.

## How to Apply

When to apply: every Tier 1+ task, per fable-discipline's tier classification. After implementation is complete, before marking the task done:

1. Read the plan or deconstruction file.
2. Run `git diff` and compare against the plan. Note deviations.
3. Run the exact pass conditions from the deconstruction.
4. Write a brief verification report to `.claude/plans/{task-name}-verify.md`:

```markdown
## Verification: {task-name}

### Plan compliance:
- [ ] Step 1: {pass/fail} — {notes}
- [ ] Step 2: {pass/fail} — {notes}

### Self-attack (3 vectors):
1. {Attack vector 1} — {mitigated / not-a-risk because...}
2. {Attack vector 2} — {mitigated / not-a-risk because...}
3. {Attack vector 3} — {mitigated / not-a-risk because...}

### Deviations from plan:
- {list any changes from the original plan}

### Result: {PASS / FAIL with notes}
```

5. Only mark the task complete if verification passes.

## The Verification Checklist

- [ ] Diff reviewed line-by-line against the plan
- [ ] All pass conditions executed successfully
- [ ] At least 3 adversarial attack vectors considered
- [ ] All deviations from plan documented
- [ ] Verification report written
- [ ] Regression check: existing tests still pass, existing behavior unchanged

## Loop-Until-Dry

For Tier 2+, verification is not one pass. After fixing anything the checklist or self-attack found, re-run this whole skill on the fixes. Repeat until a full pass finds **zero new issues** — only then is the task complete. Anything touching auth, payments, or data migration requires two consecutive clean passes (per fable-discipline).

## Regression Check

After verifying the new changes, run the full existing test suite. Verify that:
- No previously passing test now fails
- No previously working integration is broken
- Existing API contracts are still satisfied (if applicable)
- No behavioral regression in related features

## Anti-Patterns

- Running only the happy path
- Verification reports that say "no issues found" without listing attack vectors
- Skipping verification because "the tests pass" — unit tests don't catch integration bugs
- Verification that doesn't reference specific lines in the diff
- Marking tasks complete before writing the verification report

## Relationship to Other Skills

Verify answers "did I build what I planned?" — it executes the pass conditions from deconstruct plus the self-attack (3 vectors). It is not the final gate for Tier 2: the independent 6-vector adversarial-review still follows for Tier 2 — see fable-discipline's Which Review? table. The full pipeline lives in fable-discipline.