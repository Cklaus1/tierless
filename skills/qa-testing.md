---
name: qa-testing
description: QA-testing skill — designs a test plan from behavior (not code), covering happy path, edges, errors, and integration
metadata:
  type: user
---

# QA Testing — Test Design Skill

## Why

Smaller models write tests that mirror the implementation — they test that the code does what the code does, which is a tautology. Real QA starts from the *behavior contract*: what should this do, for whom, under what conditions? This skill forces test design from the spec side, so tests catch wrong implementations instead of enshrining them.

## The Rule

**Design the test plan from the requirements, before or without reading the implementation.** Then write the tests.

**When:** any Tier 2+ change adding or altering behavior — the test plan lands before deconstruct completes (per tierless-router lanes).

**Boundary with verify:** qa-testing designs the suite before/without reading the implementation; verify executes gates after it. Running verify does not satisfy this skill.

## How to Apply

A test suite must cover four layers, in this order of priority:

1. **Contract** — for each requirement, the observable behavior: given X, the user sees Y
2. **Edges** — boundaries of every input: empty, one, many, max, just-past-max, wrong type, unicode
3. **Errors** — every way the operation fails: what does the user see, is state left consistent, is it retryable?
4. **Integration** — the seams: does the feature work through the real entry point (route/CLI/UI), not just the unit?

Then:

1. Write the test plan to `.claude/plans/{task-name}-testplan.md` **before writing test code**:

```markdown
## Test Plan: {feature}

### Contract
- Given {state}, when {action}, then {observable result}
- ...one line per requirement, traced back to the spec/roadmap item

### Edges
- {input}: empty / single / many / at-limit / past-limit / malformed
- ...one line per input, per interesting boundary

### Errors
- {failure}: user sees {message}, state is {rolled back / consistent}, retry {works / is idempotent}

### Integration
- Through {real entry point}: {end-to-end scenario}

### Explicitly not tested
- {thing}: because {reason}
```

2. Implement the tests. Each test maps to one plan line; name it after the behavior (`rejects_expired_token`), not the method (`test_validate_2`).
3. Run the suite. Then **mutate to validate**: pick 2–3 core lines of the implementation, break each one deliberately, confirm a test fails. If nothing fails, the suite is decorative — fix it.

## Coverage Judgment

Do not chase a coverage percentage. Priority order:
1. Money, auth, and data-mutation paths — exhaustive
2. Public API contracts — every documented behavior
3. Error handling — every catch block earns its keep or gets deleted
4. Pure display/formatting — light touch

## Anti-Patterns

- Tests written by reading the implementation and asserting what it returns
- One giant happy-path test per feature ("it works")
- Mocking so much that the test only exercises the mocks
- Asserting on internal state instead of observable behavior — refactors shouldn't break tests
- Skipping the mutation check — a passing suite proves nothing until you've seen it fail
- "Explicitly not tested" section left empty (you always chose not to test something; say what)
