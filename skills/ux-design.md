---
name: ux-design
description: UX-design skill — flow design before screen design: user journeys, friction audit, error recovery, and interaction contracts
metadata:
  type: user
---

# UX Design — Flow & Interaction Skill

## Why

ui-design makes screens look right; UX design makes the *path through them* work. Smaller models design screens in isolation — each one fine, but the journey has dead ends, lost state, and no way back. This skill forces flow design before screen design: the flow map here lands before ui-design's tokens or any screen work begins — that ordering is the contract between the two skills.

Boundary with icp-onboarding: icp-onboarding defines WHICH win and path; this skill maps HOW each step behaves.

## The Rule

**Before building any screen, map the flow it belongs to — from the user's trigger to their goal — including every failure exit.** Screens are implementation details of flows.

## How to Apply

### 1. Map the flow

Write `.claude/plans/{feature}-flow.md`:

```markdown
## Flow: {name}
**User:** {who} **Trigger:** {what makes them start} **Goal:** {done = what}

### Steps
1. {screen/state} → user does {action} → {next}
   - failure: {what can go wrong} → {where they land, what they see, how they recover}
2. ...

### Exits
- Success: {end state — what confirms it}
- Abandon: {what happens to their partial work}
- Error: {every step's failure path leads somewhere designed}
```

### 2. Friction audit

Count for the primary path: steps, required inputs, decisions. Then cut:
- Every input either derivable, defaultable, or deferrable? Defer it.
- Can the user see progress and current position at every step?
- Optimize for the frequent case; move rare options behind "advanced"

### 3. Interaction contracts

Every action the user takes must honor four promises:
- **Feedback within 100ms** — press states, spinners after 400ms, skeletons for full-screen loads
- **Reversibility** — destructive actions get undo (preferred) or confirmation (fallback); confirmation copy states what's lost ("Delete 3 projects?" not "Are you sure?")
- **State preservation** — navigation away and back, refresh, and network blips don't destroy typed input
- **Honest affordances** — things that look tappable are; disabled things say why

### 4. Error recovery design

For each failure in the flow map, design the recovery, not just the message:
- Say what happened in the user's vocabulary, what was (not) saved, and the one action to take next
- Validation errors appear at the field, at blur or submit — never only in a toast
- Never dead-end: every error state has a path forward or back

## Review Checklist

- [ ] Flow map exists and every failure edge lands somewhere designed
- [ ] Primary path step count justified (each step earns its existence)
- [ ] Back button works at every step without data loss
- [ ] Slow-network walkthrough: throttle and watch what the user sees at each moment — or trace the code path for each loading state when you can't drive a browser
- [ ] A first-time user can tell, at each screen, where they are and what to do next

## Anti-Patterns

- Designing the success path and letting errors "fall out" of the implementation
- Confirmation dialogs as a substitute for undo
- Progress indicators that lie (fake percentages, spinners on instant actions)
- Asking for information before it's needed ("create an account" before showing value)
- Toasts as the only record of important outcomes — they vanish; receipts should persist
