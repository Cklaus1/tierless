import re
B="/root/projects/fable5/eval/gap-diff/"
CH = {
"adversarial-review":{
 "1 file handle leak":r"file (handle|descriptor)? ?leak|never closed|not closed|with open|context manager|f\.close|\bleak",
 "2 KeyError missing keys":r"keyerror|missing key|\['items'\]|\['id'\]|key.*(missing|absent)|not in o|\.get\(",
 "3 empty->ZeroDivision":r"zerodivision|divide by zero|division by zero|len\(results\).*0|empty (list|orders|input)|no orders",
 "4 float money/rounding":r"\bfloat|floating.point|decimal|round|money.*(float|precision)|penny|cent",
 "5 cache not thread-safe":r"thread.?safe|\brace\b|\block\b|global.*(mutable|shared|state)|concurren|not safe",
 "6 unbounded cache":r"unbounded|grows? forever|memory leak|never evict|cache.*(grow|bound|evict|size)|no (ttl|eviction|limit)",
 "7 cache by-reference mutation":r"by reference|mutat|aliasing|same object|shares? (a )?reference|modifies the (input|dict)|caches the (input|mutable)",
 "8 _hits global wrong":r"_hits|global.*hits|hits.*(never reset|accumulat|wrong|shared|leak across)",
 "9 tax/discount order":r"tax.*(after|before|order)|discount.*then.*tax|tax on discounted|order of operations|tax.*subtotal",
 "10 rate not validated":r"discount_rate.*(negative|>|range|valid|1)|rate.*(range|negative|validation|bound)|invalid rate",
 "11 json/file unhandled":r"json.*(error|invalid|malformed|fail)|filenotfound|file not found|not exist|ioerror|oserror|exception.*(open|load)",
 "12 average semantics":r"average.*(cache|hit|stale|prior|skew|mislead)|avg.*(include|wrong|cached)",
},
"qa-testing":{
 "1 even split":r"even|divides evenly|no remainder|exact.*split|100.*2|divisible",
 "2 remainder distribution":r"remainder|uneven|does.?n.?t divide|first (few|n|people).*(extra|\+1|more)|10.*3|100.*3|leftover cent",
 "3 sum-equals-total":r"sum.*(equal|=|add).*total|adds? up|invariant|conservation|total.*preserved|reconstruct",
 "4 num_people<=0":r"num_people.*(0|zero|negative)|zero people|negative people|people.*(<= ?0|invalid)",
 "5 total negative":r"negative total|total.*(< ?0|negative)|total.*invalid",
 "6 tip negative":r"negative tip|tip.*(< ?0|negative)|tip.*invalid",
 "7 tip zero/default":r"tip.*(0|zero|default|no tip|without tip)|zero tip|default tip",
 "8 tip rounding":r"tip.*(round|rounding|\.5|half|fraction)|round.*tip",
 "9 total zero":r"total.*(0|zero)|zero (total|bill)|free|0 cents",
 "10 one person":r"one person|num_people.*1|single person|1 person",
 "11 large numbers":r"large|big (bill|number|total)|overflow|million|huge",
 "12 fairness <=1 cent":r"at most.*(1|one) (extra|more|cent)|remainder.*< num_people|no one gets.*2|fairness|difference.*(1|one) cent",
},
"threat-modeling":{
 "1 predictable link IDs":r"predictable|guessable|enumerat|sequential id|brute.?force.*(link|url|id)|unguessable|random.*(token|id)",
 "2 link leakage":r"\bleak|referrer|shared.*(link|url)|forwarded|logs?.*(url|link|token)|url in (history|logs)",
 "3 no expiry enforcement":r"expir|\bttl\b|time.?limit|link.*(never|forever|permanent)|expiry.*(bypass|enforc)",
 "4 password brute-force":r"brute.?force.*password|rate.?limit|password.*(guess|attempt)|no.*(throttle|lockout)",
 "5 malware upload":r"malware|virus|malicious (file|upload|content)|scan|antivirus|dangerous file",
 "6 XSS/content-type":r"\bxss\b|content.?type|content-disposition|inline|html.*(upload|served|render)|mime|served as html",
 "7 S3/bucket misconfig":r"s3.*(public|misconfig|acl|bucket|direct)|signed url|presigned|object storage.*(access|permission)|bucket policy",
 "8 authz/cross-tenant":r"authoriz|ownership|cross.?tenant|access other|idor|tenant isolation|only.*(owner|their)",
 "9 unbounded upload/DoS":r"size limit|unbounded|storage exhaust|\bdos\b|denial of service|large file|quota|upload.*(limit|abuse)",
 "10 retention/deletion":r"retention|deletion|lingers|orphan|still (accessible|stored)|delete.*(actual|storage|s3)|scrub",
 "11 exfiltration/insider":r"exfiltrat|insider|data (leak|loss|theft)|sensitive|pii|compromised account|leak.*(data|file)",
 "12 no audit log":r"audit|access log|download log|who (downloaded|accessed)|logging.*(access|download)|traceab",
 "13 password insecure":r"password.*(plain|hash|storage|same channel|with the link)|store.*password|hash.*password",
},
"ui-design":{
 "1 no loading state":r"loading (state|indicator|spinner)|no loading|while.*(fetch|load)|pending state",
 "2 no empty state":r"empty state|no (rows|data|results)|zero (rows|results)|nothing to show|empty.*(list|table)",
 "3 no error state":r"error state|fetch (fail|error)|\.catch|error handling|network (error|fail)|request fail",
 "4 missing key prop":r"key prop|missing key|key=|key warning|react key",
 "5 not semantic table":r"semantic|<table>|table element|\bth\b|\btd\b|role=|div.*(table|instead)|not a (real )?table",
 "6 color-only status":r"color.?only|colou?rblind|color alone|not (just|only) colou?r|icon.*(status|text)|red.*green.*(access|colorblind)",
 "7 low-contrast #999":r"#999|contrast|low.?contrast|wcag|gray.*(header|text).*(contrast|fail)|4\.5|readab",
 "8 not keyboard accessible":r"keyboard|not.*(button|focusable)|<button>|tabindex|onclick.*div|div.*(clickable|not accessible)|role=.?button|\bfocus",
 "9 stale-closure bug":r"stale (closure|rows|state)|closure|\[\.\.\.rows|dependency array|deps.*(missing|rows)|functional update|prev ?=>",
 "10 hardcoded styles":r"inline style|hardcod|design token|magic (number|value)|px.*hardcod|no (theme|token)|repeated.*(200|width)",
 "11 no hover/focus states":r"hover|focus (state|ring|visible)|active state|interactive.*(state|feedback)|no.*(hover|focus)",
 "12 no aria/sr":r"aria|screen reader|\balt\b|sr-only|accessible name|announce|label.*(status|active)",
},
"code-archaeology":{
 "1 backoff/timeout coupled to 3":r"backoff|2 ?\*\* ?attempt|timeout.*attempt|10 ?\* ?\(attempt|coupled|sleep.*attempt|exponential|timing.*(change|scale)",
 "2 attempt==2 hardcoded last":r"attempt == 2|== 2|last attempt|hardcoded (2|last)|count ?- ?1|final attempt|failure event.*(last|2)",
 "3 lock TTL 300 vs retry time":r"\b300\b|\bttl\b|lock.*(expire|duration|exceed)|retry.*(time|exceed).*(lock|300)|total.*(time|duration)|lock.*(time|window)",
 "4 setnx race/ownership":r"setnx|lock.*(race|steal|release other|not (mine|owned))|force.*(concurrent|double|race)|delete.*lock.*(other|another)|lock ownership",
 "5 idempotency write/event":r"idempoten|double (write|event|emit)|emit.*(twice|duplicate|retry)|replay|exactly.once|re.emit",
 "6 timeout growth unbounded":r"timeout.*(grow|unbounded|large|10\*|balloon)|fetch.*(long|slow).*retry|timeout.*(scale|increase)",
 "7 event consumers downstream":r"consum|downstream|who (listens|handles|subscribes)|event.*(consumer|handler|contract)|emit.*(depend|downstream)",
 "8 version compare semantics":r"version|<=|get_local_version|stale|equal.*version|version.*(compare|semantic|skip)",
 "9 callers' expectations":r"caller|who calls|call site|callers.*(expect|rely|depend)|call.*sync_account",
 "10 config source/default 3":r"config|default.*3|preserve.*(3|current|behavior)|backward.?compat|where.*(value|param|setting) come|\benv\b|parameter default",
 "11 tests/characterization":r"\btest|characteriz|coverage|existing test|test.*(before|first)|no tests|write.*test",
 "12 git history/why 3":r"git (log|blame|history)|why (3|hardcoded|these)|chesterton|reason.*(3|hardcoded|chosen)|intentional|original (author|intent|decision)",
},
}
def sc(path,checks):
    try: t=open(path).read().lower()
    except FileNotFoundError: return None
    return {k:(1 if re.search(v,t,re.I) else 0) for k,v in checks.items()}
print(f"{'skill':<20}{'haiku':>7}{'fable':>7}{'/N':>5}{'  gap':>7}")
for skill,checks in CH.items():
    h=sc(f"{B}{skill}/attempt-haiku.md",checks); f=sc(f"{B}{skill}/attempt-fable.md",checks)
    if h is None or f is None: print(f"{skill:<20}  (missing attempt file)"); continue
    hs,fs=sum(h.values()),sum(f.values())
    print(f"{skill:<20}{hs:>7}{fs:>7}{len(checks):>5}{fs-hs:>+7}")
