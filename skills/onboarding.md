---
name: onboarding
description: Onboarding skill — end-to-end system walkthrough for new developers joining a project
metadata:
  type: user
---

# Onboarding — New Developer Walkthrough Skill

## Why

Asked to onboard someone, smaller models dump a documentation index — a list of files and links — instead of a guided path that ends in a real contribution. New developers then waste days (sometimes weeks) understanding a codebase before their first meaningful change. This skill replaces the index with a structured, end-to-end walkthrough from the perspective of someone seeing the system for the first time.

## The Rule

**Every project must have an onboarding path.** The onboarding walkthrough takes a new developer from "zero knowledge" to "first meaningful contribution" in a single session. It is not a documentation index — it is a guided journey through the system.

## How to Apply

When a new developer joins, or when reviewing a project for the first time:

1. Write the onboarding walkthrough to `.claude/plans/{project-name}-onboarding.md`:

```markdown
## Onboarding: {project-name}

### 1. Run it (5 minutes)
- `cd /path/to/project`
- `./scripts/project-init` (or equivalent setup)
- `npm run dev` (or equivalent)
- Open http://localhost:3000 — you should see {expected output}

### 2. Break it (5 minutes)
- Change {this specific thing}
- Observe {what happens}
- This teaches you how {component A} connects to {component B}

### 3. Fix something (15 minutes)
- Find the {smallest bug or TODO} in {file:line}
- Fix it
- Run `npm test` to verify nothing broke
- This teaches you the test and review workflow

### 4. Understand the architecture (10 minutes)
- {file}: {role} — this is the entry point
- {file}: {role} — this handles {responsibility}
- Data flows: {describe the main data path}

### 5. Your first real task
- {specific, small, real task that teaches the system}
```

2. Walk the new developer through each step.
3. Answer questions as they arise — update the walkthrough with clarifications.

## What Makes a Good Onboarding

- **It's a journey, not a table of contents.** Each step builds on the previous one.
- **It's time-boxed.** Each section has an estimated duration. If a section takes more than its estimate, the walkthrough is wrong — simplify.
- **It ends with a real contribution.** Not a toy example, not a test — something that actually matters to the project.
- **It teaches by doing.** The "break it" step is critical — understanding how things work is easier than understanding how they're organized.

## Anti-Patterns

- Onboarding that is just a link to docs
- Steps that say "read the code" without specifying which files
- Time estimates that are wildly optimistic ("understand the codebase in 10 minutes")
- Ending with "now go find something to work on" — that's not onboarding, that's abandonment
- Including setup steps that require permissions or tools the developer doesn't have

## Walkthrough Checklist

Before delivering the walkthrough, verify:
- [ ] Each step has a time estimate
- [ ] Step 1 runs from a fresh clone
- [ ] The first-task section names a real file
- [ ] Walkthrough validated by executing step 1 yourself

For the product's customer-facing first-run experience, see icp-onboarding.