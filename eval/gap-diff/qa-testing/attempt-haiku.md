# Test Suite for `split_bill`

## 1. Happy-Path / Core Correctness

### TC-01: Simple even split, no tip
- **Input:** `split_bill(1000, 2)`
- **Expected:** `[500, 500]`

### TC-02: Simple even split, with tip
- **Input:** `split_bill(1000, 2, 10)`
- **Expected:** `tip = round(1000 * 10 / 100) = 100`, `grand = 1100`, `base = 550`, `remainder = 0`, result `[550, 550]`

### TC-03: Odd split with remainder distribution
- **Input:** `split_bill(1000, 3)`
- **Expected:** `base = 333`, `remainder = 1`, result `[334, 333, 333]` (first person gets the extra cent)

### TC-04: Remainder distributed to multiple people
- **Input:** `split_bill(1000, 7)`
- **Expected:** `base = 142`, `remainder = 6`, result `[143, 143, 143, 143, 143, 143, 142]`

### TC-05: Single person pays all
- **Input:** `split_bill(500, 1)`
- **Expected:** `[500]`

### TC-06: Single person with tip
- **Input:** `split_bill(500, 1, 20)`
- **Expected:** `tip = round(500 * 20 / 100) = 100`, `grand = 600`, result `[600]`

### TC-07: Large bill, many people, no remainder
- **Input:** `split_bill(10000, 5)`
- **Expected:** `[2000, 2000, 2000, 2000, 2000]`

### TC-08: Large bill, many people, with remainder
- **Input:** `split_bill(10000, 3)`
- **Expected:** `base = 3333`, `remainder = 1`, result `[3334, 3333, 3333]`

### TC-09: Tip causes remainder shift
- **Input:** `split_bill(100, 3, 10)`
- **Expected:** `tip = round(100 * 10 / 100) = 10`, `grand = 110`, `base = 36`, `remainder = 2`, result `[37, 37, 36]`

### TC-10: Sum of result always equals grand total
- **Input:** `split_bill(999, 7, 15)`
- **Expected:** `tip = round(999 * 15 / 100) = 150`, `grand = 1149`, `base = 164`, `remainder = 1`, result `[165, 164, 164, 164, 164, 164, 164]`, sum = 1149

---

## 2. Boundary Values

### TC-11: Zero total, no tip
- **Input:** `split_bill(0, 5)`
- **Expected:** `[0, 0, 0, 0, 0]`

### TC-12: Zero total with tip
- **Input:** `split_bill(0, 3, 20)`
- **Expected:** `tip = round(0 * 20 / 100) = 0`, `grand = 0`, result `[0, 0, 0]`

### TC-13: Minimum valid total (1 cent)
- **Input:** `split_bill(1, 1)`
- **Expected:** `[1]`

### TC-14: Minimum valid total split across people
- **Input:** `split_bill(1, 3)`
- **Expected:** `base = 0`, `remainder = 1`, result `[1, 0, 0]`

### TC-15: Total equals exactly one person's share
- **Input:** `split_bill(1, 1, 0)`
- **Expected:** `[1]`

### TC-16: Minimum valid num_people (1)
- **Input:** `split_bill(999, 1)`
- **Expected:** `[999]`

### TC-17: Minimum valid tip (0)
- **Input:** `split_bill(500, 2, 0)`
- **Expected:** `[250, 250]`

### TC-18: Very large total
- **Input:** `split_bill(999999999, 3)`
- **Expected:** `base = 333333333`, `remainder = 0`, result `[333333333, 333333333, 333333333]`

### TC-19: Very large total with tip
- **Input:** `split_bill(999999999, 3, 18)`
- **Expected:** `tip = round(999999999 * 18 / 100) = 1799999998`, `grand = 2799999997`, `base = 933333332`, `remainder = 1`, result `[933333333, 933333332, 933333332]`

### TC-20: Very large number of people
- **Input:** `split_bill(1000, 1000)`
- **Expected:** `base = 1`, `remainder = 0`, result = list of 1000 ones

### TC-21: More people than cents
- **Input:** `split_bill(5, 10)`
- **Expected:** `base = 0`, `remainder = 5`, result `[1, 1, 1, 1, 1, 0, 0, 0, 0, 0]`

### TC-22: Tip percent of 100 (double the bill)
- **Input:** `split_bill(100, 2, 100)`
- **Expected:** `tip = round(100 * 100 / 100) = 100`, `grand = 200`, result `[100, 100]`

### TC-23: Tip percent greater than 100
- **Input:** `split_bill(100, 3, 150)`
- **Expected:** `tip = round(100 * 150 / 100) = 150`, `grand = 250`, `base = 83`, `remainder = 1`, result `[84, 83, 83]`

---

## 3. Tip Calculation / Rounding Edge Cases

### TC-24: Tip rounds down (standard case)
- **Input:** `split_bill(100, 2, 15)`
- **Expected:** `tip = round(100 * 15 / 100) = 15`, `grand = 115`, `base = 57`, `remainder = 1`, result `[58, 57]`

### TC-25: Tip rounds down due to .5 rounding (banker's rounding or standard)
- **Input:** `split_bill(101, 2, 10)`
- **Expected:** `tip = round(101 * 10 / 100) = round(10.1) = 10`, `grand = 111`, `base = 55`, `remainder = 1`, result `[56, 55]`

### TC-26: Tip that produces exact .5 (Python round halves to even)
- **Input:** `split_bill(105, 2, 10)`
- **Expected:** `tip = round(105 * 10 / 100) = round(10.5) = 10` (Python banker's rounding: 10.5 rounds to 10), `grand = 115`, `base = 57`, `remainder = 1`, result `[58, 57]`

### TC-27: Tip that rounds up at .5 boundary
- **Input:** `split_bill(115, 2, 10)`
- **Expected:** `tip = round(115 * 10 / 100) = round(11.5) = 12` (Python banker's rounding: 11.5 rounds to 12), `grand = 127`, `base = 63`, `remainder = 1`, result `[64, 63]`

### TC-28: Small tip on small bill that rounds to zero
- **Input:** `split_bill(1, 1, 1)`
- **Expected:** `tip = round(1 * 1 / 100) = round(0.01) = 0`, `grand = 1`, result `[1]`

### TC-29: Tip percent that produces non-integer tip
- **Input:** `split_bill(7, 2, 15)`
- **Expected:** `tip = round(7 * 15 / 100) = round(1.05) = 1`, `grand = 8`, `base = 4`, `remainder = 0`, result `[4, 4]`

### TC-30: Tip percent of 1
- **Input:** `split_bill(100, 3, 1)`
- **Expected:** `tip = round(100 * 1 / 100) = 1`, `grand = 101`, `base = 33`, `remainder = 2`, result `[34, 34, 33]`

### TC-31: Tip percent of 0.5 (fractional tip)
- **Input:** `split_bill(100, 2, 0.5)`
- **Expected:** `tip = round(100 * 0.5 / 100) = round(0.5) = 0` (Python banker's rounding), `grand = 100`, result `[50, 50]`

### TC-32: Tip percent of 33 (repeating decimal)
- **Input:** `split_bill(100, 3, 33)`
- **Expected:** `tip = round(100 * 33 / 100) = round(33.0) = 33`, `grand = 133`, `base = 44`, `remainder = 1`, result `[45, 44, 44]`

### TC-33: Tip percent of 33.33 (repeating decimal)
- **Input:** `split_bill(100, 3, 33.33)`
- **Expected:** `tip = round(100 * 33.33 / 100) = round(33.33) = 33`, `grand = 133`, `base = 44`, `remainder = 1`, result `[45, 44, 44]`

---

## 4. Error / Validation Cases

### TC-34: num_people = 0
- **Input:** `split_bill(100, 0)`
- **Expected:** Raises `ValueError("num_people must be positive")`

### TC-35: num_people = -1 (negative)
- **Input:** `split_bill(100, -1)`
- **Expected:** Raises `ValueError("num_people must be positive")`

### TC-36: num_people = -100 (large negative)
- **Input:** `split_bill(100, -100)`
- **Expected:** Raises `ValueError("num_people must be positive")`

### TC-37: total_cents = -1 (negative total)
- **Input:** `split_bill(-1, 2)`
- **Expected:** Raises `ValueError("total must be non-negative")`

### TC-38: total_cents = -1000 (large negative)
- **Input:** `split_bill(-1000, 3)`
- **Expected:** Raises `ValueError("total must be non-negative")`

### TC-39: tip_percent = -1 (negative tip)
- **Input:** `split_bill(100, 2, -1)`
- **Expected:** Raises `ValueError("tip must be non-negative")`

### TC-40: tip_percent = -100 (large negative tip)
- **Input:** `split_bill(100, 2, -100)`
- **Expected:** Raises `ValueError("tip must be non-negative")`

### TC-41: All parameters invalid (num_people=0, total=-1, tip=-1)
- **Input:** `split_bill(-1, 0, -1)`
- **Expected:** Raises `ValueError` — the first check that fires is `num_people <= 0`, so `ValueError("num_people must be positive")`

---

## 5. Type / Input Shape Edge Cases

### TC-42: Float total_cents
- **Input:** `split_bill(100.5, 2)`
- **Expected:** `grand = 100 // 2 = 50` (Python `//` on float returns float), result `[50.0, 50.0]` — returns floats, not ints. This is a potential bug: the docstring says "integer cents" but float input produces float output.

### TC-43: Float num_people (valid integer-valued float)
- **Input:** `split_bill(100, 2.0)`
- **Expected:** `base = 100 // 2.0 = 50.0`, result `[50.0, 50.0]` — same float output issue.

### TC-44: Float num_people (non-integer)
- **Input:** `split_bill(100, 2.5)`
- **Expected:** `base = 100 // 2.5 = 40.0`, `remainder = 100 % 2.5 = 0.0`, result `[40.0]` — only 4 elements produced (int(2.5) = 2, but `range(2.5)` raises TypeError). Actually `range(2.5)` raises `TypeError`. This is a crash / unhandled input type.

### TC-45: Float tip_percent
- **Input:** `split_bill(100, 2, 12.5)`
- **Expected:** `tip = round(100 * 12.5 / 100) = round(12.5) = 12` (banker's rounding), `grand = 112`, result `[56, 56]` — works but produces float tip if not careful.

### TC-46: String total_cents
- **Input:** `split_bill("100", 2)`
- **Expected:** `total_cents < 0` comparison with string raises `TypeError`. Crash.

### TC-47: String num_people
- **Input:** `split_bill(100, "2")`
- **Expected:** `num_people <= 0` comparison with string raises `TypeError`. Crash.

### TC-48: None as num_people
- **Input:** `split_bill(100, None)`
- **Expected:** `num_people <= 0` raises `TypeError`. Crash.

### TC-49: Empty list as num_people
- **Input:** `split_bill(100, [])`
- **Expected:** `[] <= 0` raises `TypeError`. Crash.

### TC-50: Boolean num_people (True = 1)
- **Input:** `split_bill(100, True)`
- **Expected:** `True` is `1` in Python, so `base = 100 // 1 = 100`, result `[100]` — works but may be unintended.

### TC-51: Boolean num_people (False = 0)
- **Input:** `split_bill(100, False)`
- **Expected:** `False` is `0`, so `num_people <= 0` is True, raises `ValueError("num_people must be positive")`

---

## 6. Distribution / Remainder Logic

### TC-52: Remainder equals num_people (all get +1)
- **Input:** `split_bill(1000, 5)`
- **Expected:** `base = 200`, `remainder = 0`, result `[200, 200, 200, 200, 200]` — no remainder case, all equal.

### TC-53: Remainder = num_people - 1
- **Input:** `split_bill(1000, 5)`
- **Expected:** `base = 200`, `remainder = 0` — this is even. Let me pick differently: `split_bill(1002, 5)` gives `base = 200`, `remainder = 2`. Result `[201, 201, 200, 200, 200]`.

### TC-54: Remainder = 1 (single extra cent)
- **Input:** `split_bill(1001, 5)`
- **Expected:** `base = 200`, `remainder = 1`, result `[201, 200, 200, 200, 200]`

### TC-55: Remainder = num_people (grand is multiple of num_people)
- **Input:** `split_bill(1000, 4)`
- **Expected:** `base = 250`, `remainder = 0`, result `[250, 250, 250, 250]`

### TC-56: Verify first `remainder` people get +1, rest get base
- **Input:** `split_bill(100, 5)`
- **Expected:** `base = 20`, `remainder = 0`, result `[20, 20, 20, 20, 20]` — even split.

### TC-57: Verify distribution order with remainder
- **Input:** `split_bill(103, 5)`
- **Expected:** `base = 20`, `remainder = 3`, result `[21, 21, 21, 20, 20]` — first 3 get +1

### TC-58: All people get +1 (remainder == num_people, but grand not multiple)
- **Input:** `split_bill(105, 5)`
- **Expected:** `base = 21`, `remainder = 0`, result `[21, 21, 21, 21, 21]` — actually even. Let me use `split_bill(104, 5)`: `base = 20`, `remainder = 4`, result `[21, 21, 21, 21, 20]`

---

## 7. Consistency / Invariant Checks

### TC-59: Sum invariant — result sum always equals grand total
- **Input:** `split_bill(12345, 7, 13)`
- **Expected:** `tip = round(12345 * 13 / 100) = round(1604.85) = 1605`, `grand = 13950`, result sum = 13950

### TC-60: All values are base or base+1
- **Input:** `split_bill(99999, 13, 5)`
- **Expected:** `tip = round(99999 * 5 / 100) = round(4999.95) = 5000`, `grand = 104999`, `base = 8076`, `remainder = 11`, result has 11 entries of 8077 and 2 entries of 8076. All values are either 8076 or 8077.

### TC-61: Count of base+1 entries equals remainder
- **Input:** `split_bill(500, 8, 10)`
- **Expected:** `tip = round(500 * 10 / 100) = 50`, `grand = 550`, `base = 68`, `remainder = 6`, result has exactly 6 entries of 69 and 2 entries of 68.

### TC-62: Result length equals num_people
- **Input:** `split_bill(100, 10)`
- **Expected:** Result is a list of length 10

### TC-63: Result is always a list (not tuple or other type)
- **Input:** `split_bill(100, 2)`
- **Expected:** `type(result) is list`

### TC-64: All result elements are non-negative
- **Input:** `split_bill(0, 5)`
- **Expected:** `[0, 0, 0, 0, 0]` — all zero, non-negative

---

## 8. Floating-Point Tip Edge Cases

### TC-65: Tip with floating-point precision issue
- **Input:** `split_bill(10, 3, 33.333333)`
- **Expected:** `tip = round(10 * 33.333333 / 100) = round(3.3333333) = 3`, `grand = 13`, `base = 4`, `remainder = 1`, result `[5, 4, 4]`

### TC-66: Very small tip that rounds to zero
- **Input:** `split_bill(1, 1, 0.01)`
- **Expected:** `tip = round(1 * 0.01 / 100) = round(0.0001) = 0`, `grand = 1`, result `[1]`

### TC-67: Tip percent as float with many decimal places
- **Input:** `split_bill(1000, 3, 16.666666666666668)`
- **Expected:** `tip = round(1000 * 16.666666666666668 / 100) = round(166.66666666666669) = 167`, `grand = 1167`, `base = 389`, `remainder = 0`, result `[389, 389, 389]`

---

## 9. Large-Scale / Stress Cases

### TC-68: Maximum reasonable num_people
- **Input:** `split_bill(1000000, 100000)`
- **Expected:** `base = 10`, `remainder = 0`, result = list of 100000 tens

### TC-69: Large total, small num_people, large tip
- **Input:** `split_bill(1000000, 2, 50)`
- **Expected:** `tip = round(1000000 * 50 / 100) = 500000`, `grand = 1500000`, result `[750000, 750000]`

### TC-70: Large total, large tip, odd split
- **Input:** `split_bill(1000000, 3, 25)`
- **Expected:** `tip = round(1000000 * 25 / 100) = 250000`, `grand = 1250000`, `base = 416666`, `remainder = 2`, result `[416667, 416667, 416666]`

---

## 10. Docstring Contract Verification

### TC-71: Return type is list of integers (when all inputs are integers)
- **Input:** `split_bill(100, 3)`
- **Expected:** `all(isinstance(x, int) for x in result)` is True. Result `[34, 33, 33]` — all ints.

### TC-72: Docstring says "Raises ValueError for invalid input" — verify all three validation branches
- **Input:** `split_bill(100, -1, 10)` → `split_bill(-1, 1, 10)` → `split_bill(100, 1, -1)`
- **Expected:** Each raises `ValueError` with the specific message from the docstring.

### TC-73: Docstring says "distributing any remainder cents to the first people"
- **Input:** `split_bill(100, 4)`
- **Expected:** `base = 25`, `remainder = 0`, result `[25, 25, 25, 25]` — no remainder to distribute.
- **Input:** `split_bill(101, 4)`
- **Expected:** `base = 25`, `remainder = 1`, result `[26, 25, 25, 25]` — first person gets the extra cent.

### TC-74: Docstring says "totals always add up exactly"
- **Input:** `split_bill(1, 1000000, 99)`
- **Expected:** `tip = round(1 * 99 / 100) = 1`, `grand = 2`, `base = 0`, `remainder = 2`, result = list of 1000000 elements: first 2 are 1, rest are 0. Sum = 2 = grand.

---

## Summary

| Category | Count | Description |
|---|---|---|
| Happy-Path / Core Correctness | TC-01 to TC-10 | Basic splits, tips, remainder distribution |
| Boundary Values | TC-11 to TC-23 | Zero, one, minimum, maximum, edge magnitudes |
| Tip Calculation / Rounding | TC-24 to TC-33 | Python banker's rounding, fractional tips, edge rounding |
| Error / Validation | TC-34 to TC-41 | All three ValueError branches, order of validation |
| Type / Input Shape | TC-42 to TC-51 | Floats, strings, None, booleans, type coercion |
| Distribution / Remainder Logic | TC-52 to TC-58 | Remainder edge cases, distribution order |
| Consistency / Invariants | TC-59 to TC-64 | Sum invariant, value range, type, length |
| Floating-Point Tip Edge Cases | TC-65 to TC-67 | Precision, tiny tips, repeating decimals |
| Large-Scale / Stress | TC-68 to TC-70 | Large numbers, many people |
| Docstring Contract Verification | TC-71 to TC-74 | Return type, error messages, docstring claims |

**Total test cases: 74**