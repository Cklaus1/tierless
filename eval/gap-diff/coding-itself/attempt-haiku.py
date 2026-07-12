from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def expand_occurrences(
    start_iso: str,
    rule: dict,
    range_start_iso: str,
    range_end_iso: str,
) -> list[str]:
    start_dt = datetime.fromisoformat(start_iso)
    range_start = datetime.fromisoformat(range_start_iso)
    range_end = datetime.fromisoformat(range_end_iso)

    freq = rule["freq"]
    interval = rule["interval"]
    count = rule["count"]

    results: list[str] = []
    orig_day = start_dt.day

    if freq == "monthly":
        # Compute each candidate from start_dt to avoid day-clipping.
        # Skip months without orig_day.
        month_num = 0
        while True:
            month_num += interval
            candidate = start_dt + relativedelta(months=month_num)
            if candidate.day != orig_day:
                continue
            if candidate >= range_end:
                break
            if candidate >= range_start:
                results.append(candidate.isoformat())
    elif freq == "daily":
        i = 0
        while True:
            i += 1
            if count is not None and i > count:
                break
            current = start_dt + timedelta(days=interval * (i - 1))
            if current >= range_start and current < range_end:
                results.append(current.isoformat())
            elif current >= range_end:
                break
    elif freq == "weekly":
        i = 0
        while True:
            i += 1
            if count is not None and i > count:
                break
            current = start_dt + timedelta(weeks=interval * (i - 1))
            if current >= range_start and current < range_end:
                results.append(current.isoformat())
            elif current >= range_end:
                break

    return results