# QA test design

Here is a function. Design a thorough test suite for it — enumerate the test cases you would
write (you don't need to write the test code, just specify each case: the input/scenario and the
expected result). Aim for complete coverage of the behavior, including edge cases and failure modes.

```python
def split_bill(total_cents, num_people, tip_percent=0):
    """Split a bill evenly. Returns a list of per-person amounts in integer cents whose sum
    equals total_cents + tip, distributing any remainder cents to the first people so the
    totals always add up exactly. Raises ValueError for invalid input."""
    if num_people <= 0:
        raise ValueError("num_people must be positive")
    if total_cents < 0:
        raise ValueError("total must be non-negative")
    if tip_percent < 0:
        raise ValueError("tip must be non-negative")
    tip = round(total_cents * tip_percent / 100)
    grand = total_cents + tip
    base = grand // num_people
    remainder = grand % num_people
    return [base + (1 if i < remainder else 0) for i in range(num_people)]
```
