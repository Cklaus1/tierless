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

## FULL-CYCLE CONFIRMED — CEILING (were screened as candidates, then disproven) (2)
- **version-control** — screen said +3; full cycle w/ planted traps + eye-verify = CEILING. Bare Haiku
  caught all four traps (missed-callsite/incomplete-rename, stale docs, unrelated dep bump, junk file).
- **compiler-building** — screen said +5; full cycle = CEILING. Bare Haiku caught the code-specific
  traps incl. the subtle dead-`<`-grammar-rule and the NAME-eval crash. (`eval/gap-diff/*-full/RESULT.md`)

**Methodological correction:** the auto-generated screen OVER-ESTIMATES candidate gaps ~2-3x (generic
keyword items the model expresses in different words score as misses). It is reliable for CEILING
verdicts but NOT for gap magnitude. The two biggest screened candidates both collapsed to ceiling on a
full hand-built + eye-verified cycle. Updated prior: the remaining 7 candidates below are likely
ceiling too.

## SCREENED — remaining GAP CANDIDATES (keyword ≥2, now LIKELY inflated → probably ceiling) (7)
| skill | keyword gap | note |
|---|---|---|
| database-design | +3 | candidate — likely inflated (screen over-estimates) |
| infra-ops | +3 | candidate — likely inflated |
| code-migration, requirements-elicitation, security-review, systems-programming, tech-doc | +2 | candidates — likely inflated (both +3/+5 candidates we tested were ceiling) |

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
