from datetime import datetime, timedelta
import calendar


def expand_occurrences(start_iso: str, rule: dict, range_start_iso: str, range_end_iso: str) -> list[str]:
    start = datetime.fromisoformat(start_iso)
    range_start = datetime.fromisoformat(range_start_iso)
    range_end = datetime.fromisoformat(range_end_iso)

    freq = rule["freq"]
    interval = rule.get("interval") or 1
    count = rule.get("count")

    out: list[str] = []
    emitted = 0  # number of series occurrences generated so far

    if freq in ("daily", "weekly"):
        step = timedelta(days=interval * (7 if freq == "weekly" else 1))
        occ = start
        while occ < range_end:
            if count is not None and emitted >= count:
                break
            if occ >= range_start:
                out.append(occ.isoformat())
            emitted += 1
            occ = occ + step
    elif freq == "monthly":
        day = start.day
        base_index = start.year * 12 + (start.month - 1)
        k = 0
        while True:
            month_index = base_index + k * interval
            k += 1
            year = month_index // 12
            month = month_index % 12 + 1
            if day > calendar.monthrange(year, month)[1]:
                continue  # months without this day are skipped entirely
            occ = start.replace(year=year, month=month)
            if occ >= range_end:
                break
            if count is not None and emitted >= count:
                break
            if occ >= range_start:
                out.append(occ.isoformat())
            emitted += 1
    else:
        raise ValueError(f"unsupported freq: {freq!r}")

    return out
