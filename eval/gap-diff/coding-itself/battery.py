#!/usr/bin/env python3
# GRADER-ONLY execution battery for the coding-itself probe. Not shown to arms.
# Usage: python3 battery.py /path/to/attempt.py   (file must define expand_occurrences)
import sys, os, json, importlib.util

def load(path):
    spec = importlib.util.spec_from_file_location("arm_mod", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.expand_occurrences

CASES = []
def case(name, args, expected):
    CASES.append((name, args, expected))

# 1. basic daily, window subset, half-open end
case("daily_basic",
     ("2026-03-01T09:00:00+00:00", {"freq":"daily","interval":1,"count":5}, "2026-03-01T00:00:00+00:00", "2026-03-04T00:00:00+00:00"),
     ["2026-03-01T09:00:00+00:00","2026-03-02T09:00:00+00:00","2026-03-03T09:00:00+00:00"])
# 2. half-open: occurrence exactly at range_end is EXCLUDED
case("half_open_end_excluded",
     ("2026-03-01T00:00:00+00:00", {"freq":"daily","interval":1,"count":None}, "2026-03-01T00:00:00+00:00", "2026-03-03T00:00:00+00:00"),
     ["2026-03-01T00:00:00+00:00","2026-03-02T00:00:00+00:00"])  # 03-03 excluded
# 3. half-open: exactly at range_start INCLUDED
case("half_open_start_included",
     ("2026-03-01T00:00:00+00:00", {"freq":"daily","interval":1,"count":3}, "2026-03-01T00:00:00+00:00", "2026-03-02T00:00:00+00:00"),
     ["2026-03-01T00:00:00+00:00"])
# 4. count bounds the series (window wants more than count)
case("count_bounds",
     ("2026-03-01T00:00:00+00:00", {"freq":"daily","interval":1,"count":2}, "2026-03-01T00:00:00+00:00", "2026-12-01T00:00:00+00:00"),
     ["2026-03-01T00:00:00+00:00","2026-03-02T00:00:00+00:00"])
# 5. weekly interval=2 (every other week)
case("weekly_interval2",
     ("2026-03-02T12:00:00+00:00", {"freq":"weekly","interval":2,"count":4}, "2026-03-01T00:00:00+00:00", "2026-05-01T00:00:00+00:00"),
     ["2026-03-02T12:00:00+00:00","2026-03-16T12:00:00+00:00","2026-03-30T12:00:00+00:00","2026-04-13T12:00:00+00:00"])
# 6. monthly day-31 SKIP (Jan31 -> Mar31 -> May31; Feb/Apr skipped)
case("monthly_day31_skip",
     ("2026-01-31T08:00:00+00:00", {"freq":"monthly","interval":1,"count":None}, "2026-01-01T00:00:00+00:00", "2026-06-01T00:00:00+00:00"),
     ["2026-01-31T08:00:00+00:00","2026-03-31T08:00:00+00:00","2026-05-31T08:00:00+00:00"])
# 7. window entirely before series -> []
case("window_before",
     ("2026-03-01T00:00:00+00:00", {"freq":"daily","interval":1,"count":3}, "2026-01-01T00:00:00+00:00", "2026-02-01T00:00:00+00:00"),
     [])
# 8. window entirely after bounded series -> []
case("window_after",
     ("2026-03-01T00:00:00+00:00", {"freq":"daily","interval":1,"count":3}, "2026-06-01T00:00:00+00:00", "2026-07-01T00:00:00+00:00"),
     [])
# 9. timezone offset preserved (-05:00)
case("tz_offset_preserved",
     ("2026-03-01T09:00:00-05:00", {"freq":"daily","interval":1,"count":2}, "2026-03-01T00:00:00-05:00", "2026-03-05T00:00:00-05:00"),
     ["2026-03-01T09:00:00-05:00","2026-03-02T09:00:00-05:00"])
# 10. unbounded terminates, window clips
case("unbounded_clipped",
     ("2026-03-01T00:00:00+00:00", {"freq":"daily","interval":1,"count":None}, "2026-03-10T00:00:00+00:00", "2026-03-13T00:00:00+00:00"),
     ["2026-03-10T00:00:00+00:00","2026-03-11T00:00:00+00:00","2026-03-12T00:00:00+00:00"])

def norm(s):
    # compare by instant+offset via datetime parse to avoid trivial format diffs (Z vs +00:00)
    from datetime import datetime
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    return d.isoformat()

def main():
    fn = load(sys.argv[1])
    results={}
    for name,args,expected in CASES:
        try:
            got = fn(*args)
            ok = [norm(x) for x in got] == [norm(x) for x in expected]
            results[name] = {"pass": ok, **({} if ok else {"got": got, "want": expected})}
        except Exception as e:
            results[name] = {"pass": False, "err": f"{type(e).__name__}: {e}"}
    p=sum(1 for r in results.values() if r["pass"])
    print(json.dumps({"passed":p,"total":len(CASES),"rate":round(p/len(CASES),3),"results":results}, indent=1))

if __name__=="__main__":
    main()
