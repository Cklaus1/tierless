# Bug Hunt Debug Log

## Hypothesis 1
**Hypothesis:** Python's built-in `round()` uses banker's rounding (round half to even), but financial calculations require round half up. This causes the cart total to be 1 cent lower whenever the discounted value lands exactly on a `.5` cent boundary.

**Prediction:** If true, then any cart where `subtotal * (1 - discount_rate)` ends in `.5` cents will show a total 1 cent lower than expected. This is intermittent because it only happens on specific subtotal/discount combinations.

**Test:** Verified by comparing `round(float_value)` against `Decimal(value).to_integral_value(ROUND_HALF_UP)` across multiple subtotal/discount combinations. All mismatches were exactly 1 cent, and all occurred at `.5` boundaries. The float computation itself was exact (diff=0.0), confirming the issue is purely the rounding mode, not floating-point precision.

**Result:** CONFIRMED.

## Root Cause
Python's `round()` implements IEEE 754 "round half to even" (banker's rounding). Financial/monetary calculations require "round half up" (standard commercial rounding). When a discounted cart total lands exactly on a half-cent boundary (e.g., 166.5 cents), `round(166.5)` returns 166 (the even number) instead of 167 (round half up), causing the customer to see a total 1 cent lower than expected.

## Fix
Replace `round(discounted)` with `int(Decimal(str(discounted)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))` to use proper commercial rounding.

## Regression Test
Add a test case where `subtotal=333`, `discount_rate=0.5` (50% off). The correct total is 167 cents (333 * 0.5 = 166.5, round half up = 167). The buggy code returns 166.