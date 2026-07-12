import re, sys
BASE="/root/projects/fable5/eval/gap-diff/"

DEBUG = {
 "1 line-number mismatch noticed": r"line 41|line 27|line number|line-number|don'?t match|doesn'?t match|mismatch|41.{0,6}27|27.{0,6}41",
 "2 source can't produce the error": r"never returns? none|always returns|cannot (be|return) none|can'?t be none|no (code )?path.*none|apply_discount.{0,20}(never|always)",
 "3 ROOT=deployed code differs": r"deployed|different version|stale|out.of.date|not (this|the) (shown )?(source|code)|version (skew|mismatch)|running code|monkeypatch|shadow|overload|redeploy|the code (that'?s )?running|isn'?t the code",
 "4 (proxy = hit #3)": r"__USE_3__",
 "5 correct next action": r"check.*(deployed|running|actual|real line 41)|diff.*deploy|what.*(actually|really).*(deployed|running)|pull the running|inspect the deployed|reconcile|compare.*(deployed|running)",
 "6 reproduction/evidence": r"reproduce|reproduction|\b1%\b|intermittent|specific (user|tier|data)|which (users|requests)|add logging|instrument",
}
API = {
 "1 idempotency keys": r"idempotenc|idempotency.key|retry.safe|exactly.once|double.(charge|send|submit|spend)|dedup",
 "2 money=integer minor units": r"minor unit|cents|integer.{0,12}(amount|money)|amount.{0,12}(cents|minor|integer)|no float|not.{0,6}float|currency|ISO.?4217",
 "3 error taxonomy (coded)": r"error (code|taxonomy|type)|machine.readable|coded error|insufficient_funds|error.{0,10}enum|problem.?detail|application/problem",
 "4 pagination": r"paginat|cursor|limit.{0,10}offset|page.?token|next.?page|has_more",
 "5 async status/state machine": r"pending|settled|status.{0,15}(pending|processing|poll)|state machine|asynchronous|async.{0,10}(settle|process)|webhook",
 "6 versioning/evolution": r"version|/v1|/v2|breaking change|additive|backward.?compat|deprecat",
 "7 authz/ownership on read": r"authoriz|ownership|only.{0,10}(their|own)|scope|IDOR|cross.(account|user|tenant)|can'?t (see|read|access) other",
 "8 amount validation/limits": r"positive amount|amount.{0,6}> 0|amount <= 0|\blimit|maximum|max.{0,8}amount|reject.{0,10}negative|validation",
}
def score(path, checks):
    t=open(path).read().lower()
    out={}
    for k,v in checks.items():
        if v=="__USE_3__": continue
        out[k]=1 if re.search(v,t,re.I) else 0
    return out
def run(name, checks, hpath, fpath):
    h=score(hpath,checks); f=score(fpath,checks)
    print(f"\n=== {name} ===")
    print(f"{'finding':<40}{'haiku':>7}{'fable':>7}")
    for k in h:
        print(f"{k:<40}{h[k]:>7}{f[k]:>7}")
    print(f"{'TOTAL':<40}{sum(h.values()):>7}{sum(f.values()):>7}  (/{len(h)})")
run("DEBUGGING", DEBUG, BASE+"debugging/attempt-haiku.md", BASE+"debugging/attempt-fable.md")
run("API-DESIGN", API, BASE+"api-design/attempt-haiku.md", BASE+"api-design/attempt-fable.md")
