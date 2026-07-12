from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


def expand_occurrences(start_iso: str, rule: dict, range_start_iso: str, range_end_iso: str) -> list[str]:
    start = datetime.fromisoformat(start_iso)
    range_start = datetime.fromisoformat(range_start_iso)
    range_end = datetime.fromisoformat(range_end_iso)

    freq = rule["freq"]
    interval = rule["interval"]
    count = rule["count"]

    def make_delta():
        if freq == "daily":
            return timedelta(days=interval)
        elif freq == "weekly":
            return timedelta(weeks=interval)
        elif freq == "monthly":
            return relativedelta(months=interval)
        else:
            raise ValueError(f"Unsupported freq: {freq}")

    delta = make_delta()
    results = []
    current = start
    idx = 1

    while True:
        if count is not None and idx > count:
            break

        if current >= range_end:
            break

        if current >= range_start:
            results.append(current.isoformat())

        current = current + delta
        idx += 1

    return results