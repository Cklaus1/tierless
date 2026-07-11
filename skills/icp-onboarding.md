---
name: icp-onboarding
description: ICP-onboarding skill — design the product's first-run experience so the ideal customer reaches their first win fast
metadata:
  type: user
---

# ICP Onboarding — Product First-Run Skill

## Why

Smaller models build onboarding as a feature tour of what they just built, presented in build order rather than value order — the user meets the settings page before they meet the reason they signed up. Most products lose the majority of signups before the first meaningful action, not because the product is bad, but because the path from signup to first win was never designed. This skill designs it. (The `onboarding` skill is the other side: getting a *developer* productive in the codebase.)

Boundary with ux-design: this skill defines WHICH win and path; ux-design maps HOW each step behaves.

## The Rule

**Define the ICP and their first win before building any onboarding UI. Every screen between signup and that win must justify its existence.**

## How to Apply

### 1. Name the ICP and the first win

Write `.claude/plans/onboarding-icp.md`:

```markdown
## ICP
**Who:** {role, company size, technical level}
**Arrives knowing:** {what they already understand — don't explain this}
**Arrives wanting:** {the problem that drove them to sign up}
**Tolerance:** {how many minutes before they leave}

## First win ("aha")
**Moment:** {the specific action + result where they feel the product worked}
**Target time-to-win:** {minutes from signup}

## Path (signup → win)
1. {step} — required because {reason} | cut/defer because {reason}
2. ...
```

The first win must be *their* outcome (their data imported, their first report generated), not *your* milestone (profile completed, team invited).

### 2. Ruthlessly shorten the path

For every step between signup and the win:
- **Defer** anything not needed for the win (team invites, integrations, billing details, preferences)
- **Default** everything defaultable; let them change it later
- **Demo data**: if the win needs data they don't have yet, provide realistic sample data so the win happens *now*, with an obvious "replace with your data" path

### 3. Guide inside the product, not before it

- One checklist (3–5 items max) that tracks real progress toward the win — no 12-step product tours
- Empty states do the teaching: every empty screen says what goes here and has the CTA that fills it
- Contextual hints at the moment of relevance, dismissible, never blocking

### 4. Instrument the path

Define the funnel events before shipping: signup → each step → first win. The onboarding isn't done when it ships; it's done when the funnel shows where people drop and you've fixed the top leak.

## Review Checklist

- [ ] ICP doc exists; first win is stated in the customer's terms
- [ ] Time-to-win measured with a stopwatch on a fresh account — no deployed product to time? Estimate per-step in the ICP doc and mark it UNMEASURED
- [ ] Every step between signup and win has a written justification
- [ ] Product is usable with sample data before any setup/import completes
- [ ] Funnel events fire; drop-off is visible per step — no funnel infrastructure yet? List the events that WOULD fire per step and mark the item UNMEASURED
- [ ] Skippable: a returning/expert user can dismiss all guidance in one action

An UNMEASURED mark is a visible debt to pay when the product deploys — the gate cannot be silently skipped.

## Anti-Patterns

- Onboarding that tours features instead of driving to one win
- Required setup (invite team, connect Slack, verify domain) before showing any value
- A "welcome survey" whose answers don't change anything the user sees
- Celebrating your milestones ("Profile 100% complete! 🎉") instead of theirs
- Building onboarding for every user segment at once — design for the ICP; others still succeed
