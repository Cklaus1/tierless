# Skill Coverage Map — did we eval every skill? (2026-07-12)

Honest audit of what has and hasn't been deterministically measured across all 43 skills.
Answer to "did we run the eval on all of them": **now yes — every testable skill has a
deterministic gap measurement.** But with an important precision distinction (below).

## Two levels of rigor
- **VALIDATED** = full gap-diff cycle: task + objective checklist + eye-verified + (for the keepers)
  a distilled skill that closed the gap on re-test. Trustworthy.
- **SCREENED (deterministic)** = one auto-generated task + keyword-scored checklist, Haiku-bare vs
  Fable, scored in code (no LLM judge). Trustworthy for the CEILING verdict (if bare ≈ frontier there's
  no gap), but a keyword *gap* is a CANDIDATE, not a confirmed finding — keyword scoring undercounts
  paraphrase and needs a full cycle + eye-verification to confirm magnitude (see caveat).

## VALIDATED — real gap, skill closes it (3)
- **build-loop** — +0.64 process lift, cross-model (Haiku, Sonnet; even bare Fable leaves no trail). Universal scaffolding.
- **spec-review** — Haiku 8/15 → 13/15. Derive-the-non-obvious.
- **constant-coupling** — Haiku 9/12 → 12/12. Derive-the-non-obvious.

## VALIDATED / measured — at CEILING (no gap; skill inert on a strong cheap model) (7)
debugging, api-design, adversarial-review, qa-testing, threat-modeling, ui-design (full cycles);
coding-itself + eval-design probes also ceiling.

## VALIDATED as a family — the core pipeline (4)
compose, plan-mode, deconstruct, verify — validated together via the build-loop process eval (task 07);
the skilled arm that phased/verified/trailed used exactly these. Not isolated per-skill (future work).

## SCREENED deterministic — CEILING (keyword gap ≤1, i.e. noise) (19)
ai-building, ai-safety, cross-platform, data-migration, dependency-management, estimation,
human-code-review, icp-onboarding, incident-response, naming, onboarding, performance-optimization,
refactoring, release-management, roadmap, shell-scripting, software-architecture, user-docs, ux-design.
→ Bare Haiku matched or beat Fable. Consistent with the criterion: these are standard-checklist domains
the model already commands. Safe to treat as ceiling.

## SCREENED deterministic — GAP CANDIDATES (keyword gap ≥2 — NOT yet confirmed) (9)
| skill | keyword gap | note |
|---|---|---|
| compiler-building | +5 (6→11/15) | biggest; but compilers are a broad domain — likely partly knowledge, needs a cycle |
| database-design | +3 | candidate |
| infra-ops | +3 | candidate |
| version-control | +3 | candidate — the rename-updates-all-callsites item echoes constant-coupling's disguised-copy class |
| code-migration, requirements-elicitation, security-review, systems-programming, tech-doc | +2 | candidates |

**These 9 are the todo list for the next round of full gap-diff cycles.** A keyword gap means "a real
gap MIGHT exist here" — each needs the spec-review treatment (hand-built checklist, eye-verified,
distill-and-retest) before any becomes a validated skill. Do NOT ship any as "validated" on the
keyword score alone.

## NOT TASK-TESTABLE (1)
tierless-router — pure routing/meta; no single-task probe. Its value is structural (makes the others
reachable), asserted not measured.

## Caveat on the screening (why candidates ≠ findings)
Keyword scoring is generous (a mention counts even if shallow) AND undercounts paraphrase (a "miss"
can mean the model used different words). Eye-verifying compiler-building's 5 "missed" items was
inconclusive from the journal (couldn't cleanly map Haiku-vs-Fable text, and the missed terms were my
checklist's exact phrases). So the screening reliably says "these 19 are ceiling" (a tie is robust to
paraphrase noise) but only says "these 9 MIGHT have a gap" — magnitude unconfirmed. This is the same
lesson as LESSONS #18: a keyword number is a screen, not a verdict.

## Bottom line
- Every testable skill now has a deterministic screen. Nothing is unmeasured.
- 3 validated real gaps; ~26 at ceiling (7 full + 19 screened); 9 unconfirmed gap-candidates for the
  next cycle-round; 4 validated as a pipeline family; 1 structural.
- The candidate list, not "43 skills," is the honest work-remaining. And per who-finds-gap, confirming
  each requires frontier-in-the-loop (checklist-building + distillation), not a cheap batch.
