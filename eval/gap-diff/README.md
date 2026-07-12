# Gap-Diff Skill Derivation

A bottom-up method for deriving (and validating) discipline skills — the complement to
top-down authoring. Instead of writing a skill from a prior about "good discipline," you
**observe the gap** between a cheap model and a frontier model on a real task, then distill
only the *repeatable process* the frontier model used that the cheap one skipped.

## Why this is better than top-down authoring

The top-down method (how the 41 skills were first written) risks producing polished skills
for gaps that don't exist — which the eval later showed happened (single-shot bug/review
tasks have no cheap-vs-frontier gap; the skills for them don't move the needle). The gap-diff
method only produces a skill **where a measured gap exists**, and derives its content from the
frontier model's actual behavior rather than the author's imagination.

## The cycle

1. **Establish the gap.** Cheap model and frontier model each do the same real task (here:
   review a flawed tech spec) into separate files. Same prompt, no cross-reading.
2. **Diff, rigorously.** A separate agent extracts what the frontier caught that the cheap
   model *genuinely missed* (not just phrased more elaborately), and classifies each miss as
   **KNOWLEDGE** (a fact the cheap model lacked — NOT distillable) or **PROCESS** (a repeatable
   discipline it skipped — distillable). Only the process fraction can become a skill.
3. **Distill.** Turn the process deltas into a candidate skill (or a sharpening of an existing
   one). Nothing that traces to a knowledge gap goes in.
4. **Re-test.** Cheap model + the distilled skill re-does the same task.
5. **Blind-grade the close.** Did the skilled cheap review now catch what it missed bare?
   Scored against the frontier bar, blind. If yes, the skill is validated by construction.

## The model ladder (important)

Earlier evals used **Opus** as the frontier bar — a convenient proxy. But the project's
thesis is "match **Fable**." This cycle runs all three: Haiku (cheap) → Opus (proxy) →
Fable (true frontier). Two diffs result:
- **Fable vs Haiku** = the thesis-accurate gap the skill must close (the real target).
- **Fable vs Opus** = validates whether Opus was a fair proxy in all prior evals.

## Cycle 1: tech-spec review (2026-07-11)

Fixture: `spec.md` — a plausible real-time-notification-fanout design with planted
weaknesses (fire-and-forget pub/sub + polling removed, no reconnect/catch-up, no WS auth,
unspecified write-vs-publish ordering, Redis SPOF, a scaling cliff, no rollback, SSE
unconsidered).

Reviews: `review-haiku.md`, `review-opus.md`, `review-fable.md`.

### Diff result — Opus vs Haiku (the proxy gap)
**Gap: MODERATE, ~80% PROCESS / 20% KNOWLEDGE.** Bare Haiku independently caught essentially
all of Opus's blocking issues (fire-and-forget pub/sub, reconnect strategy, WS auth, sticky
sessions, SSE alternative) and even *beat* Opus on three points (broadcast fanout, per-user
connection-count DoS, WSS transport). Opus's edge was a cluster of deeper failure-path catches:
1. write-vs-publish **ordering** race (PROCESS)
2. Redis Cluster ≠ sharded pub/sub (**KNOWLEDGE** — the only non-distillable miss)
3. Redis as an unaddressed **SPOF** / no degraded mode (PROCESS)
4. **thundering herd** on deploy/mass-reconnect (PROCESS)
5. multi-device/multi-tab **cardinality** assumption (PROCESS)
6. capacity math behind the magic number "3 instances" (PROCESS)
7. push payload schema id-vs-full (PROCESS)
8. net DB-load reduction not tied back to the stated 40% goal (PROCESS)

7 of 8 misses were process. The four distillable disciplines (see `candidate-skill.md`):
1. Trace every **external dependency's own** failure, not just the service under review.
2. When two stores must agree, trace the **ordering** of writes and the crash window between.
3. Ask "**what happens when everyone does it at once**" (correlated reconnect/load spikes).
4. Challenge every **cardinality assumption and magic number**, and tie the design back to the
   doc's own stated metric.

### Diff result — three-way (Haiku / Opus / Fable)
Ran Fable too (the project's true target bar; earlier evals used Opus as a proxy). Rigorous
three-way diff:
- **Ceiling by tier** (15 real flaws in the spec): Fable ~14, Opus ~11, Haiku ~6-full.
  Ordering Fable > Opus > Haiku is real.
- **Is Opus a fair proxy for Fable?** About right — a mild lower bound. Opus lands within ~3
  substantive findings of Fable; the one important thing Fable caught that BOTH cheaper models
  missed was **mobile background delivery (needs APNs/FCM)** — a whole-platform-reasoning gap.
  So earlier Opus-bar evals weren't measuring against a badly low bar.
- **Honesty note:** the *cheapest* model (Haiku) alone caught one flaw both better models missed
  (broadcast/system-alert fanout). Capability isn't a strict superset by tier.
- **Gap composition:** ~80% PROCESS (distillable), 20% KNOWLEDGE. Through-line: *Haiku audits
  what the spec SAYS and finds it thin; Fable audits what the spec ASSUMES and finds it wrong.*

### Distillation → `candidate-skill.md` (the `spec-review` skill)
Five audits derived bottom-up from the Fable-vs-Haiku process deltas (knowledge-only gaps —
Redis-Cluster pub/sub, WS-on-mobile mechanics — deliberately excluded):
1. Dependency-failure audit (every dependency's own restart/failover/SPOF)
2. Dual-write/ordering audit (two-system writes, both partial-failure directions)
3. Correlated-event audit (what happens when it hits everyone at once)
4. Goal × population × state cross-product (the highest-leverage one — catches mobile, old
   clients, multi-device)
5. Quantify-the-claims audit (percentiles, magic numbers, net effect vs the stated goal)

### RE-TEST RESULT — the method WORKS ✅
Haiku re-reviewed the same spec WITH the distilled skill. Scored all four reviews against the
15-flaw checklist by **deterministic keyword matching** (auditable, no LLM judgment — the LLM
grader we first used hallucinated its scores and was discarded; see below):

| review | /15 |
|---|---|
| haiku bare | 8 |
| **haiku + spec-review skill** | **13** |
| opus bare | 12 |
| fable bare | 15 |

**The skill moved Haiku from 8 → 13, closing ~70% of the gap to the frontier bar and edging
past bare Opus.** It picked up exactly the audited flaws: dual-write-both-directions, thundering
herd, old-clients, mobile (APNs/FCM), multi-device. The two it still missed were the pure
KNOWLEDGE gap (Redis Cluster/sharded pub/sub — correctly excluded from the skill) and one niche
flaw (read/unread sync). Mechanism verified by reading the review: it ran the five audits.

**Conclusion: the gap-diff method produces a validated, working skill — and it's a better basis
for skill-building than top-down authoring** (it only fires where a measured gap exists, derives
content from observed frontier behavior, and respects the knowledge/process boundary automatically).

### Grader caveat (LESSONS #12, re-learned)
The first blind LLM grader returned 6.5/9.5/12/7 — claiming bare-Haiku beat Fable. Verifying its
per-flaw claims against the actual review text (grep) showed it scored against hallucinated content
(credited bare-Haiku with mobile/read-state/thundering-herd it never mentioned). Discarded; replaced
with deterministic keyword scoring. Keyword scoring is slightly generous (a hit isn't always
substantive) but applied identically to all four, so the comparison is fair. **An LLM grader needs a
keyword/execution backstop — never trust its numbers without spot-checking against the source text.**
