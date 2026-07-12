# Full cycles: version-control + compiler-building → both CEILING (2026-07-12)

The full-coverage screen flagged these as the two biggest gap CANDIDATES (version-control +3,
compiler-building +5 on auto-generated checklists). Ran the full deterministic cycle on both —
hand-built task with PLANTED TRAPS + hand-built checklist + eye-verification.

## version-control (task: turn a tangled working tree into commits; 4 planted traps)
Keyword: Haiku 12/14, Fable 13/14 (+1). **Eye-verified: CEILING.**
Bare Haiku caught ALL four discriminating traps:
- the missed `refresh.py` call still using the old name (the incomplete-rename bug) — 4 mentions
- the stale `docs/auth.md` code example — caught
- the unrelated cryptography bump needing its own commit — caught
- the 2MB `scratch/debug_dump.json` junk file (don't commit / gitignore) — caught
Its two keyword "misses" (#1 atomic-commits phrasing, #14 session.py two-concerns) were paraphrase
artifacts — it separated the bugfix/rename/format/dep into distinct commits explicitly.

## compiler-building (task: review an interpreter with planted defects)
Keyword: Haiku 12/15, Fable 14/15 (+2). **Eye-verified: CEILING.**
Bare Haiku caught the code-specific traps, including the subtle ones:
- #1 the NAME/variable eval crash (`env` never read, `float()` on a name) — 10 mentions
- #2 the DEAD `<` grammar rule — never actually parsed — 12 mentions (this was THE subtle trap)
- #5 missing close-paren not checked, #7 trailing tokens accepted — caught
Its keyword "misses" were #13 (precedence — actually discussed, paraphrased) and #15 (recursion-depth
/ stack overflow — a genuinely minor gap, not a discriminating trap).

## Conclusion
**Both are ceiling. No skill to build for either.** The screening's +3/+5 gaps were INFLATED by the
auto-generated checklists (generic keyword items that Haiku expressed in different words). Under a
hand-built checklist with real planted traps + eye-verification, bare Haiku traced the code/status and
found the actual bugs — matching Fable.

## The methodological lesson (important for the coverage map)
The full-coverage SCREEN (auto-generated checklist, no eye-verify) OVER-ESTIMATED these gaps by 2-3x.
This means the OTHER 7 screened "gap candidates" (database-design, infra-ops, code-migration,
requirements-elicitation, security-review, systems-programming, tech-doc) are probably ALSO inflated —
their true gaps are likely 0-1 (ceiling), not the +2/+3 the screen reported. The screen is reliable
for CEILING verdicts but systematically inflates candidate gaps. To confirm any candidate needs the
full hand-built-checklist + eye-verified cycle — and the first two we ran both collapsed to ceiling.
Prior: the remaining candidates are ceiling too; the validated-gap set stays at 3 (build-loop,
spec-review, constant-coupling).
