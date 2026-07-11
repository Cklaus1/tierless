# Hard-Tasks Calibration (2026-07-11)

Four deliberately-hard single-shot tasks were built to give the model×skills grid the
headroom it lacked (the v2 grid had every arm at 0.85–1.0 on 5/6 tasks — see
`results/SCORES.md`). Each was **headroom-checked against bare Haiku BEFORE being added to
the graded set** — dogfooding the `verify` skill (observe, don't assume).

**Result: bare Haiku aced all four.** They are NOT in the graded grid. They live here as
calibration evidence: proof of where a strong small model's ceiling is.

| Task | Trap it targets | Bare-Haiku result | Verdict |
|---|---|---|---|
| 08-concurrency-bug | TOCTOU check-then-act race behind a lock that "looks right" | ~5/6 — named TOCTOU, gave the interleaving, explained why single-client tests miss it, correct fix | too easy |
| 09-multi-bug | two independent bugs; does the model stop after the first? | ~6/6 — found BOTH bugs, mapped each to its reported symptom | too easy |
| 10-second-order-security | stored/second-order shell-injection + XSS behind "validated elsewhere" bait | 6/6 + bonus — caught both, rejected the framing, gave payloads, found an unplanted SMTP-injection too | too easy |
| 11-migration-trap | expand/migrate/contract with 5 hidden hazards incl. the `updated_at`-not-a-settle-time trap | ~6/7 + bonus — built the trigger, reasoned about old servers mid-deploy, used CONCURRENTLY, inventoried external readers, flagged enum locking; missed only the updated_at subtlety | too easy |

## Why this is a finding, not a failure

Making the gotcha more obscure would only test trivia recall — which a modern small model
has in depth — not whether *discipline* helps. Single-shot "spot-the-bug / review-the-code /
plan-the-migration" tasks are a **ceiling category** for a strong cheap model. Chasing harder
puzzles is a treadmill.

See LESSONS #14 for where headroom actually lives:
- process over a long horizon (build-loop / task-07),
- coverage/thoroughness graded by count ("found 3 vs found 9"),
- confidently-wrong traps (plausible answer is affirmatively incorrect),
- adversarial verification (loop-until-dry vs one pass).

## Reuse

These tasks are honest and well-constructed — they're just calibrated for a *weaker* model.
If a much smaller/older model (or a distilled 3–7B local model, a plausible ICP deployment
target) is ever added to the ladder, re-run these against it; they likely DO discriminate
there. Keep; don't delete.
