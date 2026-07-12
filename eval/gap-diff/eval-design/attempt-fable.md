# Eval design: do process-discipline skills close the gap between a cheap model and a frontier model on coding tasks?

## 0. The claim, made precise

Informal claim: "adding a set of process-discipline 'skills' to a cheaper LLM makes it produce work
closer to a frontier model on coding tasks."

This is a **gap-closure claim**, not merely an improvement claim. It has three load-bearing parts
that must each be operationalized:

1. **"Cheaper LLM" / "frontier model"** — a concrete model pair (e.g., Haiku-class vs Opus-class),
   run in the *same agent harness* with the same tools. "Cheaper" must remain true after the skills
   are added (skills consume tokens and turns), so cost is a measured outcome, not an assumption.
2. **"Process-discipline skills"** — a pinned, versioned artifact set (e.g., skill files injected
   into context or loaded on trigger: plan-before-coding, run-tests-before-claiming-done,
   verify-end-to-end, self-review-the-diff, etc.). The eval tests *this specific set*, and the
   design must prevent the set from being tuned on the test tasks.
3. **"Produce work closer to"** — two distinct senses, both worth measuring:
   - **Outcome closeness**: the cheap+skills model's *scores* move toward the frontier model's
     scores (functional correctness, code quality).
   - **Artifact closeness**: the *work products* (diffs, commit hygiene, test coverage, absence of
     debris) become harder to distinguish from frontier output in blinded comparison.

**Primary estimand — gap closure on the primary metric:**

```
GapClosed = (S_cheap+skills − S_cheap) / (S_frontier − S_cheap)
```

computed on the aggregate primary score S, with a bootstrap CI over tasks (see §6). GapClosed = 0
means skills did nothing; 1.0 means full parity; >1 means surpassing the frontier model; negative
means skills hurt. This ratio is only meaningful when the denominator (the baseline gap) is
substantially positive — verifying that is itself part of the eval (§6.4).

**Pre-registered decision rule** (stated up front so results can't be laundered post hoc — §7).

---

## 1. Experimental arms

| Arm | Model | Context additions | Purpose |
|-----|-------|-------------------|---------|
| A | Cheap | none (stock harness) | Baseline; denominator anchor |
| B | Cheap | process-discipline skills | Treatment |
| C | Frontier | none (stock harness) | Target; numerator anchor |
| P | Cheap | **placebo skills**: equal token count of generic, well-written but process-irrelevant guidance (e.g., style trivia, restated harness docs) | Controls for "any extra instruction text / longer context / more induced turns" vs. the specific skill *content* |
| D (secondary) | Frontier | same skills | Tests whether skills are cheap-model-specific or universally good; interaction term |

Notes on arm construction:

- **Identical harness everywhere**: same agent scaffold, same tool definitions, same system prompt
  (modulo the skill/placebo injection), same max-turn and max-token limits, same sandbox image,
  same temperature/sampling settings where the APIs allow it. Any harness difference between arms
  is a confound that will silently dominate the result.
- **The placebo arm P is the most commonly skipped and most important control.** Skills typically
  (a) lengthen the prompt, (b) induce more turns and more test-running, i.e. more *compute*. If B
  beats A, you must be able to say whether the *discipline content* did it, or whether any
  extra scaffolding/compute would have. If B ≈ P, the claim as stated is unsupported even if B > A.
- **Compute accounting instead of compute capping.** Don't hard-cap B to A's token budget (that
  would strangle the mechanism being tested — discipline legitimately spends tokens on tests and
  review). Instead, record tokens/turns/wall-clock/$ per run and report cost-conditioned results
  (§6.5). Do keep one *shared generous cap* (e.g., 2× the p95 of frontier usage) so runaway loops
  terminate identically in all arms.
- **Model version pinning**: pin exact model snapshot IDs; never "latest" aliases. Run all arms
  **interleaved in the same time window** (randomize run order across arms) so provider-side model
  or infra drift affects all arms equally.
- **If the claim is meant to generalize** ("cheaper LLMs" plural), replicate on a second model
  pair (e.g., a different vendor's small/large pair). One pair supports only the narrow claim.

---

## 2. Task suite

### 2.1 Sources and composition

Target **n = 200 tasks** (power analysis in §6.3), drawn from:

- **~100 curated public agentic tasks** with hidden test oracles — e.g., a SWE-bench-Verified-style
  subset (real repos, real issues, held-out fail-to-pass tests), filtered for solvability of the
  environment (tests deterministic, dependencies pinned).
- **~60 fresh tasks harvested from post-training-cutoff commits/issues** in active OSS repos
  (issue + the maintainer's fix-commit's tests as oracle). This is the contamination hedge: both
  models may have memorized popular benchmark fixes, and memorization differentially favors the
  frontier model, inflating the gap, or favors the cheap model, shrinking it — either way it
  corrupts the estimand.
- **~40 constructed tasks** in private repos the models have never seen, spanning categories that
  public benchmarks under-represent and that process discipline plausibly affects: multi-file
  refactors, "add feature + tests", debugging with a misleading symptom, tasks with a pre-existing
  broken test the agent must not "fix" by deletion.

Stratify deliberately across: **task type** (bugfix / feature / refactor / test-writing / debug),
**language** (at least 2–3), **repo size**, and **difficulty** (bucketed by baseline frontier pass
rate from a small pilot: easy/medium/hard). Report per-stratum results; the headline number should
be the stratified aggregate.

### 2.2 Difficulty calibration and ceiling/floor management

Run a **pilot (~30 tasks × arms A and C, 3 runs each)** first, to:

- Verify the baseline gap exists: if frontier ≈ cheap on the suite, gap closure is undefined and
  the suite is wrong (too easy → ceiling; too hard → floor; or the models are closer than assumed).
  Aim for pilot pass rates roughly: cheap 30–50%, frontier 60–85%. Rebalance strata until the
  suite has headroom in both directions.
- Shake out environment flakiness (§8.6) before burning the real budget.

Pilot tasks are then **excluded from the main run** (they informed design decisions).

### 2.3 Firewall between skill development and evaluation

This is the single biggest validity threat in practice: skills are usually authored and iterated
*by looking at model failures on some task set*. Rules:

- Maintain a hard **dev/test split of tasks**. Skills may be developed and tuned against the dev
  set only. The 200-task test set is frozen (hashes committed) before anyone runs the treatment
  arm on it, and is run **once**.
- Audit skill text for task-specific leakage (repo names, API names, bug patterns that appear in
  test tasks). A skill that says "when editing the pagination module, remember the off-by-one" is
  a cheat, not a process discipline.
- If iteration on skills continues after seeing test results, that's a new experiment requiring a
  new held-out test set.

---

## 3. Run protocol

- **k = 3 runs per task per arm** (nondeterminism is large in agentic settings; a single run per
  task confounds model variance with treatment effect). 5 arms × 200 tasks × 3 runs = **3,000
  runs**. If budget forces cuts, cut arm D first, then reduce placebo to k=2; never cut k on A/B/C
  below 3.
- **Fresh sandbox per run**, identical container image, network policy identical across arms
  (ideally hermetic/offline after dependency install, so no arm can look up the real fix).
- **Randomized, interleaved execution order** across arms and tasks (guards against time-of-day
  provider load, model drift, and infra degradation correlating with arm).
- **Uniform failure taxonomy**: distinguish *model failure* (wrong code, gave up) from
  *infrastructure failure* (sandbox crash, API 5xx, rate-limit timeout). Infra failures are
  retried up to 2× and excluded if unresolved (logged, counted, and reported — if infra failure
  rate differs by arm, e.g. because skills-runs are longer and hit timeouts, that's a finding, not
  noise to discard). Model failures are never retried.
- **Everything logged**: full transcripts, tool calls, diffs, token counts, seeds where supported,
  skill version hash, harness commit, model snapshot IDs. The eval must be re-runnable.

---

## 4. Scoring

### 4.1 Primary metric: functional correctness (objective)

**Hidden held-out tests** per task (fail-to-pass + pass-to-pass regression suite), executed in a
clean checkout with the agent's diff applied. Score per run:

- `resolved` ∈ {0,1}: all fail-to-pass tests pass AND no pass-to-pass regressions.
- Primary aggregate: **mean resolved rate** per arm (average over runs, then tasks — i.e., per-task
  mean of k runs, then unweighted/stratified mean over tasks).

Guardrails:
- Detect and reject **oracle-gaming**: diffs that edit/delete tests, mock out the tested path,
  or special-case the test inputs. Automated checks (diff must not touch test files unless the
  task is test-writing; grep for test-name references in source) + human audit of a random 5% of
  passing runs, oversampling suspiciously small diffs.
- **Flaky-test quarantine**: pre-run each task's test suite 10× on the gold solution; any test
  that flakes gets removed from the oracle before the eval starts.

Why primary: the claim is about *work quality*, and functional correctness is the one signal that
cannot be flattered by verbose, well-formatted output — which matters because process-discipline
skills specifically make output *look* more disciplined (§8.2).

### 4.2 Secondary metric: blinded pairwise artifact quality (the "closeness" measure)

For each task, sample one run per arm and form **blinded pairwise comparisons** of final work
products (diff + any added tests + final summary), judged by an LLM judge on a fixed rubric
(correct-looking, minimal, idiomatic, tested, no debris/dead code, no unrelated changes):

- **B vs C** (cheap+skills vs frontier): the headline "closeness" comparison. Report B's win rate
  against C; parity ≈ 50%.
- **A vs C** (baseline distance) and **B vs A** (direct improvement) for triangulation.
- Also an **indistinguishability probe**: judge asked to *classify* which of two blinded outputs
  came from the frontier model; accuracy near chance for (B,C) pairs = artifact closeness.

Judge-bias controls (each is a known failure mode):
- **Position swap**: every pair judged twice with order swapped; discard/flag inconsistent verdicts.
- **Length/verbosity bias**: strip agent commentary; judge the diff and tests, not the prose.
  Report correlation of verdicts with diff length as a diagnostic.
- **Self-preference bias**: judge model from a *different family* than any arm's model; ideally two
  judges from different vendors, report agreement.
- **Style-over-substance bias**: rubric anchored to functional-correctness ground truth on a
  calibration slice — before trusting the judge, verify on ~50 human-labeled pairs that judge
  agreement with expert human preference is ≥ some threshold (e.g., 80%, Cohen's κ reported). If
  the judge can't match humans, the secondary metric is human-labeled on a subsample instead.

### 4.3 Tertiary/diagnostic metrics (never used for the verdict — Goodhart hazard)

Process-adherence measures (ran the tests before finishing, wrote a plan, reviewed its own diff,
touched-file count, regression-suite executions). These are the *mechanism* the skills target, so
using them as evidence would be circular — the skills literally instruct the model to do these
things. They are reported only to explain *why* results happened (mediation analysis: did B's wins
come disproportionately on runs where the discipline behaviors actually occurred?).

### 4.4 Cost and latency

Per run: input/output tokens (by model), $ cost at list price, wall-clock, turn count. Used in §6.5.

---

## 5. What "closer" is NOT allowed to mean

Explicitly excluded operationalizations, because they're gameable or vacuous:

- **Textual similarity of B's output to C's output** (embedding distance, BLEU on diffs). Two
  correct fixes can be textually unlike; imitating frontier *style* is not the claim.
- **Improvement on process metrics alone** (§4.3, Goodhart).
- **Judge preference without functional anchoring** (§4.2 calibration requirement).

---

## 6. Analysis plan

### 6.1 Primary analysis

Paired-by-task design. For the resolved-rate outcome:

- Per-task score = mean of k runs (in [0,1]). Compute arm means and all pairwise differences
  (B−A, C−A, B−P, C−B).
- **Cluster bootstrap over tasks** (resample tasks with replacement, 10,000 reps; runs within a
  task travel together — runs are correlated within task, so naive per-run CIs are anti-conservative)
  for CIs on each difference and on **GapClosed = (B−A)/(C−A)**.
- Cross-check with a **mixed-effects logistic regression**: `resolved ~ arm + (1|task)` (+ strata
  fixed effects). Consistency between the two increases confidence; discrepancy triggers
  investigation.

### 6.2 Secondary analyses

- Pairwise win rates (§4.2) with the same task-level bootstrap.
- Per-stratum GapClosed (does the effect concentrate in, e.g., multi-file tasks?).
- Placebo contrast: **B − P** must be positive and a substantial share of B − A, else the effect
  is scaffolding, not skill content.
- Variance analysis: does B reduce *run-to-run variance* per task vs A? (Discipline plausibly
  makes output more consistent — a real and reportable form of "closer to frontier", which tends
  to be more consistent.)
- Frontier interaction (arm D): if D − C ≈ B − A, skills are model-agnostic uplift; the "closes
  the gap to frontier" framing then needs the caveat that a skills-using frontier model re-opens it.

### 6.3 Power / sample size (why 200 × 3)

Pilot-informed, but roughly: with per-task paired comparisons and expected baseline rates around
A ≈ 40%, C ≈ 70% (gap = 30pp), detecting a B−A effect of 10pp (i.e., ~33% gap closure) at α=0.05
with 80–90% power needs on the order of 150–250 paired tasks given typical inter-task variance in
agentic suites (task effects are large; k=3 within-task runs mainly shrink measurement noise, they
don't multiply effective n). 200 tasks with k=3 sits in that band and leaves room for per-stratum
reads. Recompute properly from pilot variance before the main run; if pilot variance implies
<70% power for the pre-registered minimum effect, enlarge the suite before running, not after.

### 6.4 Estimand sanity conditions (checked before interpreting GapClosed)

- **C − A > 0 with CI excluding 0** and ideally ≥ 10pp. If not, report "no meaningful gap to
  close on this suite" and stop — a GapClosed ratio with a near-zero denominator is noise.
- Per-task gap sign heterogeneity reported: on tasks where the cheap model already beats the
  frontier model, gap closure is ill-defined; the regression estimand (arm effects) is the robust
  fallback and is always reported alongside the ratio.

### 6.5 Cost-conditioned reading

The claim's economic content is "frontier-ish quality at cheap-ish price". Report a **cost–quality
Pareto plot** (x = mean $ per task, y = resolved rate) with all arms. Key numbers:
- Cost multiplier of B vs A (skills inflate tokens/turns — by how much?).
- Whether B remains below C's cost. If skills push the cheap model's per-task cost to ≥ the
  frontier model's, the claim is technically about quality but practically dead; say so.
- Optional strong comparison: **compute-matched frontier** — what does C achieve at B's dollar
  budget (e.g., frontier with a tighter turn cap)? This answers "should I buy skills or buy tokens?"

### 6.6 Multiplicity

One pre-registered primary metric (resolved rate) and one primary contrast (GapClosed via B−A,
C−A). Everything else is labeled secondary/exploratory; no p-value shopping across the metric
zoo. No interim peeking with optional stopping — n is fixed by the pre-registration.

---

## 7. Decision rule (pre-registered)

**Claim SUPPORTED** if all of:

1. B − A > 0, 95% CI excluding 0, on resolved rate (primary).
2. **GapClosed ≥ 25%** point estimate with 95% CI lower bound > 0. (25% is a judgment call —
   pre-register whatever threshold stakeholders agree constitutes "closer" worth acting on; the
   point is that it's fixed *before* data.)
3. **B − P** accounts for ≥ half of B − A (the effect is the skill content, not the scaffolding).
4. No oracle-gaming pattern in the audit (§4.1) that inflates B specifically.
5. Secondary artifact-closeness metric directionally agrees (B vs C win rate improves over
   A vs C win rate); if it sharply disagrees with the primary, publish both and investigate
   before claiming.

**Claim REFUTED** if B − A CI excludes positive effects ≥ the pre-registered minimum, or B < A.

**INCONCLUSIVE** otherwise (report CIs; specify what a follow-up needs — usually more tasks or a
harder/easier suite).

Scope statement attached to any verdict: supported claim applies to *this skill set, this model
pair, this harness, this task distribution* — generalization beyond that requires the second
model pair (§1) and ideally a second harness.

---

## 8. Threats to validity — enumerated

**8.1 Skill/test contamination (design-side overfitting).** Skills tuned on test tasks, or
task-specific hints embedded in skill text. Mitigation: dev/test firewall, frozen test set, skill
text audit, run-once policy (§2.3).

**8.2 Judge flattery of "disciplined-looking" output.** Process skills make transcripts and
summaries look rigorous; LLM judges reward structure and confidence. Mitigation: functional tests
as primary; judge sees artifacts not prose; length-bias diagnostics; human calibration (§4.2).

**8.3 Compute confound.** Skills → more turns/tokens → more chances to succeed, independent of
discipline content. Mitigation: placebo arm, cost-conditioned analysis, compute-matched frontier
comparison (§1, §6.5).

**8.4 Benchmark contamination of models.** Public benchmark fixes memorized differentially by
model. Mitigation: post-cutoff and private task strata; check whether results differ between
public and fresh strata — a big discrepancy is a red flag for the public stratum, not the fresh one.

**8.5 Harness asymmetry.** Different tool-calling reliability, default prompts, or token limits by
model; the cheap model failing due to harness friction masquerades as capability gap. Mitigation:
one harness, pinned config, transcript audits of early runs from each arm for tool-call
malfunctions.

**8.6 Environment flakiness.** Flaky tests, network-dependent installs, sandbox nondeterminism
create noise and, worse, *bias* (longer skill-runs hit more timeouts). Mitigation: hermetic
sandboxes, flaky-test quarantine, infra-failure taxonomy with per-arm failure-rate reporting (§3).

**8.7 Nondeterminism / single-run illusions.** k=1 runs make treatment effects indistinguishable
from sampling noise. Mitigation: k=3, variance reported, task-clustered inference.

**8.8 Ceiling/floor effects.** Suite too easy (frontier ≈ 100%, gap tiny, ratio unstable) or too
hard (everyone ≈ 0). Mitigation: pilot calibration to mid-range pass rates (§2.2).

**8.9 Oracle gaming.** Passing by editing tests, mocking, or hardcoding. Discipline skills that
say "make the tests pass" can *increase* this. Mitigation: hidden tests, diff restrictions,
automated + human audits oversampling the treatment arm (§4.1).

**8.10 Model drift / time confound.** Provider updates mid-eval. Mitigation: pinned snapshots,
interleaved randomized scheduling, short eval window (§1, §3).

**8.11 Metric circularity.** Scoring on process adherence that the skills directly command.
Mitigation: process metrics diagnostic-only (§4.3).

**8.12 Aggregation artifacts.** Per-run averaging over-weights tasks with fewer infra exclusions;
ratio-of-means vs mean-of-ratios discrepancies in GapClosed. Mitigation: per-task means first,
stratified aggregation, both regression and ratio estimands reported (§6.1, §6.4).

**8.13 Publication-grade cherry-picking.** Many metrics/strata → something is always "significant".
Mitigation: pre-registered primary metric, contrast, threshold, and n; exploratory results labeled
as such (§6.6, §7).

**8.14 Generalization overreach.** One model pair, one harness, one skill version → claim stated
as if universal. Mitigation: scope statement in the verdict; replication arm on a second pair if
the general claim is needed (§1, §7).

**8.15 Prompt-interaction fragility.** Skills may work only with this exact system prompt or
break at a slightly different context length. Mitigation (robustness check, exploratory): re-run a
50-task subsample with a lightly paraphrased skill set / reordered skills; a real effect survives
paraphrase.

---

## 9. Deliverables and qualitative layer

- Main results table (arms × {resolved rate, win rate vs C, $ per task, tokens, turns}) with CIs;
  GapClosed headline with CI; per-stratum breakdown; Pareto plot.
- **Failure/success anatomy**: human read of ~30 sampled transcripts — 10 tasks where B succeeded
  and A failed (did the discipline mechanism actually cause the save?), 10 where B failed anyway,
  10 where B regressed vs A (skills can cause overhead-death: budget exhausted on ceremony).
  Quantitative gap closure without this mechanism check invites believing a number produced by an
  artifact.
- Full artifact release (internally): transcripts, diffs, seeds, configs, skill hashes, analysis
  notebook — sufficient for an independent re-run.

## 10. Budget sketch

3,000 runs; assume ~$0.15–0.40/run cheap-model arms (skills arms toward the high end), ~$1.50–3/run
frontier arms → order of **$3k–6k** in API spend plus sandbox compute; pilot ~5% extra; judging
(~800 pairwise calls × 2 orderings × 2 judges) is small by comparison. Human labeling: ~50
calibration pairs + ~30 transcript reads ≈ 2–3 expert-days. Cheap relative to the decision the
eval informs (whether to deploy skills fleet-wide), which is the right lens for sizing it.
