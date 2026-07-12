# Evaluation Design: "Skills Close the Cheap-to-Frontier Gap"

## 1. The Claim

Adding a set of process-discipline "skills" to a cheaper LLM makes it produce work closer to a frontier model on coding tasks.

This claim has two sub-claims:
- **C1 (skill efficacy):** Cheap model + skill > cheap model bare, on the same task.
- **C2 (gap closure):** Cheap model + skill approaches frontier model bare, on the same task.

The evaluation must test both sub-claims, and must also test whether the effect generalizes across tasks and models.

---

## 2. Methodological Decisions

### 2.1 What "closer to frontier" means — scoring

**Decision: Use deterministic keyword-checklist scoring as the primary metric, with human spot-checks as a secondary validation layer. Never trust an LLM grader for the final numbers.**

Rationale (learned from LESSONS #12, re-learned in the spec-review cycle):
- An LLM grader hallucinated scores in the spec-review eval — it credited bare-Haiku with findings (mobile/read-state/thundering-herd) that the review text never contained. Its per-flaw claims failed grep verification against the actual source text.
- Keyword scoring is slightly generous (a hit isn't always substantive), but it applies IDENTICALLY to all arms, so comparisons are fair. Generosity is a known, bounded bias.
- LLM-judge scoring is an unknown, unbounded bias — it can inflate, hallucinate, or systematically favor one arm over another.

**Implementation:**
- Each task has a checklist of findings (e.g., the 15-flaw checklist for spec-review, the 12-item checklist for code-archaeology).
- Each checklist item has a deterministic grep pattern (regex) that matches substantive discussion of that finding.
- Score = number of checklist items matched, out of total.
- Patterns are written BEFORE the eval runs, based on the frontier model's output (what the frontier actually said, not what we wish it said).
- A human spot-checks 20-30% of scored items by reading the source text to confirm the keyword hit is substantive (not a false positive from a tangential mention).

**Anti-pattern guarded against:** "The model usually gets it right" — quantified usually; 95% is 1-in-20 users hitting failure. Keyword scoring gives exact counts, not vibes.

### 2.2 Task selection

**Decision: Test on a diverse set of tasks, not a single cherry-picked one. Include both "derive-the-non-obvious" tasks (where skills showed a real gap) and "standard checklist" tasks (where skills showed no gap).**

Rationale (from ENUMERATION-CYCLES.md):
- Skills help where items to enumerate are NON-OBVIOUS and must be DERIVED (spec-review, code-archaeology, build-loop).
- Skills do NOT help where items are a STANDARD CHECKLIST the model already has memorized (debugging, api-design, security-review, adversarial-review, qa-testing, threat-modeling, ui-design).
- Testing only on tasks where the skill works would be cherry-picking and would overstate the claim.
- Testing only on tasks where the skill doesn't work would be cherry-picking in the other direction.

**Task set (from the project's existing evals):**
- **Real-gap tasks (3):** spec-review, code-archaeology, build-loop
- **Ceiling tasks (3):** debugging, adversarial-review, qa-testing
- **Total: 6 tasks**

This gives a balanced view: the skill's value is concentrated in the derive-the-non-obvious domain. The eval should show that pattern, not a uniform lift.

### 2.3 Model arms

**Decision: Three arms per task — Haiku bare, Haiku + skill, Fable bare. Optionally add Sonnet as a fourth arm for cross-family generalization.**

Rationale (from SONNET-ARM.md):
- Haiku is the "cheap model" arm. It has demonstrated measurable gaps on the derive-the-non-obvious tasks.
- Fable is the "frontier bar." It is the project's true target, not Opus (which was a proxy).
- Sonnet was tested and found to be near-ceiling on the validated-skill tasks — it had almost no gap to close. This is an important finding: the skill's value depends on WHICH cheap model you run.
- The eval should include Sonnet to validate this finding, but the primary comparison is Haiku.

**Arms:**
- **A1: Haiku bare** — the cheap model, no skill
- **A2: Haiku + skill** — the cheap model, with the distilled skill for that task
- **A3: Fable bare** — the frontier reference bar
- **A4: Sonnet bare** (optional) — cross-family check

### 2.4 Multiple runs — variance control

**Decision: Run each arm 3 times per task. Report mean and spread.**

Rationale:
- LLM outputs are probabilistic. A single run can lie due to sampling variance.
- 3 runs is the minimum for detecting a real effect. With N=3, you can compute mean and standard deviation, and see if the confidence intervals overlap.
- N=3 is also practical: each run produces a file on disk, and scoring is deterministic (grep), so the cost is mostly time, not money.

**Reporting:**
- Report mean score and standard deviation per arm per task.
- A skill's effect is real if the mean difference exceeds 2x the pooled standard deviation (roughly: the gap is larger than the noise).
- If the spread is large (high variance), the skill's effect may be inconsistent — which is itself a finding.

### 2.5 Blind grading

**Decision: The grader (grep patterns + human spot-checks) must not know which arm it is scoring.**

Rationale (from checklist item #6):
- Even deterministic scorers can be biased if they know which arm is which. A human reading the text to spot-check will bring priors.
- Blind grading is easy here: rename the files (arm-A, arm-B, arm-C) before scoring. The human spot-checker sees "arm-A" and "arm-B" without knowing which is bare and which is +skill.

**Implementation:**
- After all runs complete, rename files: `attempt-haiku.md` -> `arm-A.md`, `attempt-haiku-skill.md` -> `arm-B.md`, `attempt-fable.md` -> `arm-C.md`.
- The human spot-checker scores a random 20-30% sample without knowing which arm is which.
- The grep scoring is inherently blind (it doesn't read filenames, only content).

### 2.6 Headroom / ceiling check

**Decision: Before running the eval, verify that the bare model does NOT already ace the task. If bare Haiku scores >= 90% of Fable, the task proves nothing.**

Rationale (from checklist item #4):
- The enumeration-skill analysis showed that many tasks (debugging, api-design, security-review, adversarial-review, qa-testing, threat-modeling, ui-design) are at ceiling — Haiku already scores the same as Fable.
- Running the eval on a ceiling task would show no skill effect, but that doesn't mean the skill is useless — it means the task is the wrong one for this model.
- The eval must explicitly flag ceiling tasks and exclude them from the "skill efficacy" claim.

**Implementation:**
- Before the eval, run a quick baseline: score Haiku bare and Fable bare on each task.
- If Haiku bare >= 0.9 * Fable bare, flag the task as "ceiling" and exclude it from the primary analysis.
- The ceiling finding is itself a result: it tells you which tasks the cheap model already handles well.

### 2.7 Pre-registered success criterion

**Decision: Define what "supported" means BEFORE seeing results.**

Rationale (from checklist item #12):
- If you decide what counts as "the claim is supported" after seeing the numbers, you can always find a definition that works.
- Pre-registering the criterion forces honesty.

**Pre-registered criteria:**
- **C1 supported (skill efficacy):** Haiku + skill mean score > Haiku bare mean score by >= 1 point on at least 2 of the 3 real-gap tasks, AND the difference exceeds 2x the pooled standard deviation.
- **C2 supported (gap closure):** Haiku + skill mean score >= 0.8 * Fable bare mean score on at least 2 of the 3 real-gap tasks.
- **C1 NOT supported:** Haiku + skill mean score <= Haiku bare mean score on any real-gap task, or the difference is within noise (<= 2x pooled std dev).
- **C2 NOT supported:** Haiku + skill mean score < 0.7 * Fable bare mean score on any real-gap task.

### 2.8 Contamination / fixture guarding

**Decision: The task fixture (the code/spec/design being reviewed) must be read-only and identical across all arms. The answer key (checklist items) must not be shown to the model generating the output.**

Rationale (from checklist item #9):
- If the model sees the checklist items while generating its output, it's not testing the skill — it's testing whether the model can regurgitate the answer key.
- If the fixture differs between arms (even slightly), the comparison is confounded.

**Implementation:**
- The fixture file (e.g., `spec.md`, `expenses.py`) is read-only and placed in a fixed location.
- The model prompt does NOT include the checklist. The checklist is only used for scoring AFTER the model produces its output.
- The skill itself is the only difference between bare and +skill arms. The skill describes a PROCESS, not a list of answers.

### 2.9 Knowledge vs. Process — mechanism

**Decision: When the skill works, verify that it worked BY INSTALLING A PROCESS, not by providing answers.**

Rationale (from checklist item #10):
- A skill that just lists answers is a cheat sheet, not a discipline. It might work on the training task but won't generalize.
- The gap-diff method derives skills from PROCESS deltas (what the frontier model DID, not what it KNEW).
- The eval should verify that the skilled output shows evidence of running the process, not just listing the answers.

**Implementation:**
- After scoring, read the skilled output and check: does it show the process being applied? (e.g., for spec-review, does it run the five audits? For code-archaeology, does it trace the constant through all expressions?)
- This is a binary check: process-evidence present or absent. It's a secondary metric, not the primary score.
- If the score goes up but process-evidence is absent, the skill may be working by accident (e.g., the prompt happened to mention the right keywords).

### 2.10 Per-model generalization

**Decision: Run the eval on at least two cheap models (Haiku and Sonnet) to test whether the skill effect transfers.**

Rationale (from checklist item #11, and from SONNET-ARM.md):
- A result on one model may not transfer. The Sonnet test showed that the skill was nearly inert on Sonnet because Sonnet was already near-ceiling bare.
- The skill's value is model-specific. A skill derived from a Haiku-vs-Fable gap is validated FOR HAIKU. It may be inert on Sonnet.
- This is not a failure of the skill — it's a finding about the product claim. The claim must be tightened: "skills close the SPECIFIC blind spots of the SPECIFIC model you run."

**Implementation:**
- Include Sonnet as a fourth arm on the 3 real-gap tasks.
- Report: does the skill move Sonnet? (Expected: minimal, because Sonnet is near-ceiling.)
- This validates the hypothesis that the skill's value is model-specific, not universal.

---

## 3. Pitfalls and Guardrails

### P1: LLM-judge bias (CRITICAL)

**Pitfall:** Using an LLM to grade the outputs. The LLM grader hallucinated scores in the spec-review eval — it credited bare-Haiku with findings it never mentioned.

**Guard:** Deterministic keyword scoring only. LLM judge may be used for exploratory analysis, but never for the final verdict.

### P2: Ceiling effect (HIGH)

**Pitfall:** Testing on tasks where the cheap model already scores near the frontier. The skill shows no effect, but that's because the task is too easy, not because the skill is useless.

**Guard:** Pre-register ceiling threshold (0.9 * Fable score). Flag and exclude ceiling tasks from the primary analysis. Report them separately.

### P3: Single-run variance (MEDIUM)

**Pitfall:** Running each arm once. A single run can lie due to sampling variance. The skill might appear to work (or not work) by chance.

**Guard:** Run each arm 3 times. Report mean and spread. Require the effect to exceed 2x pooled std dev.

### P4: Grader bias (MEDIUM)

**Pitfall:** The human spot-checker knows which arm is which and brings priors. Even with deterministic grep scoring, the human layer can be biased.

**Guard:** Blind grading. Rename arms before human spot-check. Grep scoring is inherently blind.

### P5: Contamination (MEDIUM)

**Pitfall:** The model sees the answer key (checklist items) while generating its output. The skill is tested against the wrong thing.

**Guard:** Fixture is read-only. Checklist is only used for scoring, never shown to the model. The skill describes a process, not answers.

### P6: Cherry-picked tasks (MEDIUM)

**Pitfall:** Testing only on tasks where the skill works. The claim appears stronger than it is.

**Guard:** Include both real-gap and ceiling tasks. Report the pattern: skills help on derive-the-non-obvious tasks, not on standard-checklist tasks.

### P7: Overclaiming generalization (LOW)

**Pitfall:** Claiming "skills close the gap" universally, when the effect is model-specific.

**Guard:** Tighten the product claim: "skills close the SPECIFIC blind spots of the SPECIFIC model you run." The method (gap-diff + deterministic scoring) is the durable asset.

### P8: Keyword false positives (LOW)

**Pitfall:** A keyword hit doesn't always mean substantive discussion. The model might mention the keyword in passing, not as a genuine finding.

**Guard:** Human spot-checks 20-30% of scored items. If the false-positive rate is high, tighten the grep patterns.

### P9: Prompt leakage (LOW)

**Pitfall:** The skill prompt itself contains hints that lead to the right answers, rather than installing a genuine process. The skill works by accident.

**Guard:** After scoring, verify process-evidence in the skilled output. If the score goes up but no process is visible, the skill may be working by keyword coincidence.

### P10: Model upgrade confound (LOW)

**Pitfall:** If the model version changes between runs (e.g., Haiku-4.5 vs. a later Haiku), the comparison is confounded.

**Guard:** Pin model versions. Document the exact model string used for each run. Upgrading a model is a change that re-runs the evals.

---

## 4. Execution Plan

### Phase 1: Fixture and checklist preparation (before any model runs)

1. For each of the 6 tasks, identify the fixture file (the code/spec/design to be reviewed).
2. For each task, write the deterministic grep patterns based on the frontier model's output. Each pattern should match substantive discussion of a specific finding.
3. Pre-register the success criterion (Section 2.7).
4. Pre-register the ceiling threshold (0.9 * Fable score).

### Phase 2: Model runs

For each of the 6 tasks, run 4 arms x 3 runs = 12 model invocations:
- Haiku bare (3 runs)
- Haiku + skill (3 runs)
- Fable bare (3 runs)
- Sonnet bare (3 runs, optional)

Each run produces a file on disk. Files are named deterministically: `attempt-{model}.md` or `attempt-{model}-skill.md`.

### Phase 3: Scoring

1. Run the grep patterns against each file. Count hits.
2. Compute mean and std dev per arm per task.
3. Flag ceiling tasks (Haiku bare >= 0.9 * Fable bare).
4. Blind the files (rename to arm-A, arm-B, arm-C).
5. Human spot-check 20-30% of scored items.

### Phase 4: Analysis

1. Report results in a table: task x arm x score.
2. Evaluate C1 (skill efficacy): does Haiku + skill > Haiku bare?
3. Evaluate C2 (gap closure): does Haiku + skill approach Fable bare?
4. Report ceiling tasks separately.
5. Report Sonnet results: does the skill transfer?
6. Report process-evidence: did the skilled output show the process being applied?

### Phase 5: Verdict

- PASS: C1 and C2 both supported on >= 2 of 3 real-gap tasks.
- FAIL: C1 or C2 not supported on any real-gap task.
- INCONCLUSIVE: Results are mixed (supported on 1 of 3 real-gap tasks) or variance is too high to draw conclusions.

---

## 5. What This Eval Does NOT Test

- **Weaker models than Haiku:** The eval tests Haiku (4.5) and Sonnet, which are both relatively strong cheap models. The models where skills would plausibly show the LARGEST gap are small local models (Qwen-7B-class, Llama-8B). Those are not in this gateway. Until tested there, "skills close the cheap-to-frontier gap" is demonstrated only for the narrow band of already-strong cheap models.
- **Cost/latency trade-offs:** The eval measures quality, not cost. A skill that improves quality but doubles latency or cost may not be worth it. That's a separate eval.
- **Long-term retention:** The eval measures one-shot performance. Does the skill's effect persist across sessions? Does the model internalize the process? That's a separate question.
- **Skill quality itself:** The eval assumes the skills are given. It does not test whether the gap-diff method produces good skills. That's a separate eval (and was the subject of the spec-review cycle, which showed the method works).

---

## 6. Summary of Methodological Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scoring method | Deterministic keyword grep + human spot-check | LLM judge hallucinated scores (LESSONS #12) |
| Task set | 6 tasks: 3 real-gap + 3 ceiling | Avoid cherry-picking; test the full pattern |
| Model arms | Haiku bare, Haiku+skill, Fable bare, Sonnet bare | Test efficacy + gap closure + cross-family |
| Runs per arm | 3 | Control for sampling variance |
| Blind grading | Yes (rename arms before human spot-check) | Prevent grader bias |
| Ceiling check | Pre-register 0.9 * Fable threshold | Flag tasks where the skill has nothing to do |
| Pre-registered criteria | C1: +1 point on >= 2 of 3 real-gap tasks; C2: >= 0.8 * Fable on >= 2 of 3 | Decide before seeing results |
| Contamination guard | Fixture read-only; checklist hidden from model | Test the skill, not the answer key |
| Mechanism check | Verify process-evidence in skilled output | Ensure the skill works by process, not keyword coincidence |
| Generalization | Test on Haiku + Sonnet | Validate model-specificity of skill effects |