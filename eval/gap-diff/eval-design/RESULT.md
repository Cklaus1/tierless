# Gap-diff on eval-design itself (2026-07-12)

Reflexive cycle: can a skill make the eval HARNESS better? Task: "design an eval for the claim that
skills help a cheap model." Checklist = 12 methodological disciplines, each mapping to a failure THIS
project hit (LLM-judge hallucination, ceiling tasks, single-run variance, fixture contamination,
grader arithmetic, etc.). Deterministic keyword scoring + eye-verification.

## Result: CEILING (perfect tie)
| arm | /12 |
|---|---|
| Haiku bare | 12 |
| Haiku + qa-testing + ai-building | 12 |
| Fable bare | 12 |

Eye-verified the two hardest tells (not keyword artifacts): bare Haiku gave genuine, detailed
reasoning on #3 (don't trust an LLM judge — "graders manufacture gaps even when none exist, because
the prompt primes them to find the gap") and #4 (headroom check — "five of six tasks in the first v2
grid were at 0.85-1.0, learned the hard way"). Real mastery, not phrase-dropping.

## Verdict for the roadmap question ("should we gap-diff the eval harness?")
**No eval-design skill to build — it's at ceiling.** A modern model, bare, already designs a rigorous
eval (control the variable, objective/deterministic scoring, distrust LLM judges, headroom-check,
blind grading, execution oracles, guard contamination, pre-register success). The existing skill arm
(qa-testing + ai-building) added nothing because there was no gap to close. This is the same pattern
as the standard-checklist skills (LESSONS #20): eval-design is a discipline the model already has.

## Important CAVEAT — this cycle was partly open-book (a real methodological flaw)
The arms could read this repo — including LESSONS.md and eval/, which document these exact disciplines
and failures. Bare Haiku's answer CITED our specific findings ("the first blind LLM grader
hallucinated", "five of six tasks... in the first v2 grid"). So the 12/12 may reflect the model
STUDYING OUR ANSWER KEY, not independently deriving good eval design. This doesn't change the "ceiling"
verdict (even open-book, no skill beat bare), but it means the cleanliness is compromised. A proper
version would run the arms in a sandbox with no access to this repo's eval/ and LESSONS.md. Logged as
its own lesson: **when the task domain IS the project, the project's own docs are a test leak** — the
same contamination class as LESSONS #17 (grader files in the arm-readable path), one level up.

## Net
Reflexive gap-diff was worth running — it (a) confirmed eval-design is ceiling (no skill needed), and
(b) surfaced a new contamination mode (repo-as-answer-key) that matters for ANY future self-referential
cycle. Both are useful negatives. It did NOT produce a skill.
