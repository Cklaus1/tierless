# Implement: a recurring-schedule expander

Write a Python function with EXACTLY this signature:

```python
def expand_occurrences(start_iso: str, rule: dict, range_start_iso: str, range_end_iso: str) -> list[str]:
    ...
```

It expands a recurring event into the list of occurrence datetimes (as ISO-8601 strings) that fall
within a query window `[range_start_iso, range_end_iso)` (half-open: include start, exclude end).

- `start_iso`: the first occurrence, an ISO-8601 datetime, possibly timezone-aware (e.g.
  `"2026-03-01T09:00:00-05:00"`).
- `rule`: `{"freq": "daily"|"weekly"|"monthly", "interval": int, "count": int | None}`.
  - `interval` = every N periods (interval=2 weekly = every other week).
  - `count` = total number of occurrences the series has (including the first); if `None`, the
    series is unbounded.
- Return occurrences within the window, in ascending order, as ISO strings in the SAME offset/format
  as `start_iso`.

Requirements / edge cases you must handle correctly:
1. Half-open window: an occurrence exactly at `range_end` is EXCLUDED; exactly at `range_start` is INCLUDED.
2. `count` bounds the series even if the window would contain more (don't emit past the Nth occurrence).
3. `monthly` must handle **day-of-month overflow**: a series starting Jan 31, monthly, should produce
   the last valid day for short months is NOT required — instead, months without that day are SKIPPED
   (Jan 31 → Mar 31 → May 31 ...; Feb and Apr are skipped). Match this rule exactly.
4. Timezone-aware inputs: preserve the offset; do arithmetic on aware datetimes (a DST-shifting local
   zone is out of scope — offsets are fixed, e.g. `-05:00`).
5. If the window is entirely before the series start or after it ends, return `[]`.
6. Unbounded series (`count=None`) must still terminate — bounded by the window.

Return only the function (plus imports). It will be imported and called directly.
