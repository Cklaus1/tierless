# Eval Design: "Skills Close the Cheap-to-Frontier Gap on Coding Tasks"

## 1. The Claim

Adding a set of process-discipline "skills" to a cheaper LLM makes it produce work closer to a frontier model on coding tasks.

Formally: for a task T, let A = score(bare-cheap, T), B = score(skills-cheap, T), C = score(frontier, T). The claim is that B is significantly closer to C than A is, i.e. the gap-closure ratio (B - A) / (C - A) is meaningfully > 0 across a representative set of tasks.

## 2. Experimental Design

### 2.1 Arms

Three arms per task, identical task text and context:

| Arm | Model | Skills |
|-----|-------|--------|
| A | Cheap model (e.g. Haiku-4.5) | None (task text only) |
| B | Same cheap model | Relevant skill files provided, instructed to follow |
| C | Frontier model (e.g. Fable or Opus) | None (task text only) |

**Why three arms, not two.** A two-arm design (bare vs skills) can only show "skills helped." It cannot answer whether the skills brought the cheap model *close to the frontier bar*. The C arm is the reference bar -- the target that B should approach. Without C, you cannot measure gap-closure, only absolute improvement.

**Why hold the model constant between A and B.** The only variable between A and B is skill-state. If you also change the model, you cannot disentangle skill-lift from model-difference. This is the single most important control.

### 2.2 Tasks

**Minimum: 6 tasks.** A single task is a cherry-pick. Two tasks could be correlated (both testing the same dimension). Six tasks should span the skill library's categories:

1. **Bug-hunt / debugging** -- trace a defect in existing code (tests `debugging`, `code-archaeology`)
2. **Ambiguous specification** -- the ask is underspecified; the model must clarify (tests `requirements-elicitation`)
3. **Multi-step build** -- a project that unfolds over phases (tests `build-loop`, `deconstruct`)
4. **Migration / refactoring** -- change code while preserving behavior across modules (tests `code-migration`, `refactoring`)
5. **Security review** -- audit a design or code for vulnerabilities (tests `security-review`, `threat-modeling`)
6. **Architecture / design review** -- critique a design doc for hidden assumptions (tests `spec-review`)

**Task difficulty criterion: headroom check BEFORE the eval.** Each task must be verified (by running bare Haiku once) to have a score well below ceiling. If bare Haiku scores >= 0.85 on a task, the task is replaced. Ceiling tasks cannot discriminate between arms. This was learned the hard way: five of six tasks in the first v2 grid were at 0.85-1.0 for every arm, making the results noise.

**Task source: Opus-generated tasks are harder and more discriminating than hand-written ones.** The project's own hand-written tasks were too easy; Opus-generated fixtures showed real headroom. Use Opus-generated or adversarially-stressed tasks.

**What makes a good task for this eval:**
- Has a specific, checkable tell (not "quality")
- Has headroom: bare cheap model does not ace it
- Has a frontier model that does better than bare cheap (otherwise there is no gap to close)
- Is realistic: a real coding task, not a contrived puzzle
- Is self-contained: all context provided in the task directory

### 2.3 Runs

**N = 3 runs per cell.** A single run is untrustworthy -- the project's v1 eval inverted results twice from single-run variance. N=3 per (model, state, task) cell gives a spread that can be reported. The mean across 3 runs is the cell score.

**Why not N=10 or N=100.** More runs reduce variance but cost linearly. N=3 is the project's empirically-derived minimum for directional signals. If the spread at N=3 is large (e.g. one run at 0.2, another at 0.9), the task is unreliable and should be redesigned, not compensated for with more runs.

### 2.4 Grid Size

3 arms x 6 tasks x 3 runs = **54 arm-runs + 54 blind gradings**.

## 3. Scoring

### 3.1 Unit of Grading: Tells

Each task has 4-6 **tells**: specific, checkable things that separate disciplined work from plausible-looking work. A tell is a concrete, quotable feature of the output.

For each tell, assign:
- **HIT (1.0)** -- the output demonstrably contains it. Quote the line.
- **PARTIAL (0.5)** -- gestures at it but incompletely. Use sparingly; when unsure between PARTIAL and MISS, choose MISS.
- **MISS (0.0)** -- absent, or the output does the wrong thing.

**A tell is HIT only on evidence in the output.** "A reasonable model would have meant this" is a MISS. Grade as an adversary trying to disprove the skills' value.

### 3.2 Task Score

`task tell-hit rate = sum(tell scores) / number of tells`, in [0, 1].

### 3.3 Arm Score

Average tell-hit rate across all 6 tasks, per arm. Report per-task and the average.

### 3.4 The Claim Test: Gap-Closure Ratio

For each task: `(B - A) / (C - A)`, when `C > A`.

- ~0 --> skills didn't help (B no better than bare)
- ~1 --> skills brought the small model to the reference bar
- >1 --> skills pushed past the reference on these tells (possible: skills encode specific checks even a strong bare model skips)
- If `C approx A` on a task, the task doesn't discriminate -- flag it for replacement, don't report a ratio.

### 3.5 Additional Metrics

- **Skill lift per model:** `mean(skills) - mean(bare)` for each model. Does discipline help Haiku more than Opus (the "cheap models have more to gain" hypothesis)?
- **Backfire detection:** any cell where `skills < bare`. Flag and investigate.
- **The money number:** the cheapest model whose `skills` mean >= a pricier model's `bare` mean.

### 3.6 Scoring Method: Deterministic + Adversarial Human

**Never trust an LLM judge for the final score.** The project's first blind LLM grader hallucinated its per-flaw scores (credited bare-Haiku with catching items it never mentioned, inverting the result). LLM graders will manufacture gaps even when none exist, because the prompt primes them to "find the gap."

**Scoring hierarchy:**
1. **Deterministic checks where possible:** keyword grep, execution oracle (run the code, check the output), structural checks (does the file exist, does it have the right format). This is the gold standard.
2. **Adversarial human grading:** a human reads the output and scores against the tells, blind to arm label. Quote the supporting line in every HIT/PARTIAL justification.
3. **LLM judge as辅助 only:** if an LLM grader is used, it must be spot-checked against source text. Never trust its numbers without verification.

**Execution-based scoring for build tasks.** For tasks where the model produces code, run the code against a test battery. This is ground truth -- the code either passes or it doesn't. No LLM judgment needed. The project's task-12 (ledger build) used this pattern: 10 adversarial acceptance tests run against the arm's code.

## 4. Blind Grading

**The grader must not know which arm produced the output.** Strip arm labels from outputs before scoring. The grader sees anonymized outputs and scores against the tells without knowing whether it came from arm A, B, or C.

**The grader must not see the answer key.** `tells.md` is the answer key -- never shown to any arm, and the grader uses it as a checklist, not as a reference answer to match against.

**One grader, all arms of a task, in one sitting.** For consistency, grade all arms of a task in a single session. This prevents grader drift between sessions.

**Quote every verdict.** Every HIT/PARTIAL must include a quote from the output. This makes the grade auditable by a second grader.

## 5. Methodological Decisions and Pitfalls

### PITFALL 1: LLM Judge Bias (CRITICAL)

**Problem:** LLM graders hallucinate scores and inflate gaps. The project's first blind grader credited bare-Haiku with catching mobile/read-state/thundering-herd items it never mentioned, inverting the entire result.

**Guard:** Use deterministic scoring (keyword grep, execution oracle) wherever possible. If an LLM grader is used, spot-check every verdict against the source text. Never trust LLM-computed numbers.

### PITFALL 2: Ceiling / Headroom (CRITICAL)

**Problem:** If bare Haiku already scores >= 0.85 on a task, the task cannot discriminate. The first v2 grid had 5 of 6 tasks at ceiling, making results noise.

**Guard:** Run a headroom check on each task BEFORE the eval. If bare Haiku scores too high, replace the task. Build tasks to the difficulty where the thesis can actually be falsified.

### PITFALL 3: Single-Run Variance

**Problem:** Single runs inverted results twice in v1. A skills arm scoring below bare on one run was purely variance.

**Guard:** N=3 minimum per cell. Report the spread, not just the mean. If the spread is large, the task is unreliable.

### PITFALL 4: Fixture Contamination

**Problem:** Mutating tasks edit shared `context/` files in place, corrupting the fixture for other arms. In v1, this corrupted task 01 mid-run.

**Guard:** Fixtures are READ-ONLY reference. The solution lives in the response text, never on disk. Every mutable fixture file starts with a guard comment. Arm prompts forbid writing. Verify fixtures are pristine before each run (`git status --short eval/tasks/*/context/`).

### PITFALL 5: Test Leakage

**Problem:** Grader files in an arm-readable directory can be seen and optimized against by the build arm. In task-12b, the arm found `acceptance_test.py` in the task dir and ran it against its own code ("10/10").

**Guard:** Keep grader artifacts OUTSIDE the arm's readable path. "Don't read it" in a prompt is not enforcement -- structure the environment so the bad action is impossible.

### PITFALL 6: Knowledge vs Process Confound

**Problem:** A skill might help because it provides *knowledge* (a fact the model lacked) rather than *process* (a discipline the model skipped). The claim is about process skills, but the eval cannot distinguish these without analysis.

**Guard:** After the eval, analyze WHY each skill helped. Did the skilled model run the discipline steps (process), or did it just know a fact (knowledge)? The gap-diff method (observe frontier vs cheap, diff, classify as KNOWLEDGE or PROCESS) is the right tool here. Only process deltas should become skills.

### PITFALL 7: Model-Specific Effects

**Problem:** A skill validated on Haiku may not help Sonnet (Sonnet was already near ceiling on spec-review and code-archaeology). The skill closes Haiku's specific blind spots, not a universal gap.

**Guard:** Report per-model results. Don't generalize from one cheap model. The honest framing is "these skills close the SPECIFIC blind spots of the SPECIFIC model you run."

### PITFALL 8: Cherry-Picked Tasks

**Problem:** A single task (or a small set of correlated tasks) can produce a result that doesn't generalize.

**Guard:** Use 6+ tasks spanning different skill categories. If all tasks test the same dimension (e.g., all are bug-hunts), the result is narrow.

### PITFALL 9: The Frontier Bar Is Not Ground Truth

**Problem:** Treating C (frontier) as "correct" is wrong. The project found that on MVP-scoping, Opus also scored below bare Haiku -- it inflated the MVP with sync + reminders. "Reference" is a bar per tell, not a universal upper bound.

**Guard:** Score C the same way as A and B. C is another graded arm, not ground truth.

### PITFALL 10: Skills Can Backfire

**Problem:** In v1, Haiku + `roadmap` dropped a HIPAA/health-data risk that bare Haiku had caught. Focusing the model on the skill's frame (scope phasing) crowded out a domain instinct it had unaided.

**Guard:** Monitor for `skills < bare` cells. Investigate backfire cases. Skills should point at "what to also remember," not just "how to structure."

### PITFALL 11: Pre-Register the Success Criterion

**Problem:** Deciding what "supported" means AFTER seeing results is p-hacking. If you see (B-A)/(C-A) = 0.3 and then decide "0.3 is good enough," you've moved the goalpost.

**Guard:** Pre-register the success criterion BEFORE running the eval. Example: "The claim is supported if the mean gap-closure ratio across all 6 tasks is >= 0.5, AND no task shows skills < bare, AND the result holds across all 3 runs."

### PITFALL 12: The Skill Files Themselves Are a Variable

**Problem:** Different skills have different quality. A weak skill file may not help even if the model follows it. A strong skill file may help even on tasks it wasn't distilled against. The eval conflates "skill quality" with "skill effect."

**Guard:** Use the best-available skill files (those validated by gap-diff cycles). Report which skill was used for each task. If a skill was not validated, flag the result as preliminary.

### PITFALL 13: Prompt Leakage Between Arms

**Problem:** If the arm prompt for B (skills) reveals the task's intent more than the prompt for A (bare), B may perform better not because of the skill but because the prompt was more informative.

**Guard:** Keep the task text identical across arms. The only difference is whether skill files are attached. The arm prompt should be the same template, with the skill attachment being the only variable.

### PITFALL 14: Temperature / Sampling Variance

**Problem:** If different arms use different temperature or sampling parameters, the comparison is confounded.

**Guard:** Use identical model parameters (temperature, top_p, max_tokens) across all arms. The only variable is the prompt (skill files).

### PITFALL 15: Task Order Effects

**Problem:** If arms run sequentially (A first, then B, then C), the model may improve from session context or the prompt may drift.

**Guard:** Randomize arm order. Run A, B, C in random order for each task. Or run all three in parallel.

## 6. Decision Framework

### What counts as "claim supported"?

Pre-registered criterion:

1. **Primary:** Mean gap-closure ratio across all 6 tasks >= 0.5. This means skills close at least half the gap to the frontier on average.
2. **Secondary:** Skill lift (B - A) is positive on every task. No backfire.
3. **Tertiary:** The result holds across all 3 runs (no run inverts the direction).
4. **Exploratory:** Report the "money number" -- the cheapest model whose skills match a pricier model's bare score.

If criterion 1 is met but 2 or 3 is not, the claim is "partially supported -- directionally positive but with exceptions." If criterion 1 is not met, the claim is "not supported by this data."

### What makes results untrustworthy?

- Any single-run result (N=1)
- Tasks where bare model scores >= 0.85 (ceiling)
- LLM-judged scores without deterministic backstop
- Fixture contamination (dirty context files)
- Test leakage (arm sees the oracle)
- Different model parameters across arms
- Different task text across arms

## 7. Execution Plan

1. **Select 6 tasks** from the task library, ensuring headroom on each.
2. **Write tells** for each task (4-6 specific, checkable tells).
3. **Pre-register** the success criterion.
4. **Run all 54 arm-runs** (3 arms x 6 tasks x 3 runs), blind to arm labels.
5. **Grade blind** -- one grader, all arms of a task, in one sitting, quoting supporting lines.
6. **Compute** per-task and overall scores, gap-closure ratios, skill lifts.
7. **Analyze** mechanism: did skills help via process or knowledge?
8. **Report** with full transparency: per-cell scores, spreads, backfire flags, limitations.

## 8. Honest Limitations

- **Small N (6 tasks)** -- directional, not publication-grade. Widen before drawing strong conclusions.
- **Strong cheap models** -- Haiku-4.5 is already strong; many disciplines are table stakes. The skills' value concentrates on steps models still skip under time pressure. The gap would plausibly be larger on weaker models (Qwen/Llama-class), but those aren't in this gateway.
- **Model-specific effects** -- skills validated on Haiku may not help Sonnet. The method (gap-diff) is portable; individual skills are not.
- **Skill quality variance** -- not all skills are equally well-written. A weak skill file may not help.
- **Single-shot vs multi-step** -- the project's key finding is that discipline's value is invisible on single-shot tasks and decisive on multi-step tasks. This eval should weight multi-step tasks more heavily.