# Migration plan: Python 2 / Django 1.8 monolith → Python 3 / modern Django

## Executive summary (and the pushback, up front)

The proposed plan — a clean-repo rewrite, big-bang cutover, 4 months, 6 engineers — has three
independent components, and **each one is a well-documented failure mode**. I'll push back on all
three, then lay out a plan that actually gets us to Python 3 + a supported Django, with paying
customers unharmed, in roughly 9–12 months while continuing to ship features at reduced capacity.

The one thing leadership is *right* about is urgency: Python 2.7 has been end-of-life since
January 2020 and Django 1.8's extended support ended in April 2018. We are running an unpatched
stack, and every month we wait accrues security and compliance risk (and makes hiring harder).
The disagreement is not about *whether* to do this — it's about *how*, because the proposed *how*
maximizes the odds we never finish.

---

## Part 1: Pushback — why the proposed plan fails

### 1.1 "Rewrite in a clean new repo" — don't

**The arithmetic doesn't work.** 200k lines ÷ 6 engineers ÷ 16 weeks ≈ 2,100 lines of
production-quality re-implementation per engineer per week — *plus* tests, *plus* data migration,
*plus* parity verification, *plus* everything not counted in "lines" (infra, deploy pipeline,
integrations, admin tooling, cron/Celery jobs, email templates, reports). Sustained real-world
throughput on re-implementation of poorly-specified legacy behavior is a small fraction of that.
Honest estimate for a true rewrite of a 200k-line, ~10-year-old SaaS: 18–36 months. Every rewrite
estimate I've seen at this scale was off by 2–4×, in the wrong direction.

**The code is the spec.** A decade of production code encodes thousands of decisions that exist
nowhere else: edge-case handling for specific customers, regulatory quirks, workarounds for partner
API bugs, "load-bearing bugs" that customers have built workflows on top of. A rewrite team must
rediscover all of this — usually via customer-facing incidents. This is Joel Spolsky's "things you
should never do" argument and the Netscape 4→6 story; the base rate for ground-up rewrites of
live revenue-generating systems is grim, and the failure mode is not "it shipped late" but "it was
cancelled after 14 months and we still run the old system, now with two years less patching."

**The moving-target problem.** A separate repo forces a choice: (a) feature-freeze the old system
for the duration — the business will not accept a 4-month freeze, and the real duration is 18+
months; or (b) keep shipping features in old *and* re-implement them in new — double work,
permanent divergence, and the rewrite chases a target that recedes faster than the team closes on
it. This alone kills most parallel rewrites.

**You lose the history.** `git blame` and the issue links in commit messages are the only
documentation of *why* code is weird. A clean repo throws away the institutional memory exactly
when you need it most.

**Second-system effect.** A "clean" rewrite invites re-architecting everything at once (new
framework patterns, new schema, maybe microservices, maybe a new frontend). Every added axis of
change multiplies risk. The migration should change *one thing at a time*: language version, then
framework version. Architecture improvements come after, incrementally, on a supported stack.

### 1.2 "Big-bang cutover" — don't

- **No rollback path.** The moment the new system writes customer data, rolling back means either
  losing writes or building a reverse data migration under incident pressure. With paying
  customers, an un-rollbackable deploy of 200k rewritten lines is a bet-the-company move.
- **All latent bugs land on one night.** Incremental migration surfaces bytes/str bugs,
  serialization bugs, and behavior drift a handful at a time, each individually debuggable.
  A big-bang cutover surfaces hundreds simultaneously, in production, with the whole customer
  base as the test cohort.
- **Data migration under a downtime window** for a live SaaS schema (with in-flight Celery jobs,
  sessions, caches, webhooks, third-party callbacks) is its own multi-month project with dress
  rehearsals — none of which is budgeted in the 4 months.

The alternative — progressive rollout (canary hosts, percentage-based traffic shifting, per-tenant
flags) with instant rollback — is available *only* if the new and old code run against the same
database and the same repo. That's a structural argument for in-place migration.

### 1.3 "4 months" — not for a rewrite; plausible only as the first milestone of an incremental plan

Four months is roughly what it takes a team of 6 to do Phase 0 + the Django 1.8→1.11 ladder + a
large fraction of Python 2/3 compatibility work (see timeline, Part 4). I'd offer leadership that
reframe: *in 4 months we can be on Django 1.11 with the codebase running its test suite under both
Python 2 and Python 3 — a demonstrable, de-risked halfway point — rather than 4 months into an
18-month rewrite with nothing shipped.*

### 1.4 Steelmanning leadership, and what to say

Leadership's real goals are usually: (1) get off the unpatched stack fast, (2) escape accumulated
tech debt, (3) a clean story for customers/auditors/recruits. Answer each:

1. **Speed to safety:** the incremental path reaches "off Python 2" *sooner* than any realistic
   rewrite finishes, and delivers security value at every intermediate milestone (each Django hop
   picks up years of fixes). A rewrite delivers zero security value until the very end — which is
   the part most likely never to arrive. Meanwhile, apply interim mitigations now: WAF in front,
   network segmentation, dependency audit, backport-critical patches (or a paid ES vendor for
   Python 2.7 / old Django if compliance demands it).
2. **Tech debt:** the debt goes away module-by-module *after* we're on a supported stack, with the
   safety net of tests and typed, linted code — not by betting everything on one repo-sized PR.
3. **Narrative:** "we upgraded a live system with zero downtime and continuous delivery" is a
   better engineering-brand story than a rewrite, and it produces auditable checkpoints
   (Django 1.11 LTS → 2.2 LTS → 3.2 LTS → 4.2 LTS) for compliance.

Commit to measurable milestones with dates and demo them. If leadership still insists on a new
repo, the only responsible variant is the **strangler fig**: put a routing proxy in front, carve
off one bounded context at a time into new services, retire the monolith slice by slice. It's
valid but *slower and more expensive* than in-place upgrade for a single-team monolith; it's the
right tool when you also need to break the monolith apart, which nobody has claimed here.

---

## Part 2: The actual plan

Strategy in one line: **same repo, same database, one variable at a time, deployed continuously**.
The sequence exploits the designed-for-this bridge: **Django 1.11 LTS is the last release that
supports Python 2 and the first LTS that supports Python 3** — it's the pivot point of the whole
migration.

Ladder: `Django 1.8 (py2) → 1.9 → 1.10 → 1.11 (py2) → 1.11 (py2+py3 dual) → 1.11 (py3 only)
→ 2.0 → 2.1 → 2.2 LTS → 3.0 → 3.1 → 3.2 LTS → 4.0 → 4.1 → 4.2 LTS` (and onward to 5.x once
stable there). Python: `2.7 → 3.7/3.8 (whatever futurize-era libs support as the bridge)
→ 3.11/3.12` once on Django ≥4.2. Never change Django version and Python version in the same
deploy.

### Phase 0 — Safety nets and reconnaissance (weeks 1–4, parallelizable)

Nothing else starts until we can (a) detect breakage fast and (b) know the true scope.

1. **Inventory & dependency audit (this sets the critical path).**
   - `pip freeze` everything, including transitive deps and anything vendored. For each package:
     does a Python-3-compatible version exist? Does a Django-2.x/3.x/4.x-compatible version exist?
     Is it maintained at all?
   - Expect casualties in a Django 1.8-era stack: `MySQL-python`/`MySQLdb` (→ `mysqlclient`),
     `python-memcached` (→ `pymemcache`), old `PIL` (→ `Pillow`), ancient `celery`/`kombu`
     (3.x → 4.x → 5.x is its own mini-migration: config names, CELERY_ prefix changes, serializer
     defaults), `django-celery` (dead; replaced by celery's own Django integration +
     `django-celery-beat`/`-results`), old `boto` (→ `boto3`), `suds` (→ `zeep`),
     `python-openid`, old `requests`/`urllib3`, any `M2Crypto`-era crypto (→ `cryptography`),
     abandoned Django plugins (form wizards, old admin skins, `django-tastypie`-era API layers).
   - For each dead dependency: replace, vendor-and-port, or delete the feature. **This audit is the
     single biggest unknown in the schedule — do it in week 1.**
   - Also audit the **database server version**: modern Django raises the floor (Django 2.2 needs
     MySQL ≥5.6/PostgreSQL ≥9.4; 3.2 needs MySQL ≥5.7/PG ≥9.6; 4.2 needs MySQL ≥8/PG ≥12). A DB
     upgrade may be a hidden sub-project with its own downtime planning; schedule it early, on the
     old app version, as its own isolated change.
   - Same for OS/base image: Python 2.7 often means an ancient distro; plan the container/OS
     refresh as an isolated step too.

2. **Test reality check + characterization tests.**
   - Measure current coverage. A 10-year Django 1.8 monolith typically has patchy coverage; do not
     start migrating on faith.
   - Where coverage is thin on money paths (billing, auth, permissions, tax/pricing calculations,
     exports, webhooks), write **characterization ("golden master") tests**: capture current
     behavior — including its bugs — as the spec. Snapshot tests on rendered HTML/JSON of key
     endpoints and generated files (invoices, CSVs, PDFs) are cheap and catch subtle drift like
     dict-ordering or rounding changes.
   - Turn on **coverage-in-production** (or at least import/route-level telemetry) for 2–4 weeks to
     find **dead code**, and run `vulture`. In a codebase this age, 10–25% is typically dead.
     **Delete it before migrating it** — the cheapest line to port is the one you remove.

3. **Operational safety.**
   - CI running the full suite on every PR (if it isn't already), plus a nightly run with
     `-W error::DeprecationWarning` so deprecations are failures, not noise.
   - Error tracking (Sentry) with release tagging; dashboards for error rate, latency, queue depth,
     and business KPIs (signups, checkout success) so a canary regression is visible in minutes.
   - **Canary/gradual deploy capability**: the ability to route N% of traffic (or specific
     internal/test tenants) to a subset of app servers. This is the mechanism that replaces the
     big-bang cutover, and it's also how we'll run Python 3 side-by-side later.
   - Feature-flag facility (even a simple settings/db-backed one).
   - Rehearsed database backup/restore; verified staging environment with prod-like data
     (anonymized) — bytes/str bugs live in real data (emoji in names, latin-1 in old rows, weird
     encodings in imported CSVs), not in fixtures.

4. **Team process.**
   - One engineer as **migration lead** (owns sequencing, tooling, the tracking dashboard);
     everyone contributes, features continue at ~60–70% capacity.
   - Ratchet rules enforced in CI from day 1: all *new* code must be Python 2/3 compatible
     (`from __future__ import absolute_import, division, print_function, unicode_literals`;
     lint via `pylint --py3k` / flake8 plugins), no new usage of APIs already deprecated in
     Django 1.9+. This stops the hole getting deeper while we dig out.
   - A visible burn-down: modules converted / deprecation warnings remaining / packages upgraded.

### Phase 1 — Django 1.8 → 1.11 LTS, still on Python 2 (weeks 3–10, overlaps Phase 0)

One minor version per hop; **deploy and soak in production after each hop** (a few days minimum).
For each hop: read the release notes end-to-end, fix all deprecation warnings *on the current
version* first (so the upgrade commit itself is small), bump, run suite, fix, canary, roll out.

Known work at this range (what to budget for):
- **1.8→1.9:** `django.utils.importlib`/`django.utils.unittest` removals; `ModelForm` without
  `fields`/`exclude` now errors; app loading strictness; implicit `QuerySet.__bool__` in templates
  changes; many contrib deprecations start their clock.
- **1.9→1.10:** `patterns()` removed from URLconfs (touches every `urls.py` if the codebase is old
  enough); **new-style middleware** (`MIDDLEWARE` vs `MIDDLEWARE_CLASSES`) — port each middleware
  class; `User.is_authenticated`/`is_anonymous` become properties (calling them still works but
  warns; fix call sites now because truthiness bugs here are auth bugs).
- **1.10→1.11:** last cleanups; also finish moving any lingering old-style `TEMPLATE_*` settings
  to the `TEMPLATES` dict if 1.8-era settings remain. 1.11 is where we will sit for a while, so
  get warning-clean here.
- Each hop may force third-party package bumps discovered in the Phase-0 audit; that's expected
  and why the audit came first.

### Phase 2 — Dual Python 2/3 compatibility on Django 1.11 (weeks 8–22; the long pole)

Goal: the entire codebase runs, and the full test suite passes, under **both** interpreters
(tox envs `py27-dj111` and `py3X-dj111` on every PR). Dual-run rather than flag-day conversion,
because it lets us convert module-by-module, keep deploying from `master` throughout, and roll the
interpreter switch back trivially.

Tooling:
- `python-future`'s **`futurize`** (or `modernize` + `six` — pick one idiom and standardize) for
  the mechanical pass, applied **package-by-package in small reviewed PRs**, not one mega-commit.
- `python -3` (Py2's warning flag) in CI to catch dynamic issues tests exercise;
  `pylint --py3k` for static ones.
- Convert leaf/utility packages first, then apps in dependency order; track on the dashboard.

The mechanical 80% (print, `except ... as`, relative imports, `dict.iteritems`, `xrange`,
`urllib`/`urlparse` reorg, `__unicode__`→`__str__` via `python_2_unicode_compatible`, metaclass
syntax, removed `cmp`) goes fast. Budget the schedule for the **semantic 20%**:

- **bytes vs. str — the big one.** Every boundary must be audited by hand: file I/O (mode `'b'`
  or not, explicit `encoding=`), sockets, subprocess output, `hashlib`/`hmac`/`base64` (now
  require bytes), email handling, CSV (`csv` module semantics differ), any binary protocol,
  request bodies, S3 payloads, crypto signing for webhooks/SSO. Grep for `str(`, `.encode`,
  `.decode`, `unicode(`, `basestring`. These bugs pass unit tests with ASCII fixtures and explode
  on the first customer named "Müller" — hence prod-like staging data and characterization tests.
- **Integer division.** `/` changes meaning. In a SaaS this hides in **billing, proration,
  pagination, rate limiting, and scheduling** math. `from __future__ import division` early
  (Phase 0 ratchet) plus a targeted audit of every `/` in money paths. Related:
  Python 3 `round()` is banker's rounding (half-to-even) — re-verify every financial rounding
  site against `decimal` with an explicit rounding mode; write regression tests from real
  invoices.
- **Comparison and ordering.** Py3 raises on comparing unlike types (`None < 3`, `str < int`) —
  latent in any `sorted()` over heterogeneous or nullable data; `cmp=` is gone (→ `key=` /
  `functools.cmp_to_key`).
- **Dict/set ordering assumptions.** Code that accidentally depended on Py2 dict order (or on
  hash randomization being off) — commonly bites generated SQL/report column order, template
  output, and test snapshots. The characterization tests from Phase 0 catch these.
- **Laziness.** `map`/`filter`/`zip`/`dict.keys()` become views/iterators: single-consumption
  bugs, `len()` on them, mutation during iteration.
- **`pickle` and other serialization across versions** — see Phase 3; start fixing now by moving
  Celery, cache, and session serialization to JSON (or pin `pickle` protocol 2) *while still on
  Py2*, so the wire format is version-neutral before any Py3 process exists.
- **Doctests and text fixtures** with `u''` prefixes / repr differences — either fix or convert to
  real tests.
- **C extensions / platform bits**: anything with compiled components needs Py3 wheels or
  replacement (from the Phase-0 audit).

### Phase 3 — Production cutover to Python 3 (weeks 20–26)

This is where the "big-bang" is dissolved into a non-event:

1. **Pre-neutralize shared state.** Before the first Py3 process starts, everything that crosses
   process boundaries must be readable by both interpreters:
   - **Celery**: task serializer to JSON (also kills a security hole — pickle task payloads);
     drain or version queues so no Py2-pickled payload reaches a Py3 worker mid-flight.
   - **Cache** (memcached/redis): switch to a JSON serializer or, simpler, **bump the cache key
     prefix/version at cutover** and eat a cold cache — plan for the DB load spike.
   - **Sessions**: Django's default moved to JSON serialization long ago, but a 1.8-era app may
     still be on `PickleSerializer` — switch beforehand (may log users out; announce it), or
     support a transition.
   - **Anything pickled in the DB or object store** (saved reports, cached computations,
     `django-picklefield` columns): migrate to JSON or ensure protocol-2 + bytes-compat readers.
   - **Password hashing, signing, and tokens**: verify `SECRET_KEY`-derived signatures
     (cookies, password-reset tokens, `Signer` values, webhook HMACs) produce identical results
     under both interpreters — a stray implicit encode makes every user's session/reset link die
     at cutover.
2. **Shadow/dark launch (optional but cheap insurance):** replay a sample of production GET
   traffic against a Py3 instance and diff responses (a Scientist-style experiment for the
   riskiest read endpoints); run the nightly batch/report jobs on Py3 in parallel and diff
   outputs byte-for-byte.
3. **Canary:** internal tenants → 1% → 5% → 25% → 100% of app servers on Py3 over 1–2 weeks,
   watching error rates, latency (Py3 is usually a small win, but memory profile differs —
   watch RSS and tune worker counts), and the business KPIs. **Rollback is "route traffic back";
   the database never changed.** Migrate Celery workers per-queue the same way.
4. Soak at 100% for 2+ weeks through at least one billing cycle / month-end batch, then delete
   the Py2 CI leg, remove `six`/`__future__` shims (`pyupgrade` automates this), and burn the
   Python 2 boats.

### Phase 4 — Django 1.11 → 4.2 LTS on Python 3 (months 7–11)

Now it's the same hop-fix-deploy-soak loop, but easier: one interpreter, growing test suite, and
`django-upgrade` + `python -W error::PendingDeprecationWarning` do much of the finding. Pause at
each LTS (2.2, 3.2, 4.2) for a longer soak; those are also the clean compliance checkpoints.
Budget the known heavy items:

- **2.0:** `on_delete` becomes a **required** argument on `ForeignKey`/`OneToOneField` — touches
  essentially every model file; choose semantics deliberately (don't blanket-CASCADE), and note
  it generates a wave of no-op migrations. URL routing: `url()` → `re_path()`/new `path()`.
- **2.1–2.2:** view permission added to admin (check custom admin assumptions);
  `QuerySet`/`Model.save` subtleties; DB version floors (from Phase 0).
- **3.0–3.1:** removal of long-deprecated `python_2_unicode_compatible`, `six` vendoring,
  `ugettext*` → `gettext*` everywhere (mass rename, scriptable); `django.utils.encoding`
  renames; async foundations land (no action required, but middleware/`ASGI` review if we want
  it later).
- **4.0–4.2:** `USE_L10N` removed, time-zone default flips (`USE_TZ` discipline — audit naive
  datetimes *early*, ideally back in Phase 0, because a 1.8-era app is often `USE_TZ=False` and
  flipping it is its own careful data project — it's legitimate to defer `USE_TZ=True` and pin
  the setting), `CSRF_TRUSTED_ORIGINS` scheme requirement (breaks logins if missed),
  `DEFAULT_AUTO_FIELD` (pin to `AutoField` to avoid surprise migrations), password reset token
  and session cookie changes on hops (expect a stragglers' logout).
- Upgrade CPython to 3.11/3.12 as a separate, boring step once Django ≥4.2 (floor is 3.8+);
  gains are free performance and a supported interpreter.

### Phase 5 — Actually pay down the debt (ongoing, post-migration)

The rewrite's real motivations get honored here, incrementally and safely: introduce `mypy` with a
ratchet, `black`/`ruff` the codebase, extract genuinely separable domains behind interfaces (and
only then, if warranted, into services), replace the worst legacy modules one at a time with tests
as the harness. This is where "clean" comes from — after, not before, the platform is supported.

---

## Part 3: Risk register (the honest version)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Abandoned dependency with no Py3/modern-Django path | High | Schedule (can be weeks per package) | Week-1 audit; vendor-and-port or replace early; this defines the critical path |
| bytes/str bugs on real (non-ASCII) customer data | Certain | Customer-facing errors, corrupted exports | Prod-like staging data, characterization tests, hand-audit of every I/O boundary, canary rollout |
| Cross-version pickle in Celery/cache/sessions/DB | High | Outage or silent data loss at cutover | Neutralize serialization to JSON *before* any Py3 process runs; version cache keys; drain queues |
| Integer-division / `round()` drift in billing math | Medium | Wrong invoices — worst possible bug class | Targeted audit of money paths, golden-master tests from real invoices, `decimal` with explicit rounding |
| Signing/token incompatibility (`SECRET_KEY` HMACs) | Medium | Mass logout, broken reset links, webhook auth failures | Cross-interpreter signature verification tests pre-cutover |
| Hidden business rules only discovered by breaking them | High (rewrite) / Low (in-place) | Customer trust | In-place migration never re-implements logic — this risk is mostly *created by* the rewrite plan |
| DB server / OS too old for target Django | Medium | Hidden sub-project | Phase-0 audit; upgrade DB/OS as isolated early steps |
| Test coverage too thin to migrate safely | High | Everything | Phase 0 characterization tests before touching code; coverage ratchet |
| Feature pressure erodes migration capacity | High | Migration stalls at 80% (worst outcome: dual-stack forever) | Leadership agreement on 60–70% feature capacity, visible milestone dashboard, CI ratchets so no regression |
| Team burnout / attrition on a death-march deadline | High (4-month plan) | Losing the 6 people who hold the system's knowledge | Realistic timeline with celebrated intermediate wins |
| Security incident on EOL stack during migration | Medium | Severe | WAF, segmentation, dep pinning/audit, optional commercial extended-support patches; and the fastest *credible* schedule — which is this one, not the rewrite |
| Performance/memory regressions on Py3 or new Django hops | Low–Medium | Capacity cost | Canary with latency/RSS dashboards; tune workers; `django-perf-rec`-style query-count tests on hot paths |
| "While we're at it" scope creep (new schema, new frontend, microservices) | High | Converts a migration into a rewrite by stealth | Rule: one variable per change; architecture work is Phase 5 |

The single most important risk isn't technical: it's **stopping halfway**. A codebase stuck
half-migrated (dual idioms, frozen at the bridge) is worse than either endpoint. The mitigations
are the CI ratchets (no backsliding), the module burn-down (visible progress), and leadership's
explicit commitment to see it through — which is exactly why over-promising a 4-month finish is
dangerous: when month 4 arrives mid-journey, an over-promised project gets cancelled; an
accurately-promised one gets finished.

---

## Part 4: Timeline and staffing (honest numbers)

Assumes 6 engineers, ~60–70% capacity on migration early (Phases 0–2), less later; feature work
continues throughout in the same repo, on the same trunk.

| Phase | Calendar | Milestone (demoable) |
|---|---|---|
| 0. Safety nets, audit, dead-code purge | Weeks 1–4 | Dependency verdict list; coverage baseline; canary deploys working |
| 1. Django 1.8→1.11 (Py2) | Weeks 3–10 | Prod on Django 1.11 LTS, deprecation-clean |
| 2. Dual Py2/Py3 compat | Weeks 8–22 | Full suite green on both interpreters, every PR |
| 3. Py3 production cutover | Weeks 20–26 | Prod 100% Python 3; Py2 deleted. **~Month 6: off EOL Python** |
| 4. Django 1.11→2.2→3.2→4.2 | Months 7–11 | Prod on Django 4.2 LTS, Python 3.11/3.12. **Fully supported stack** |
| 5. Debt paydown | Ongoing | mypy/lint ratchets; targeted refactors |

Total: **~9–12 months to a fully supported stack, with the highest-risk milestone (off Python 2)
at roughly month 6**, zero downtime, features shipping throughout, and a rollback path at every
step. An aggressive variant with a near-total feature freeze might compress this to ~6–7 months;
I'd take that trade only if a compliance deadline forces it, because freezes have real revenue
and customer-commitment costs and buy less time than they appear to.

Compare the alternative honestly: the 4-month rewrite doesn't deliver a supported stack in 4
months; based on every comparable case, it delivers *nothing* in 4 months, is still running the
EOL stack (now unmaintained *and* unloved) at month 12, and carries a serious chance of total
write-off. The incremental plan is not the cautious slow option — it is the *fast* option, once
you use realistic numbers for both.

## Part 5: What I need from leadership

1. Agreement to in-place, incremental migration in the existing repo; kill the clean-repo big-bang.
2. Accept ~60–70% feature velocity for ~2 quarters, ramping back up after the Py3 cutover.
3. Sign-off on interim security mitigations (and budget if we buy extended-support patches).
4. Sign-off on the milestone schedule above, reviewed monthly against the burn-down — and the
   commitment not to cancel at the halfway point, which is the only way this genuinely fails.
