---
name: spec-review
description: Spec-review skill — review a design doc for what it ASSUMES, not just what it says: trace every dependency's failure, every dual-write ordering, every correlated event, and every goal against every population and deployment state
metadata:
  type: user
---

# Spec Review — Audit the Assumptions, Not the Prose

## Why

A cheaper model reviewing a design doc audits **what the doc says** — it reads each section,
notices what's thin, and asks for more detail. It produces a competent, checklist-shaped review
that catches the headline flaws (this delivery is unreliable, there's no auth, the rollout is a
hard cutover). What it misses are the **second-order failures that live in what the doc
assumes** — the dependency whose own failure was never traced, the two writes whose ordering was
never checked, the "one per user" that's really "one per device," the goal that silently breaks
for a platform nobody mentioned. This skill is derived empirically: it's the exact set of
disciplines a frontier review applied that a cheap review skipped, on a real spec, measured by
diff (see `eval/gap-diff/`). It is *process*, not knowledge — it makes the reviewer ask the
questions; answering some still needs domain facts, but the questions are where the gap was.

## The Rule

**Review what the doc ASSUMES, not just what it says.** For every claim, dependency, number, and
goal in the spec, run the five audits below. A finding is not "this section is thin" — it is
"this specific assumption is wrong / unhandled, and here's the failure it causes."

## The Five Audits

Run each against the whole doc; write findings as concrete failure scenarios.

### 1. Dependency-failure audit
List every external thing the design leans on — every datastore, broker, queue, load balancer,
third-party service. For **each one**, ask: what happens when *it* restarts, is deployed, is
partitioned, or fails over? Is it a single point of failure? What is the explicit degraded mode?
(The cheap review traces the failure of the *service under review* but forgets the dependencies
it rests on — e.g. reasons carefully about the app tier and never asks what happens when the
message broker is down.)

### 2. Dual-write / ordering audit
Find every place where **one logical operation writes to two systems** (e.g. commit a DB row AND
publish an event; update a cache AND the source; write two tables). For each, check the ordering
and the partial-failure outcome in **both** directions: A-succeeds-B-fails, and B-succeeds-A-fails.
Name the resulting inconsistency (ghost record? silently-lost event? stale read?). State which
write must happen first and what a crash between them does.

### 3. Correlated-event audit
For every disruptive event (deploy, crash, restart, network blip, cache flush), ask what happens
when it hits **all** affected clients/connections/workers **at once**, not just one. Correlated
failure is the default in any stateful or connection-oriented tier: mass reconnect storms, cache
stampedes, retry pile-ups. The fix is usually backoff-with-jitter, draining, or staggering — name it.

### 4. Goal × population × state cross-product (the highest-leverage audit)
Take every **stated goal** and cross it against (a) every user population / platform and (b) every
deployment state — then find where it breaks:
- "instant" × mobile-backgrounded app → a persistent socket delivers nothing; needs platform push
- "turn off the old path" × already-shipped old clients (releases aren't atomic) → breaks them
- "one connection per user" × multi-tab / multi-device → per-connection counting, cross-device
  state divergence
This one audit is what most separates a frontier review from a cheap one — it catches the
requirements-level gaps that no amount of reading the existing sections surfaces.

### 5. Quantify-the-claims audit
Convert every quantitative or superlative claim into a measurable target before accepting it.
"Fast"/"sub-second" → which percentile (p50? p99?). "Cuts load 40%" → re-derive the net *after*
your own recommended changes (a catch-up-on-reconnect step can add reads back). "Scales" → to what
number, and where does it break. Every magic number ("3 instances") → where did it come from, does
it give N+1 headroom?

## How to Apply

1. Read the spec once for comprehension.
2. Run the five audits, writing each finding as: **{the assumption} → {the concrete failure} →
   {the required change}**, tagged blocking / significant / minor.
3. Write the review to `.claude/plans/{doc}-review.md` (or inline), blocking issues first.
4. Verdict: is this buildable as-is, and if not, which findings are the blockers.

## Anti-Patterns (gaming behaviors)

- A review that restates the doc's sections and calls them "thin" without naming a failure
- Auditing the service under review but not the dependencies it rests on (the #1 real gap)
- Accepting every number and goal at face value ("sub-second" with no percentile)
- Listing "multi-device?" as an open question instead of tracing what actually diverges
- Finding only what the doc *says* is incomplete, never what it *assumes* is wrong

## Verification

Done means: every dependency has a failure-mode line; every dual-write has an ordering verdict;
every stated goal was crossed against platforms and deployment states; every quantitative claim
has a measurable target or an explicit "unspecified — must define." A review missing any of these
audits is incomplete, not done.

## Provenance
Derived by gap-diff (`eval/gap-diff/tech-spec-review/`): the 5 audits are the distillable PROCESS
deltas between a Haiku review and a Fable review of the same spec, with knowledge-only gaps
(Redis-Cluster pub/sub sharding, WS-on-mobile mechanics) deliberately excluded. Through-line:
**audit what the spec assumes, not what it says.**
