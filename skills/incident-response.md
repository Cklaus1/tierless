---
name: incident-response
description: Incident-response skill — production-down discipline: stabilize first, diagnose second, fix third; no panic-driven changes
metadata:
  type: user
---

# Incident Response — Production-Down Skill

## Why

Under incident pressure, smaller models (and humans) reach for the first plausible fix and push it to production — turning one incident into two. Incident discipline is the opposite of normal-work discipline in one crucial way: **you are not trying to fix the bug, you are trying to stop the bleeding.** Root cause comes later, calmly, via the debugging skill. This skill enforces that ordering.

## The Rule

**Mitigate first, diagnose second, fix third. During an incident, the only changes allowed are reversions and mitigations — never novel code.**

## The Loop

### 1. Assess (first 5 minutes)
- What is the user-visible impact? (errors? slowness? wrong data? — wrong data is the worst; consider stopping writes)
- Since when? (the start time is your best diagnostic clue)
- Blast radius: all users or a segment? one feature or everything?
- Write these four answers down as the first timeline entry — they anchor every later decision.

### 2. Mitigate — reach for the boring levers, in this order
1. **What changed?** Deploys, flags, config, dependencies, traffic in the window before start-time. The answer is usually here.
2. **Revert it.** Roll back the deploy, flip the flag off. You do not need to understand *why* it broke to revert it. Reverting is not admitting defeat; it's the fastest mitigation that exists.
3. No recent change? Degrade gracefully: disable the affected feature, shed load, fail over, scale up.
4. **Novel code under pressure is how incidents compound.** If mitigation truly requires new code, it ships as the smallest possible diff, reviewed by a second set of eyes even mid-incident.

### 3. Verify the mitigation
Watch the same signal that told you about the incident. "I reverted" ≠ "it recovered." Confirm error rates/latency return to baseline, and say so explicitly with the metric.

### 4. Log as you go
Keep a running timeline in `.claude/plans/{date}-{slug}-incident.md`: timestamped observations, actions, and effects. Two sentences per entry. During the incident it prevents repeated dead-ends; after, it becomes the postmortem's spine. Memory under adrenaline is fiction.

### 5. Afterwards — the calm loop
- Root-cause via the **debugging** skill (reproduce, hypothesize, prove) — now with no time pressure
- The real fix routes through the normal pipeline (fable-discipline tier, verify, review) — incident fixes get *more* scrutiny, not less
- Blameless postmortem from the timeline: contributing causes (plural — there's never just one), detection gap (could we have known sooner?), and action items with owners
- Add the regression test and, if detection lagged, the missing alert

## Anti-Patterns

- Debugging the root cause while production burns (mitigate first; the "why" can wait an hour)
- Pushing a speculative fix instead of reverting the suspect change ("the rollback takes 10 minutes, my fix takes 2" — your fix also takes 3 more incidents)
- Fixing the symptom and closing the incident without a postmortem ("it recovered on its own" = it will return on its own)
- Multiple people/agents changing production concurrently without coordinating — one driver, others observe and verify
- Postmortems that end at "human error" (the process let the error through; fix the process)
- Skipping the timeline because you're busy — the timeline is what keeps you from trying the same dead-end twice
