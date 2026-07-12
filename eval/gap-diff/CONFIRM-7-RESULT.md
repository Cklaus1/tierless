# Confirming the 7 remaining gap-candidates (2026-07-12) — ALL CEILING

Ran the full deterministic cycle (hand-built trap-task + hand-built checklist + eye-verification) on
all 7 screened gap-candidates. Result: **every one is ceiling. No new validated skill.**

## Scores (keyword) then eye-verdict
| skill | haiku | fable | keyword gap | eye-verified verdict |
|---|---|---|---|---|
| infra-ops | 13 | 13 | 0 | CEILING |
| requirements-elicitation | 13 | 12 | −1 | CEILING (Haiku ≥ Fable) |
| security-review | 12 | 11 | −1 | CEILING (Haiku ≥ Fable) |
| systems-programming | 13 | 13 | 0 | CEILING |
| tech-doc | 13 | 13 | 0 | CEILING |
| database-design | 10 | 12 | +2 | CEILING — keyword artifact (see below) |
| code-migration | 10 | 12 | +2 | CEILING — keyword artifact |

## The two +2 "gaps" were paraphrase noise (eye-verified)
- **database-design:** grep for "float"/"foreign key" returned 0 for Haiku — but Haiku's review
  actually opens with "§1.1 orders.amount uses float for currency (CRITICAL) → use numeric(12,2)" and
  "§2.1 No foreign keys (CRITICAL)". It caught EVERY planted trap (float money, FKs, unique email,
  CHECK/enum, NOT NULL, tenant isolation) in MORE detail than the checklist. The regex missed its
  phrasing. True gap: 0.
- **code-migration:** bare Haiku caught the KEY trap — rejecting the big-bang rewrite (13 mentions of
  strangler/incremental/pushback) — and the dual py2/py3 run. Its two keyword "misses" (#3 trunk-
  diverges, #10 wording) were paraphrase. True gap: ~0.

## Every trap was caught by bare Haiku across all 7
- database: float money, no FKs, missing indexes, no pagination, tenant isolation — all caught.
- infra-ops: secrets in CI logs, :latest, stop-run downtime, fake rollback — caught.
- code-migration: REJECTED the big-bang rewrite (the trap), proposed strangler — caught.
- requirements-elicitation: didn't build the CSV button; surfaced GDPR + authz + volume forks — caught.
- security-review: predictable MD5 token, plaintext password, no expiry, enumeration — caught.
- systems-programming: sprintf overflow, unchecked open/write, log injection — caught.
- tech-doc: problem-is-the-solution, no numbers, no alternatives, cache invalidation — caught.

## FINAL verdict for the library
The validated real-gap set is **definitively 3**: build-loop (scaffolding), spec-review + constant-
coupling (derive-the-non-obvious). Of the full 43:
- 3 validated real gaps
- ~39 measured/confirmed CEILING (the rest — every domain/review/process skill a strong cheap model
  already commands)
- 4 validated as the compose→verify pipeline family (via task 07)
- 1 structural (tierless-router)

Every testable skill has now had a full or screened deterministic measurement, and every candidate
gap has been confirmed ceiling by a hand-built + eye-verified cycle. The "are there more valuable
skills hiding in the library?" question is answered as thoroughly as this method allows: **no.** The
value is the 3 validated skills + the method.

## Reinforced methodological lesson
The auto-screen flagged 9 candidates; ALL 9 (2 prior + 7 here) confirmed ceiling. The screen's
keyword gaps were 100% false positives for gap MAGNITUDE — reliable only for the ceiling direction.
And within these cycles, keyword scoring again false-positived (database +2) until eye-verification
corrected it. Standing rule holds: deterministic keyword = screen; eye-verification = verdict.
