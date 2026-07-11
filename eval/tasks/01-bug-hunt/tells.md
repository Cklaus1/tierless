# GRADER-ONLY — Task 01 tells

## The trap
The symptom ("total lower than sum of items") pulls attention toward the discount
line or the loyalty-points cap — those are where money visibly leaves the total.
The undisciplined move is to "fix" one of those (add a guard to loyalty, tweak the
discount). But those are correct. The actual root cause is in `total_cents`:

```python
discounted = subtotal * (1 - self._discount_rate)   # float arithmetic on money
return round(discounted)                              # banker's rounding, half-to-even
```

Two compounding real defects:
1. **`round()` uses banker's rounding** (round-half-to-even): 2.5 → 2, 0.5 → 0.
   Half-cent values round DOWN as often as up → systematically lower totals.
2. **Float arithmetic on money**: `subtotal * (1 - 0.10)` introduces representation
   error (e.g. 0.1 is not exact), so values land just under .5 and round down.

The money is already in integer cents *until* this function multiplies by a float.

## Tells (binary)
- **T1 — locates the real site**: names `total_cents` / the `round(discounted)` line
  as the cause, NOT the discount logic, loyalty cap, or `line_total_cents`. (A fix
  applied to loyalty/discount is an automatic MISS on T1 even if totals change.)
- **T2 — names the mechanism**: identifies banker's rounding (round-half-to-even)
  AND/OR float imprecision on monetary math as the why. Must name at least one
  specifically; "rounding is off" without the mechanism is PARTIAL.
- **T3 — root fix**: fixes by keeping money in integer cents / using Decimal /
  round-half-up with explicit rounding — not by nudging a different line or adding
  a fudge. The fix must make the half-cent case deterministic and not-downward.
- **T4 — reproduction before fix**: constructs or describes a concrete cart that
  triggers it (e.g. odd subtotal + 10% discount landing on a half cent) rather than
  editing code speculatively. Disciplined arms should show the repro.

## Skill lineage
debugging (reproduce-before-fix, root not symptom), database-design/naming are N/A.
Expected: C hits T1–T3 often, T4 sometimes. A often misses T1 (fixes wrong site).
B should gain T1 and T4 specifically if `debugging` is doing its job.
