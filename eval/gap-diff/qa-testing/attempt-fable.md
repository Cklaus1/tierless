# Test suite design for `split_bill(total_cents, num_people, tip_percent=0)`

## Contract under test

From the signature + docstring + code, the promised behavior is:

1. Returns a list of length `num_people` of integer cent amounts.
2. `sum(result) == total_cents + round(total_cents * tip_percent / 100)` — the sum always
   equals the grand total exactly (no lost/created cents).
3. Remainder cents go to the *first* people: amounts are non-increasing, and
   `max(result) - min(result) <= 1`.
4. Raises `ValueError` for `num_people <= 0`, `total_cents < 0`, `tip_percent < 0`.

The tests below are grouped by behavior. Each case gives **input → expected result** and, where
useful, the rationale. Cases marked *(documents current behavior / spec question)* probe behavior
the docstring doesn't pin down — they should be written after deciding what the spec is, and are
exactly the cases most likely to expose latent bugs.

---

## 1. Input validation (failure modes)

| # | Input | Expected |
|---|-------|----------|
| 1.1 | `split_bill(100, 0)` | `ValueError("num_people must be positive")` |
| 1.2 | `split_bill(100, -1)` | `ValueError` (num_people) |
| 1.3 | `split_bill(100, -1000000)` | `ValueError` (num_people) — large negative, not just -1 |
| 1.4 | `split_bill(-1, 2)` | `ValueError("total must be non-negative")` |
| 1.5 | `split_bill(-100, 2)` | `ValueError` (total) |
| 1.6 | `split_bill(100, 2, -1)` | `ValueError("tip must be non-negative")` |
| 1.7 | `split_bill(100, 2, -0.5)` | `ValueError` (tip) — fractional negative tip also rejected |
| 1.8 | `split_bill(-1, 0, -1)` | `ValueError` with the **num_people** message — validation order: num_people is checked first, then total, then tip. Add a companion case `split_bill(-1, 2, -1)` → the **total** message. Pin the order only if callers rely on it; otherwise just assert `ValueError`. |
| 1.9 | Boundary values that must **not** raise: `split_bill(0, 1)`, `split_bill(100, 1)`, `split_bill(100, 2, 0)` | No exception; sensible results (see below) |
| 1.10 | `split_bill(100, 2, -0.0)` | `-0.0 < 0` is False → does **not** raise; behaves as 0 tip → `[50, 50]`. *(documents current behavior)* |

## 2. Exact division — no remainder, no tip

| # | Input | Expected |
|---|-------|----------|
| 2.1 | `split_bill(1000, 4)` | `[250, 250, 250, 250]` |
| 2.2 | `split_bill(100, 1)` | `[100]` — single person gets everything |
| 2.3 | `split_bill(0, 1)` | `[0]` — zero bill |
| 2.4 | `split_bill(0, 5)` | `[0, 0, 0, 0, 0]` — zero bill, many people |
| 2.5 | `split_bill(1, 1)` | `[1]` — smallest nonzero bill |
| 2.6 | `split_bill(7, 7)` | `[1, 1, 1, 1, 1, 1, 1]` — total == num_people |

## 3. Remainder distribution (core rounding logic)

| # | Input | Expected | Rationale |
|---|-------|----------|-----------|
| 3.1 | `split_bill(100, 3)` | `[34, 33, 33]` | classic 1-cent remainder; sum = 100 |
| 3.2 | `split_bill(101, 2)` | `[51, 50]` | remainder 1 goes to the first person |
| 3.3 | `split_bill(5, 3)` | `[2, 2, 1]` | remainder 2 → first two people |
| 3.4 | `split_bill(99, 4)` | `[25, 25, 25, 24]` | remainder = num_people − 1 (max remainder) |
| 3.5 | `split_bill(1, 3)` | `[1, 0, 0]` | total < num_people: some people pay 0 |
| 3.6 | `split_bill(2, 5)` | `[1, 1, 0, 0, 0]` | total < num_people, remainder > 1 |
| 3.7 | `split_bill(0, 3)` | `[0, 0, 0]` | zero grand total with multiple people |
| 3.8 | Ordering assertion for all of the above | list is non-increasing, `max - min <= 1` | "first people" get the extra cents — first elements never smaller than later ones |

## 4. Tip calculation — clean cases

| # | Input | Expected | Rationale |
|---|-------|----------|-----------|
| 4.1 | `split_bill(1000, 2, 20)` | `[600, 600]` | tip = 200, grand = 1200, even split |
| 4.2 | `split_bill(1000, 4, 0)` | `[250, 250, 250, 250]` | explicit 0 tip == default |
| 4.3 | `split_bill(1000, 4)` vs `split_bill(1000, 4, 0)` | identical results | default parameter check |
| 4.4 | `split_bill(100, 3, 15)` | `[39, 38, 38]` | tip 15 → grand 115; tip interacts with remainder logic |
| 4.5 | `split_bill(1000, 3, 18)` | `[394, 393, 393]` | tip 180 → grand 1180 = 393·3 + 1 |
| 4.6 | `split_bill(200, 2, 100)` | `[200, 200]` | 100% tip |
| 4.7 | `split_bill(100, 2, 250)` | `[175, 175]` | tip > 100% is allowed (no upper bound in spec) |
| 4.8 | `split_bill(0, 3, 20)` | `[0, 0, 0]` | tip on zero total is zero |
| 4.9 | `split_bill(1000, 2, 12.5)` | tip = round(125.0) = 125 → grand 1125 → `[563, 562]` | fractional tip percent, exact product |

## 5. Tip rounding — `round()` semantics (highest-risk area)

`tip = round(total_cents * tip_percent / 100)` uses float division and Python's
**banker's rounding** (round-half-to-even). Tests must pin this down or drive a spec change.

| # | Input | Computation | Expected *(documents current behavior)* |
|---|-------|-------------|------------------------------------------|
| 5.1 | `split_bill(50, 1, 1)` | 50·1/100 = 0.5 → round → **0** | `[50]` — half rounds *down* to even 0 |
| 5.2 | `split_bill(150, 1, 1)` | 150·1/100 = 1.5 → round → **2** | `[152]` — half rounds *up* to even 2 |
| 5.3 | `split_bill(250, 1, 1)` | 2.5 → round → **2** | `[252]` — 2.5 rounds down; note 5.1/5.2/5.3 together prove half-to-even, not half-up. If the business rule is "round half up," these tests fail and expose the bug. |
| 5.4 | `split_bill(125, 1, 10)` | 12.5 → **12** | `[137]` |
| 5.5 | `split_bill(135, 1, 10)` | 13.5 → **14** | `[149]` |
| 5.6 | Float representation hazard: `split_bill(2675, 1, 1)` | 2675/100 = 26.75 exactly? No — 26.75 is representable, but products like `total_cents * tip_percent / 100` can land on values such as 26.749999…; assert the actual computed tip | pin actual output; this is a canary test for float artifacts |
| 5.7 | Tip that itself is not an integer number of cents before rounding: `split_bill(333, 3, 15)` | 333·15/100 = 49.95 → 50 → grand 383 | `[128, 128, 127]` |
| 5.8 | Non-representable fractional percent: `split_bill(1000, 3, 0.1)` | 1000·0.1/100 = 1.0000000000000002 or 1.0 (assert) → tip 1 → grand 1001 | `[334, 334, 333]` — checks float noise doesn't change the rounded tip |

## 6. Invariant / property-based tests

Run over a broad randomized or exhaustive grid (e.g., `total_cents` 0–10 000,
`num_people` 1–50, `tip_percent` ∈ {0, 5, 10, 12.5, 15, 18, 20, 33, 100, 250}):

| # | Property |
|---|----------|
| 6.1 | `len(result) == num_people` |
| 6.2 | `sum(result) == total_cents + round(total_cents * tip_percent / 100)` — **the headline guarantee: no cent is ever lost or created** |
| 6.3 | All elements are `int` (type check, not just value check) |
| 6.4 | All elements ≥ 0 (given valid inputs) |
| 6.5 | `max(result) - min(result) <= 1` — fairness: no one pays more than 1 cent above anyone else |
| 6.6 | Result is non-increasing (extra cents go to earliest indices) |
| 6.7 | Exactly `grand % num_people` people pay the higher amount |
| 6.8 | Monotonicity sanity: with tip fixed, increasing `total_cents` by 1 never decreases `sum(result)`; per-person amounts change by at most the expected delta *(optional, catches gross regressions)* |

## 7. Scale / extreme-magnitude cases

| # | Input | Expected | Rationale |
|---|-------|----------|-----------|
| 7.1 | `split_bill(10**9, 7, 18)` | sum invariant holds; values ≈ 168 571 428 each | large realistic-ish bill |
| 7.2 | `split_bill(3, 1000)` | `[1, 1, 1] + [0]*997` | num_people ≫ total |
| 7.3 | `split_bill(0, 10**6)` | list of one million zeros | very large num_people (also a mild performance test — O(n) list build) |
| 7.4 | **Float-precision overflow bug probe:** `split_bill(10**17 + 1, 1, 100)` | Ideal tip is exactly `10**17 + 1`, but `(10**17+1) * 100 / 100` is float division: the intermediate exceeds 2^53, so `round()` returns a value off by ±(up to hundreds) of cents. Assert `sum(result) == 2*(10**17 + 1)` — **expected to FAIL against current implementation**, exposing that tip should be computed with integer/Decimal arithmetic (e.g., `round(Decimal(total_cents) * Decimal(str(tip_percent)) / 100)`). | precision failure mode |
| 7.5 | `split_bill(2**53 + 1, 2, 0)` | `[4503599627370497, 4503599627370496]` | no tip path is pure int arithmetic — must stay exact even beyond float precision (contrast with 7.4) |

## 8. Argument-type edge cases *(documents current behavior / spec questions)*

The signature says "cents" (implying `int`) but nothing enforces types. Decide the spec, then
keep whichever branch of each test matches it.

| # | Input | Current behavior | Note |
|---|-------|------------------|------|
| 8.1 | `split_bill(100.5, 2)` | No error; `grand = 100.5`, floor-div yields **floats** → `[51.0, 50.0]` (sum 101.0 ≠ 100.5!) — violates both "integer cents" and the sum invariant | strong candidate for adding an `isinstance(total_cents, int)` check; test should assert the chosen behavior (reject vs. current) |
| 8.2 | `split_bill(100.0, 2)` | `[50.0, 50.0]` — floats, not ints | same spec question with a "harmless" float |
| 8.3 | `split_bill(100, 2.5)` | Passes `num_people <= 0`, then `range(2.5)` raises **TypeError** (not ValueError) | inconsistent error type for invalid input — decide whether non-int num_people should be `ValueError` |
| 8.4 | `split_bill(100, 2.0)` | Also `TypeError` from `range(2.0)` — even a whole-number float fails | |
| 8.5 | `split_bill(100, True)` | `True <= 0` is False; `range(True)` works → `[100]` (bool is int) | probably acceptable but worth pinning |
| 8.6 | `split_bill(True, 2)` / `split_bill(100, 2, True)` | Treated as 1 cent / 1% | pin or reject |
| 8.7 | `split_bill(None, 2)`, `split_bill("100", 2)`, `split_bill(100, "2")`, `split_bill(100, 2, "10")` | `TypeError` from the comparison operators | assert TypeError raised (and consider whether a friendlier error is wanted) |
| 8.8 | `split_bill(Decimal("100"), 4, Decimal("10"))` | Works; tip = round(Decimal) → int-ish; result `[28, 28, 27, 27]`? — assert actual output | Decimal interop: mixed Decimal/float would raise in the tip expression (`Decimal * float` is fine only via `/100` int); pin behavior |
| 8.9 | `split_bill(Fraction(101, 1), 2)` | Works, returns Fractions or ints — pin | exotic numeric types |
| 8.10 | `split_bill(float('nan'), 2)` | NaN comparisons are False → passes validation; `nan // 2` = nan → `[nan+..., ...]` garbage output, no error | NaN silently produces nonsense — argument for explicit type/finite checks. Same probe with `float('inf')` (returns `[inf, inf]`) and `tip_percent=float('nan')` (tip becomes nan → garbage). |

## 9. Return-value hygiene

| # | Check |
|---|-------|
| 9.1 | Return type is exactly `list` (not generator/tuple) |
| 9.2 | Two calls with the same arguments return equal but **distinct** list objects (no shared mutable state); function is pure — inputs unmodified, no globals touched |
| 9.3 | Element types are `int` for all valid-int-input cases (guards against a refactor introducing float division) |

## 10. Regression-oriented "seam" cases

Small table of exact expected outputs to lock the algorithm down (cheap to maintain, catches
off-by-one refactors in the remainder loop):

| Input | Expected |
|-------|----------|
| `(1, 1)` | `[1]` |
| `(1, 2)` | `[1, 0]` |
| `(2, 2)` | `[1, 1]` |
| `(3, 2)` | `[2, 1]` |
| `(10, 3)` | `[4, 3, 3]` |
| `(11, 3)` | `[4, 4, 3]` |
| `(12, 3)` | `[4, 4, 4]` |
| `(10, 4, 10)` | tip = round(1.0) = 1 → grand 11 → `[3, 3, 3, 2]` |
| `(1, 1, 49)` | tip = round(0.49) = 0 → `[1]` |
| `(1, 1, 50)` | tip = round(0.5) = 0 (half-even) → `[1]` |
| `(1, 1, 51)` | tip = round(0.51) = 1 → `[2]` |
| `(3, 1, 50)` | tip = round(1.5) = 2 → `[5]` |

---

## Summary of likely defects these tests will surface

1. **Banker's rounding on the tip** (§5): `round()` half-to-even is almost never the intended
   business rule for gratuities; 5.1–5.5 make the behavior visible so it can be accepted or fixed.
2. **Float precision in the tip expression** (§5.6, §5.8, §7.4): `total * pct / 100` goes through
   binary floating point; for large totals or awkward percentages the tip can be off by a cent or
   more, and for totals beyond 2^53 the sum invariant breaks outright.
3. **No type enforcement** (§8): float `total_cents` silently returns non-integer amounts whose
   sum does not equal the input (8.1); non-int `num_people` raises `TypeError` instead of the
   documented `ValueError` (8.3–8.4); NaN/inf pass validation and yield garbage (8.10).
4. **Error-type inconsistency**: the docstring promises `ValueError` for invalid input, but several
   invalid inputs produce `TypeError` or no error at all — the validation tests in §1 plus §8 map
   that boundary precisely.
