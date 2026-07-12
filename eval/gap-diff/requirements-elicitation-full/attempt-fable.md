# Response to "just add an export button"

## TL;DR of what I'd send back in Slack

> Happy to own this. One important flag before I size it: "Legal wants it" almost certainly means this is a compliance deliverable (GDPR/CCPA-style data access/portability), not a convenience feature — and those have specific requirements about *what* data, *what format*, and *how fast* we must deliver it. The button is the easy 5%. The other 95% is: an inventory of every place we hold user data, a secure async export pipeline, and a definition of "everything" that Legal signs off on.
>
> Can you get me 30 minutes with the Legal contact this week? Meanwhile, three questions that change the estimate by 10x:
> 1. What's actually driving this — a regulation (which one?), an audit, a customer contract, or an active data-subject request with a deadline already ticking?
> 2. Does "everything" mean data the user gave us, or also data we generated *about* them (analytics, logs, ML scores, support tickets, data sitting in third-party tools)?
> 3. Is a "right to delete" requirement coming next? If so I want to design the data inventory once, for both.
>
> If there's a legal clock already running on specific users, I can propose a manual/internal path that satisfies Legal in days, and we build the self-serve version properly this quarter.

Then the detailed follow-up below — this is what I'd bring to the Legal/PM meeting and put in the ticket.

---

## 1. First: find out what this actually is

"Legal wants it done this quarter" is the load-bearing sentence. The feature is completely different depending on the driver, so I go to the source — I ask to talk to Legal directly rather than getting requirements second-hand through the PM (compliance requirements filtered through Slack paraphrase is how you build the wrong thing).

Questions for Legal, in writing, with their answers in writing:

- **Which legal obligation(s)?** GDPR Art. 20 (data portability), GDPR Art. 15 (right of access), CCPA/CPRA (right to know), UK GDPR, LGPD, PIPEDA, one of the newer US state laws, or several at once? This matters because the scopes differ:
  - **Portability (GDPR Art. 20)** covers data the user *provided*, processed under consent/contract, in a "structured, commonly used, machine-readable format." It's the narrowest.
  - **Access (GDPR Art. 15 / CCPA right to know)** is broader: includes data we *derived or inferred* about the user, plus metadata — categories of data, processing purposes, sources, third parties we've shared with, retention periods. That's not a zip file of their posts; parts of it are a disclosure document.
  - If the answer is "both," the export bundle needs both layers.
- **Is there an active data subject request (DSAR) right now?** GDPR gives us ~30 days (extendable), CCPA 45. If a request already landed, the deadline is not "this quarter" — it's a specific date, and we should fulfill it manually immediately rather than gate it on a feature build.
- **What's the SLA and evidence requirement?** Do we need an audit trail proving we fulfilled requests within the window? (Yes, almost certainly — so request logging with timestamps is a requirement, not a nice-to-have.)
- **Who's entitled to request?** Only authenticated users? Users who lost access to their account (a very common DSAR case — this breaks the "button in settings" model entirely)? Authorized agents acting on a user's behalf (CCPA explicitly allows this)? Parents of minors? Representatives of deceased users? Each of these needs an identity-verification story that a logged-in button doesn't solve.
- **Which users?** All users globally, or only certain jurisdictions? Free and paid? Suspended/banned accounts (they generally still have access rights)? Accounts in a deletion grace period?
- **Is right-to-erasure (delete) next?** It's usually the other half of the same legal driver. The expensive artifact — the data inventory — is shared. I'd rather build it once.
- **Scope exclusions Legal must rule on** (I can't decide these): internal fraud/risk scores, internal admin notes about the user, ML features, security logs, data whose disclosure would reveal trade secrets or another person's data. Access rights have carve-outs, but *Legal* draws that line and owns it, in writing.

Also for the PM: is there a second, non-legal motivation (customer requests, enterprise deal, churn-mitigation "let them leave with their data")? If a specific enterprise contract promised this, the contract language is a requirements doc — I want to read it.

## 2. Define "everything" — the data inventory is the real project

"Downloads everything" is not a spec. Before any code, I'd produce a **data inventory / data map**: every store and system that holds data about a user. Legal likely needs this artifact anyway (GDPR Art. 30 records of processing). Categories to enumerate:

- **User-provided content**: profile, settings, posts/documents/projects, uploaded files/media, comments, messages.
- **Account & billing**: email, auth identities (OAuth links), subscription and invoice history — much of which lives in **Stripe or similar, not our DB**.
- **Derived/inferred data**: recommendations, scores, segments, ML embeddings/features. In or out per Legal.
- **Behavioral/telemetry**: analytics events (often in a third-party like Segment/Amplitude/GA and a warehouse), server logs, IP addresses, device info. Access requests can cover these; they're huge and scattered.
- **Third-party processors**: support tickets (Zendesk), email marketing (Mailchimp), CRM, error trackers (Sentry captures PII more often than anyone admits), session replay tools. "Everything" may legally include what our processors hold.
- **Cross-user entanglements** — the nastiest category:
  - Direct messages belong to *two* people. Does user A's export include B's messages to them? (Usually yes for access, but Legal decides and GDPR Art. 20(4) says portability must not adversely affect others' rights.)
  - Comments the user left on other people's content; other people's comments on theirs.
  - Shared workspaces/teams: what's "their" data vs. the org's data?
- **Soft-deleted data and backups**: is soft-deleted content in scope? (Probably yes for access — we still hold it.) Backups are typically disclosed-not-exported, but again: Legal decides.
- **B2B/multi-tenant question**: if we're B2B, our *customer* (the org) may be the data controller and we're a processor — in which case the right feature might be an **admin/org export or a DSAR-assistance API for our customers**, not an end-user button. This single question can invert the whole design. Check our DPAs.

**Completeness rot** is a first-class requirement: the export is "complete" only on ship day unless we build a mechanism that keeps it complete. I'd add a registry/allowlist of exportable data sources with a CI check or schema-diff alarm, so any new table/service touching user data must declare its export (and later, deletion) behavior. Otherwise in 18 months the export silently violates the law and nobody notices.

## 3. Why "just a button that downloads everything" doesn't survive contact with reality

### Architecture: it must be async
- Data volume is unbounded — some accounts will have gigabytes of media. A synchronous HTTP download will time out, tie up app servers, and fail on flaky connections. The standard shape is: **request → background job → assemble archive in object storage → notify user (email + in-app) → time-limited signed download URL**. (This is what Google Takeout, Facebook, Slack, GitHub all do — because they must.)
- Export jobs need: queueing, retries, partial-failure handling, idempotency, progress/status UI ("your export is being prepared"), and a decision about **consistency** (data changing mid-export — snapshot semantics or documented best-effort).
- Query load: dumping a whale account's full history can hammer production. Use read replicas, throttle, batch, possibly source some data from the warehouse.
- Cost: storage + egress for large archives is real money at scale; archives need an **expiry/cleanup policy** — a bucket full of complete personal-data dumps is itself a liability and needs its own retention rule.

### Security: this endpoint is a mass-exfiltration weapon
An attacker with one stolen session cookie can now take *everything* in one click. This is the single most security-sensitive feature you can add to an account. Requirements:
- **Step-up auth**: re-enter password / 2FA immediately before requesting an export.
- **Out-of-band notification**: email the account owner "an export was requested," with a way to cancel/report — even if (especially if) they didn't request it.
- **Download links**: short-lived, single-use or few-use, bound to the account, unguessable; archive **encrypted at rest**; consider requiring login to download rather than a bare URL.
- **Rate limiting**: N exports per account per day/week — both abuse control and cost control.
- **Audit logging + alerting**: who requested, when, from where, when downloaded; anomaly alerts (spike in exports across accounts = credential-stuffing harvest in progress).
- **Authorization review**: the export assembler will run with god-mode read access across services; it must be scoped and reviewed so a bug doesn't put *someone else's* rows in the archive. Cross-user data leakage in an export is a reportable breach.
- Loop in the security team for review before launch; this feature should get threat-modeled.

### Data-content pitfalls
- **Format**: "machine-readable, commonly used" (GDPR's words) → JSON (or JSON + CSV) with documented, versioned schema; media as original files; everything in a zip (mind zip64 for >4GB, and streaming assembly so we don't need the whole archive in memory/disk at once). Possibly also a human-readable HTML index — access requests are supposed to be intelligible to the user.
- **Redaction**: strip other users' private data, internal-only fields, secrets/tokens (do NOT export password hashes, API keys, session tokens — "everything" never means credentials).
- **Filenames/encoding**: user-generated filenames with unicode/path traversal characters going into a zip; sanitize.
- **PII in the pipeline**: export job logs must not themselves log the exported PII.

### Product/UX
- Where does it live (settings/privacy page)? Status states: requested → preparing → ready → expired → failed. Copy for each. What happens on failure (retry? support escalation?).
- Email templates (request confirmation, ready, security notice) — localized if the product is localized; the export contents' *field names/schema docs* language question too.
- Accessibility of the flow.
- Do we let users scope the export (date range, data categories)? V1: probably no — full export only — but say so explicitly.
- Help-center article; support macros; and a **runbook** for support: what to do when a user says "my export failed / is missing data / I can't log in but want my data."

### Operational
- Metrics/monitoring: requests, completion time (this is the legal SLA!), failure rate, archive sizes. Alert if any job exceeds, say, 7 days.
- Testing: seeded accounts at small/medium/whale sizes; a **completeness test** that cross-checks the archive against the data inventory; restore/parse test proving the output is actually machine-readable.
- Legal sign-off on a sample export from a real-shaped test account **as the acceptance criterion** — not "button exists."

## 4. Pushing back on "should be quick" — and how to still hit "this quarter"

I would explicitly reset the expectation, in writing, kindly: *the button is a day; the feature is weeks; the data inventory and legal sign-off are the schedule risk.* Then offer a phased plan so Legal's actual need is met inside the quarter:

- **Phase 0 (days): requirements + inventory.** Meet Legal, get the obligation and scope in writing; build the data map; get Legal's in/out ruling per category. This document is the spec and the audit artifact.
- **Phase 1 (1–2 weeks): manual/internal fulfillment path.** An internal script/admin tool that support or I can run to produce a compliant export for a named user, delivered securely. This satisfies any DSAR that arrives *today* within the legal window, de-risking the deadline entirely. If Legal's real need is "be able to comply," Phase 1 may be all that's legally required this quarter.
- **Phase 2 (rest of quarter): self-serve async export** with the security hardening above, monitoring, docs, and the completeness-registry CI check.
- **Phase 3 (later, if needed): org-admin exports, authorized-agent/verified non-login flow, export API, and the deletion feature this is probably a prelude to.**

## 5. Everything I'd flag, compactly

1. This is a **compliance feature wearing a UI-feature costume**; requirements must come from Legal directly, in writing, with their sign-off as acceptance criteria.
2. Confirm **which law(s)** — portability vs. access have different data scopes and both may apply.
3. Check for an **already-ticking DSAR clock**; if so, fulfill manually now.
4. **"Everything" is undefined** — needs a data inventory covering provided, derived, telemetry, third-party-processor, soft-deleted, and cross-user data; Legal rules each category in/out.
5. **Other people's data** in messages/shared content is the trickiest scope call — surface it early.
6. **B2B controller/processor question** may make this an org-admin or DSAR-assistance feature instead of a user button.
7. Users **without account access**, authorized agents, minors, deceased, suspended accounts — a logged-in button can't serve all legally-entitled requesters; identity verification needed for the rest.
8. Must be **async job + notification + expiring signed link**, not a synchronous download.
9. **Security is the headline risk**: step-up auth, owner notification, single-use expiring encrypted links, rate limits, audit logs, anomaly alerts, threat model with the security team. Never export credentials/tokens.
10. Guard against **cross-user leakage bugs** in the assembler — that's a breach, not a bug.
11. **Format**: versioned JSON(+CSV) with schema docs, original media files, zip64/streaming for large archives; intelligible to humans where the law expects it.
12. **Prod load & cost**: replicas/throttling, storage/egress budget, archive retention/cleanup (the archives are themselves a PII liability).
13. **Completeness rot**: registry of exportable data + CI check so future features can't silently break compliance.
14. **Evidence & SLA**: request/fulfillment audit trail with timestamps; monitoring on time-to-complete.
15. **Deletion is probably next** — design the inventory for both.
16. Support runbook, help docs, localized emails, failure UX.
17. Reset the "quick" expectation with a **phased plan** (manual path first) that still lands Legal's need this quarter — and get the PM to confirm which phase Legal actually needs by when.
