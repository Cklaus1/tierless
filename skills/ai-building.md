---
name: ai-building
description: AI-building skill — discipline for LLM-powered features: evals before prompts, structure at the boundary, cost/latency budgets, and failure-mode design
metadata:
  type: user
---

# AI Building — LLM Feature Skill

## Why

Smaller models build AI features the way demos are built: write a prompt, eyeball three outputs, ship. The result works in the happy path and fails silently everywhere else — because LLM outputs are probabilistic, the failure modes are invisible until users hit them, and "it looked good when I tried it" is not evidence. This skill applies the discipline system to the one domain where verification is hardest: you can't unit-test a vibe.

## The Rule

**No prompt without an eval. The eval set exists before the prompt is tuned, and every prompt change re-runs it.** Tuning a prompt against your memory of what worked is shotgun debugging with extra steps.

## How to Apply

### 1. Define the contract first (same as api-design)

Before any prompt engineering, write down: input shape, output shape (schema, not prose), latency budget, cost budget per call, and what happens when the model fails. An LLM call is an API call to an unreliable dependency — design it like one.

### 2. Build the eval set before tuning

The eval set is a written artifact at `.claude/plans/evals/{feature}.md`, one row per case:

```markdown
| input | expected | grade-method | category |
|---|---|---|---|
| {the actual input} | {pass criterion} | exact / rubric / judge / schema | typical \| edge \| adversarial \| out-of-scope |
```

- 20+ real examples minimum: typical cases, edge cases, adversarial cases, and out-of-scope inputs the feature must *refuse*
- Each with a pass criterion — exact match for extraction, rubric for generation, "must/must-not contain" for safety
- Graded automatically where possible (schema validity, string checks); LLM-as-judge for the rest, with the judge prompt itself spot-checked against human grades
- Every prompt/model/parameter change re-runs the set. No eval regression ships, same as no test regression ships.

### 3. Structure at the boundary

- **Structured output always**: JSON schema / tool calls, never regex-parsing prose
- **Validate everything the model returns** — schema, enums, ID references against real data. The model *will* eventually return a plausible hallucinated ID; your code decides whether that's a retry or a corrupt record.
- Retry with feedback once on validation failure; then fall back (see 4). Unbounded retry loops on a broken prompt burn money.

### 4. Design the failure path as a feature

For each call decide *before shipping*: on validation failure / timeout / refusal, does the feature degrade (show partial), fall back (rules-based path), or surface honestly ("couldn't process this")? Silent failure is the worst outcome — it converts a model bug into user data corruption.

### 5. Engineering hygiene

- Prompts are code: versioned in the repo, reviewed in diffs, never edited live in a dashboard
- Log every call: prompt version, model, input hash, output, latency, cost. You cannot debug what you didn't log; you cannot improve what you didn't measure.
- Pin model versions; upgrading a model is a change that re-runs the evals, not a config tweak
- All user-facing input is untrusted: treat prompt injection as a given, keep instructions and data in separate message roles, and never let model output execute privileged actions without validation (see security-review)
- Start with the strongest model to prove the feature; downgrade to cheaper models only when evals show parity
- **Boundary**: this skill covers LLM calls that *answer*; the moment the call can act (tools, code execution, external writes), ai-safety applies on top

## Anti-Patterns

- Tuning the prompt on the same 3 examples until they pass (overfitting by hand)
- "The model usually gets it right" — quantify usually; 95% is 1-in-20 users hitting failure
- Parsing prose output with regex because "it's mostly consistent"
- Chaining 5 LLM calls where 1 call + code would do — every hop multiplies failure rate and latency
- Evals that only test the happy path (the adversarial and out-of-scope rows are the ones that matter)
- Shipping a model upgrade because the changelog sounded good, without re-running evals

## Verification

Done means evidence, not vibes:
- `.claude/plans/evals/{feature}.md` exists with all four categories populated
- Eval pass-rate reported **before and after** any prompt/model/parameter change — no ship below the baseline rate
- Verdict is PASS/FAIL against those numbers; "looked good on a few tries" is a FAIL
