# Debugging: intermittent `AttributeError: 'NoneType' object has no attribute 'total'` on /checkout

## TL;DR — the root cause

**The process that produced this traceback is not running the code shown from `main`.**
The traceback is internally consistent with an *older/different* version of
`app/checkout.py` in which `summarize`'s `return applied.total` sits at line 41 and in
which `apply_discount` has a code path that returns `None`. The repo's `main` copy (27
lines, `apply_discount` always returns a `Receipt`) has already diverged from what is
deployed on (at least part of) production. The ~1% intermittency is the signature of a
**partial / stale deployment**: only a small slice of the fleet (one stale pod, one
un-restarted worker, a canary, a host that missed the rollout) is still executing the old
code, so only the requests routed to that slice crash.

There is no bug to find *in the code shown* — that version cannot raise this error. The
bug is in the deployment pipeline / release hygiene, plus whatever the old code's `None`
path was (already fixed on `main`).

## Walking through the reasoning

### 1. The code shown cannot produce this error

In the `main` source, `apply_discount` returns on every path:

- `rate is None` → `return Receipt(subtotal, Decimal("0"), subtotal)` (line 21)
- otherwise → `return Receipt(subtotal, discount, subtotal - discount)` (line 23)

There is no `return None`, no bare `return`, and no way to fall off the end of the
function. `sum(..., Decimal("0"))` handles an empty cart fine (subtotal = 0, tier rate or
no rate, still a `Receipt`). So if this exact code were running, `applied` could never be
`None`. Something raising here means the running code is *not* this code. That's the
first contradiction, and it should immediately shift suspicion from "logic bug in main"
to "which code is actually executing?"

### 2. The line numbers confirm it

The traceback reports:

- `handle_checkout` at `checkout.py` **line 88**
- `return applied.total` at `checkout.py` **line 41**

The file on `main` is **27 lines long**. Line 41 doesn't exist in it, and there is no
`handle_checkout` at all (let alone at line 88). Line numbers in a Python traceback come
from the **code objects compiled when the module was imported**, and the source text
displayed for each frame is read (via `linecache`) from the **file on disk at the moment
the traceback is formatted**.

Here the traceback shows `return applied.total` *as the text of line 41*. That tells us
the file **on disk on the crashing host** actually has that statement at line 41 — i.e.
the deployed `checkout.py` is a longer, different file than the one on `main`. (If the
host had the new 27-line file on disk but an old module loaded in memory, line 41 would
have rendered as blank/garbage instead.) So this isn't even the subtle
"module-loaded-before-file-was-swapped" variant: the *artifact on that host* is simply an
old version of the file. The repo and production have drifted.

Corroborating detail: the old version is ~1.5–3x longer (≥88 lines vs 27), consistent
with a refactor/cleanup having landed on `main` — very plausibly the very commit that
*fixed* this NoneType bug — that never fully reached production.

### 3. Why it's intermittent at ~1%

Two multiplicative filters explain the low, steady rate:

1. **Only some capacity runs the stale code.** Typical mechanisms:
   - a rolling deploy that never completed / a pod that failed to pull the new image and
     kept running the old one;
   - a `gunicorn`/`uwsgi` graceful reload where one worker survived with the old module
     (though here the on-disk file is old too, which points at a whole stale host/image
     rather than a stale worker);
   - a canary or region that was skipped;
   - a host provisioned from a cached/stale AMI or Docker layer.
   If 1 pod out of ~100 (or one worker slice of traffic) is stale, you get ~1% of
   requests hitting it — before even considering the request shape.

2. **Only some requests trigger the old bug.** In the old code, `apply_discount`
   evidently returned `None` on some branch — classic shapes are a missing `return` on
   the "no discount" arm (function falls off the end → implicit `None`), an early
   `return None` for empty carts, or a failed coupon lookup. Whatever it was, only
   requests hitting that branch crash.

Either filter alone (or both together) yields the observed "intermittent, ~1%" pattern,
and neither correlates with anything visible in the `main` source — which is exactly why
this class of bug is so disorienting if you only stare at the repo.

### 4. How to confirm (do this before "fixing")

- On a host that produced the traceback: `wc -l app/checkout.py`, `md5sum`/`sha256sum`
  it, and diff against `main`. Check the file's mtime and any `__pycache__/*.pyc`.
- Check the deployed build ID / git SHA on each host or pod (`kubectl get pods -o wide`
  + image digests, or a `/version` endpoint) and look for the odd one out.
- Correlate the error logs with hostname/pod ID — expect them all to come from the same
  small set of instances.
- In the old file (recoverable from the stale host or `git log -p app/checkout.py`),
  find the branch of `apply_discount` (or its predecessor) that returns `None`; confirm
  it matches the request shapes that crashed.

## The fix

**Immediate remediation**
1. Identify the stale instance(s) and redeploy/replace them so the entire fleet runs the
   current artifact built from `main`. Kill lingering old worker processes; don't rely on
   graceful reloads — do a full restart or replace the container.
2. Delete stale bytecode if deploys are done in-place (`find . -name '__pycache__' -exec
   rm -rf {} +`), or better, stop doing in-place deploys.

**Code-level hardening (optional but cheap)** — the current code is already correct, but
you can make this failure mode loud and self-diagnosing:
- Log/emit the running build SHA (`git rev-parse HEAD` baked in at build time) with every
  error report, so "traceback doesn't match repo" is detectable at a glance.
- If you want a belt-and-suspenders guard: have `summarize` assert
  `applied is not None` with a clear message, or type-annotate `apply_discount(...) ->
  Receipt` and enforce it in CI. This wouldn't have prevented the incident (the old code
  predates the guard) but documents the invariant.

**Preventing recurrence (the real fix)**
- Make deploys **atomic and immutable**: build a versioned image/artifact, roll it out,
  and verify convergence — the deploy isn't "done" until every serving instance reports
  the new version. Alert on version skew across the fleet.
- Fail health checks (or refuse to serve) when an instance's reported version doesn't
  match the release manifest.
- Never hot-patch files on running hosts; if a rolling deploy stalls, surface it instead
  of silently leaving mixed versions in service.

## One-paragraph summary

The traceback and the source disagree twice — the line numbers (41/88 vs a 27-line file)
and the behavior (`apply_discount` in `main` cannot return `None`). Both disagreements
have the same explanation: the crashing host is running, and has on disk, an **older
version of `app/checkout.py`** in which `apply_discount` could return `None` and in which
`return applied.total` was line 41. Roughly 1% of traffic lands on that stale instance
(and/or hits the old code's `None` branch), producing the intermittent failures. The
repo's code already contains the logic fix; the actionable fix is to finish/repair the
deployment so every instance runs the current build, and to add version-skew detection
(build SHA in logs, convergence checks) so a half-finished rollout can never masquerade
as a code bug again.
