# Coding-itself probe: does a skill improve CODE CORRECTNESS? (2026-07-12)

Prior evals said "writing correct code is ceiling" (ledger task, task 12: bare Haiku 10/10). But
that task's invariants were spelled out. This probe uses a HARDER spec with a subtle interaction
(monthly day-of-month overflow SKIP + count semantics + half-open window), scored by an execution
battery (10 cases, self-verified against a reference at 10/10 before use). Four arms.

## Result (execution-scored)
| arm | /10 | failed case |
|---|---|---|
| Haiku bare | 9 | monthly_day31_skip (threw an exception) |
| Sonnet bare | 9 | monthly_day31_skip (clamped to Feb28, corrupted whole series) |
| Haiku + deconstruct+verify | 9 | monthly_day31_skip (skipped Feb correctly, then clamped Mar→28) |
| **Fable bare** | **10** | — |

## The finding — a REAL code-correctness gap, eye-verified
On the one hard case (start Jan-31 monthly; spec: skip months without a 31st → Jan31, Mar31, May31):
- **Fable:** correct — Jan31, Mar31, May31.
- **Sonnet:** Jan31, **Feb28**, Mar28, Apr28... — the classic day-overflow-clamp bug, then carried the
  clamped day forward, corrupting the series.
- **Haiku+skill:** Jan31, **Mar28**, Apr28... — the verify discipline HELPED PARTIALLY (it correctly
  skipped Feb, which bare arms didn't) but still clamped March onto a 28 track.
- **Haiku bare:** threw an exception on the input.

This is the FIRST measured code-correctness gap: all three cheap arms got the tricky month logic
wrong, each differently, and only the frontier model got it right. It is NOT a spec ambiguity — the
spec stated the exact expected output.

## But: the skill did NOT close the gap (it half-helped)
Haiku+deconstruct+verify still scored 9/10 — same total as bare. The verify discipline changed the
FAILURE MODE (bare Haiku crashed; skilled Haiku produced a cleaner-but-still-wrong answer that at
least handled the Feb-skip) but did not make the code correct. The specific bug (day-overflow clamp
vs skip) is a KNOWLEDGE/reasoning gap about calendar arithmetic, not a process the "enumerate edge
cases" discipline reliably fixes — the model enumerated the edge case AND STILL implemented it wrong.

## Interpretation
- Code correctness is NOT fully ceiling — a hard enough spec (subtle calendar interaction) opens a
  real gap between cheap models and frontier. The ledger task was just too easy to show it.
- BUT a process skill (deconstruct/verify) does NOT close this particular gap, because the failure is
  in the REASONING about the domain (how monthly recurrence should handle Dec-31-style overflow), not
  in the process of remembering to check edges. The skilled model checked the edge and still got the
  logic wrong.
- This is the cleanest example yet of the KNOWLEDGE-vs-PROCESS boundary (LESSONS #14/#20): the gap is
  real, but it is not distillable into a discipline skill — you can't teach "get calendar math right"
  as a process. It would need either a stronger model or a domain-specific library/reference.

## Honest takeaway for the product
Skills help where the gap is PROCESS (derive the non-obvious, phase the work). They do NOT help where
the gap is the model getting the actual computation wrong — that's capability/knowledge. The
coding-itself gap here is the latter kind. So: still no distillable "coding-itself" skill; the value
remains in process/review skills, and this probe shows WHY (a real code gap exists but resists
process-distillation).
