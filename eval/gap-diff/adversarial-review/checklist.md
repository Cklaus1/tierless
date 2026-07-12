# GRADER checklist — adversarial-review (12 planted defects, keyword-scored)

Many findable defects on purpose (enumeration test). Score each by keyword presence.

1 file handle leak (open never closed / no with): r"file (handle|descriptor)? ?leak|never closed|not closed|with open|context manager|f\.close|leak"
2 KeyError on o['items']/o['id']/item['price'] (missing keys): r"keyerror|missing key|\['items'\]|\['id'\]|key.*(missing|absent)|if .*not in o|\.get\("
3 empty orders -> ZeroDivisionError (len(results)==0 on line 23): r"zerodivision|divide by zero|division by zero|len\(results\).*0|empty (list|orders|input)|no orders"
4 float money / rounding (price*qty in float, tax on discounted): r"float|floating.point|decimal|round|money.*(float|precision)|penny|cent"
5 global mutable _cache not thread-safe (race): r"thread.?safe|race|lock|global.*(mutable|shared|state)|concurren|_cache.*(race|lock)|not safe"
6 unbounded cache growth (memory leak): r"unbounded|grows? forever|memory leak|never evict|cache.*(grow|bound|evict|size)|no (ttl|eviction|limit)"
7 cache stores mutated o by reference / cross-call mutation: r"by reference|mutat|aliasing|same object|shares? (a )?reference|modifies the (input|dict)|caches the (input|mutable)"
8 _hits global shared / wrong across calls / never reset: r"_hits|global.*hits|hits.*(never reset|accumulat|wrong|shared|leak across)"
9 tax applied after discount only (or tax logic questionable) / order-of-ops: r"tax.*(after|before|order)|discount.*then.*tax|tax on discounted|order of operations|tax.*subtotal"
10 no validation of discount_rate/tax_rate range (negative/>1): r"discount_rate.*(negative|>|range|valid|1)|rate.*(range|negative|validation|bound)|invalid rate"
11 json.load failure / bad JSON / file not found unhandled: r"json.*(error|invalid|malformed|fail)|filenotfound|file not found|not exist|ioerror|oserror|exception.*(open|load)"
12 average includes cache_hits from prior calls skewing / avg semantics: r"average.*(cache|hit|stale|prior|skew|mislead)|avg.*(include|wrong|cached)"

## Scoring: each present = 1, /12. This is an ENUMERATION task — the hypothesis is bare Haiku
## finds ~half and stops; a rigorous review (fable, or haiku+adversarial-review skill) finds more.
## If Haiku ~= Fable here, even enumeration is at ceiling. If Fable >> Haiku, real distillable gap.
