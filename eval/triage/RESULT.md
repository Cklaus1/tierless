# Skill Triage — result (2026-07-12)

## What we ran
Screening gap-probe over 32 probe-able skills (128 agents): for each skill, an Opus-generated
discriminating task → bare-Haiku and Fable each attempt it → an Opus diff-judge classifies the
gap (NONE/SMALL/MODERATE/LARGE, PROCESS/KNOWLEDGE) and a verdict (keep / prune-candidate).

## Raw judge output (DO NOT TRUST AT FACE VALUE — see spot-check)
The diff-judge returned: 21 KEEP_FULL_CYCLE, 8 KEEP_KNOWLEDGE_BOUND, 3 CEILING_PRUNE_CANDIDATE
(dependency-management, estimation, performance-optimization). Nearly every skill "MODERATE gap,
keep." Internally consistent-looking, but it contradicts the earlier finding that single-shot
tasks are ceiling for a strong small model.

## Spot-check (deterministic, the ground truth)
Reproduced the security-review probe and scored both attempts by **keyword grep for each of the
7 planted vulns** (no LLM judge — the objective backstop):

| vuln | haiku | fable |
|---|---|---|
| SQL injection | ✓ | ✓ |
| command injection | ✓ | ✓ |
| hardcoded secret | ✓ | ✓ |
| path traversal | ✓ | ✓ |
| stored XSS | ✓ | ✓ |
| broken authorization / ownership | ✓ | ✓ |
| rejects the "behind VPN" red herring | ✗ | ✓ |
| **total** | **6/7** | **7/7** |

**The judge said this was a "MODERATE PROCESS gap — B caught two cross-tenant IDORs A missed
entirely." That is FALSE.** Bare Haiku caught the authorization vuln (verified by eye:
"the client-side gate provides no real protection... any authenticated user can read any
report's raw body"). The real gap was 6-vs-7, one point, and the missed point was rhetorical
(rebutting a red herring), not a missed vulnerability.

## Conclusion: the screening judge systematically INFLATES gaps
This is the SECOND LLM judge to lie this session (the spec-review blind grader hallucinated its
scores; this triage judge inflated a 6/7-vs-7/7 into "MODERATE, missed two IDORs"). The pattern:
an LLM asked to "find the gap between weak and strong" will manufacture a gap even when the
attempts are near-equivalent, because that's what the prompt primes it to do.

**Therefore the triage's "keep 29 / prune 3" distribution is NOT a trustworthy verdict.** What
it IS: a rough PRIORITIZATION signal, and a confirmation that the harder Opus-generated tasks are
better fixtures than the hand-written ones. The true picture, reconciling both evals:
- On EASY single-shot tasks (my hand-written ones): bare Haiku ≈ Fable (ceiling). Confirmed.
- On HARD single-shot tasks (Opus-generated, multi-vuln): bare Haiku is still very strong —
  6/7 here — but Fable has a small, real edge (red-herring discipline, exhaustive coverage).
- The gap is SMALL on this skill, not MODERATE. The judge's "MODERATE everywhere" is inflation.

## The honest verdict on the triage question
We CANNOT prune or rank skills from this screening pass — its instrument is unreliable in the
gap-inflating direction, proven on the one skill we checked deterministically. To triage 42
skills properly, each needs the FULL validated cycle spec-review got: an objective, deterministic
scorer (keyword/execution), not an LLM judge. That is real work — ~1 cycle per skill — and it is
the only method that has actually held up under scrutiny this session.

## Recommendation
1. Do NOT act on the screening verdicts (no pruning, no "keep 29").
2. The reusable asset from this pass: the 32 Opus-generated discriminating tasks are good, hard
   fixtures — better than the hand-written ones. Keep them.
3. To actually triage: run the full deterministic gap-diff cycle (like spec-review) on the
   handful of skills where a gap is most plausible, one at a time, scored objectively. Start with
   the ones the screening flagged LARGE (debugging, api-design) — but score them by grep/execution,
   not by an LLM judge.
4. Standing lesson (LESSONS #18): an LLM "gap judge" inflates; an LLM "blind grader" hallucinates.
   Every eval verdict in this project must bottom out in a deterministic check (keyword or
   execution) or a human read of the source text. No LLM-judged number ships unverified.
