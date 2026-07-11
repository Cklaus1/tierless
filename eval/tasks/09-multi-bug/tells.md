# GRADER-ONLY — Task 09 tells

## The trap
There are TWO independent bugs, and the report explicitly signals both ("earlier than
limit" AND "burst way over"). A bare model typically finds the first plausible bug, fixes
it, and stops — declaring victory without re-checking that BOTH reported symptoms are
resolved. The debugging discipline's rule "two bugs can share a symptom; re-run the FULL
reproduction, not just the failing step" is exactly what this task rewards.

## The two planted bugs
**Bug A — under-limiting (the "429 too early" symptom): the refill only ever refills on a
FULL period boundary, and it's all-or-nothing.** `_refill` does nothing until `elapsed >
refill_period_s`, then jumps straight to capacity. So within a 60s window tokens are NEVER
replenished gradually — a user who spends 100 tokens in 30s is stuck at 0 until the full
60s elapses, AND because partial elapsed time is discarded (last_refill only updates on the
full-period branch), a user who makes steady requests can be throttled well before a true
100/min rate. The correct token bucket refills *proportionally*: `tokens = min(capacity,
tokens + elapsed * refill_rate)` and advances last_refill each time.

**Bug B — over-limiting/bursting (the "burst way over" symptom): the all-or-nothing refill
resets to FULL capacity after any gap > 60s, regardless of how long the gap was, AND
without capping accumulated tokens** — so after a quiet period a user gets a fresh 100
tokens on top of whatever timing, and combined with the proportional fix must be capped at
capacity. The root of B is the same broken `_refill`: "set to capacity on full period"
lets a user idle 61s then fire 100 immediately, then 60s later another 100 — but the deeper
burst is that proportional refill WITHOUT a `min(capacity, ...)` cap would let tokens
accumulate unbounded across a long idle. Correct fix caps at capacity.

Both bugs live in `_refill`. The single correct rewrite (proportional refill + cap +
always-advance last_refill) fixes BOTH. A fix that only addresses the "too early" symptom
(e.g. lowering the threshold) leaves bursting; a fix that only caps leaves the gradual-
refill problem.

## Tells (binary)
- **T1 — finds the under-limiting bug**: identifies that refill is all-or-nothing / only on
  a full period, so tokens aren't replenished gradually within the window.
- **T2 — finds the over-limiting/burst bug**: identifies that the refill resets to full
  capacity after an idle gap (and/or that without a cap tokens accumulate), enabling bursts
  over 100/min.
- **T3 — connects BOTH to the report's two symptoms**: explicitly maps its fix to *both*
  "429 too early" AND "burst over limit" — does not fix one and ignore the other. THE key
  tell. Fixing only one symptom = MISS on T3 even if that one fix is correct.
- **T4 — correct proportional-refill fix**: rewrites `_refill` to add tokens proportional
  to elapsed time, cap at capacity, and advance last_refill each call. A threshold tweak or
  a partial fix is a MISS.
- **T5 — verification across both symptoms**: proposes to test BOTH the steady-rate case
  (100/min sustained is allowed, no early 429) AND the idle-then-burst case (can't exceed
  100 in a window). Re-running the full reproduction, not just the first symptom.
- **T6 — no false fixes**: doesn't "fix" by raising capacity, adding sleeps, or removing the
  limiter's teeth; recognizes both symptoms trace to the one broken `_refill`.

## Skill lineage
debugging (primary — "re-run the FULL reproduction, two bugs share a symptom"; the skill
literally warns against fixing one symptom and stopping). Skills arm gets debugging.
Hypothesis: bare models find Bug A OR Bug B, fix it, stop → MISS T3. Skills arm, following
"re-run the full reproduction," should catch that the second symptom remains → gain T2/T3/T5.
Headroom: HIGH — the "stop after the first bug" failure is exactly what bare models do.
