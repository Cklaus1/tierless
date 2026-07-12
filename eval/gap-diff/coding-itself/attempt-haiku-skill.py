from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


def expand_occurrences(start_iso: str, rule: dict, range_start_iso: str, range_end_iso: str) -> list[str]:
    """Expand a recurring event into occurrence datetimes within a half-open window."""

    def _parse(s: str) -> datetime:
        """Parse an ISO-8601 string, preserving timezone offset."""
        return datetime.fromisoformat(s)

    def _format(dt: datetime) -> str:
        """Format a datetime back to ISO-8601, preserving the original offset."""
        return dt.isoformat()

    start_dt = _parse(start_iso)
    range_start = _parse(range_start_iso)
    range_end = _parse(range_end_iso)

    freq = rule["freq"]
    interval = rule["interval"]
    count = rule["count"]

    # Determine the step size for each frequency
    if freq == "daily":
        step = timedelta(days=interval)
    elif freq == "weekly":
        step = timedelta(weeks=interval)
    elif freq == "monthly":
        step = relativedelta(months=interval)
    else:
        raise ValueError(f"Unsupported frequency: {freq}")

    results = []
    current = start_dt
    occurrence_index = 0  # 0-based index of occurrence (0 = first/starting occurrence)

    while True:
        occurrence_index += 1

        # Check count bound
        if count is not None and occurrence_index > count:
            break

        # Check if this occurrence falls within the half-open window [range_start, range_end)
        if current >= range_start and current < range_end:
            results.append(_format(current))

        # If we've passed the end of the window and count is unbounded, we can stop
        if count is None and current >= range_end:
            break

        # Advance to next occurrence
        if freq == "monthly":
            import calendar
            target_day = current.day
            # Advance by the interval in months
            candidate = current + step
            # relativedelta clamps the day (Jan 31 + 1 month = Feb 28).
            # We need to skip months where the target day does not exist.
            while True:
                max_day = calendar.monthrange(candidate.year, candidate.month)[1]
                if target_day <= max_day:
                    break
                # Skip: advance one more interval
                candidate = candidate + step
            current = candidate
        else:
            current = current + step

    return results