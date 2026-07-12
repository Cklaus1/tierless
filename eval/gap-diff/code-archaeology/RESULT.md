# code-archaeology → constant-coupling: full gap-diff cycle (2026-07-12)

Second full validated gap-diff cycle (after spec-review). Method: measure gap → diff for process →
distill skill → re-test → deterministic + eye-verified score.

## The cycle
1. **Gap established** (deterministic, prior step): on a "make the hardcoded retry count 3
   configurable — what would you need to understand first?" task, bare Haiku scored 9/12, Fable
   12/12. The 3 misses were all DISGUISED couplings of the constant.
2. **Diffed for process**: the 3 catches share one root — Haiku searched for the constant's *token*,
   Fable searched for the *value's consequences*. Extracted 5 repeatable "hunts."
3. **Distilled** → `constant-coupling.md` skill. Rule: *a hardcoded constant is rarely defined once;
   find each copy by its consequence, not its spelling.* Five hunts: algebraic aliases (off-by-one
   shadows), trace-the-induction-variable, closed-form-the-break-point, provenance-as-contract,
   degenerate-value substitution.
4. **Re-test**: Haiku + the skill, same task.

## Result (deterministic keyword + eye-verified)

| item | bare Haiku | Haiku+skill | Fable |
|---|---|---|---|
| total /12 | **9** | **12** | 12 |

The 3 previously-missed items, all now caught AND eye-verified as genuine (not terminology echo):
- **#2 `attempt == 2` disguised constant** — Haiku+skill: "a disguised declaration of N... correct
  only because range(3) produces 0,1,2. If N changes to 5 it fires on the third attempt, emitting a
  premature failure event while two more retries remain. Must become `attempt == retries - 1`."
  This is the ACTUAL BUG the requested change would introduce — bare Haiku missed it entirely.
- **#6 timeout scaling** — "at N=3 max is 30s; at N=10 it's 100s; the ceiling is an accident of N."
- **#12 provenance** — ran the provenance hunt as its own section, flagged the TTL as possible
  external contract.

Haiku+skill literally ran the five hunts as named sections. The discipline transferred cleanly.

## Verdict
**Second empirically-derived, validated skill. The gap-diff method works twice.**
- spec-review: Haiku 8/15 → 13/15 (closed ~70% of gap to frontier)
- constant-coupling: Haiku 9/12 → 12/12 (closed 100% of gap to frontier)

Both were "derive the non-obvious" gaps (LESSONS #20) — the class where skills measurably help.
Two independent successes make "gap-diff produces working skills" a pattern, not a fluke. And both
were validated by deterministic scoring + eye verification, never an LLM judge.

## Note on scope
`constant-coupling` is a focused companion to `code-archaeology` (it targets the changing-a-constant
case specifically). Whether to keep it standalone or fold the five hunts into code-archaeology as a
sub-section is a librarianship call; the DISCIPLINE is validated either way.
