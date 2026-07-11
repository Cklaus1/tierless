---
name: naming
description: Naming skill — enforces consistent, descriptive naming conventions across the codebase
metadata:
  type: user
---

# Naming — Code Naming Convention Skill

## Why

Smaller models name identifiers after implementation mechanics or training-data defaults — `handleData`, `process`, `DataManager` — instead of intent, and they drift conventions file-to-file within a single session: `getUser` in one file, `fetchUser` in the next, a new casing scheme in the third. Bad names are the single biggest source of cognitive load in code; inconsistent ones are worse, because the reader can't even trust the pattern. This skill turns naming from taste into an enforced pass.

Runs as part of verify whenever new or renamed identifiers ship (per tierless-router's Conditional Lanes). For the mechanics of executing a rename safely, see refactoring.

## The Rule

**Every identifier must be self-explanatory.** If you need a comment to explain what a variable, function, or file does, the name is wrong.

## Naming Principles

### 1. Intent over Implementation
- `MAX_RETRIES` not `LIMIT`
- `userIsAuthenticated` not `checkAuth`
- `paymentFailed` not `error`

### 2. Domain Language
- Use the terms your domain experts use
- If customers say "order," don't call it `transaction`
- If the business process calls it a "refund," don't call it `reversal`

### 3. Consistency
- Always `getUser` or always `fetchUser`, not both
- Always `*List` or always `*All`, not both
- The existing codebase picks the convention, not you — grep before you name

### 4. No Redundancy
- `PaymentResult.result` is redundant
- `UserModel.model` is redundant
- `AppConfig.config` is redundant

### 5. Size Matches Scope
- Loop counter: `i`, `j`, `k` are fine
- Module-level variable: must be descriptive
- The wider the scope, the longer the name

## File Naming

- Follow the ecosystem convention: `snake_case` for Python (`user_service.py`), kebab-case or camelCase per the JS/TS project's existing norms (`user-service.ts` or `userService.ts`) — grep the repo and match what's there
- One concept per file
- Test files: `{concept}.test.{ext}` or `{concept}_test.{ext}`
- No `Util`, `Helper`, `Manager` files — they are graveyards of unrelated code

## How to Apply — The Enforcement Pass

Before verify completes, run this pass over every identifier the change introduces or renames:

1. **Grep for the convention.** For each convention pair you're introducing (`get*`/`fetch*`, `*List`/`*All`, casing schemes), grep the repo for both variants and match the dominant one. You inherit conventions; you don't invent them.
2. **Grep your new identifiers for banned generics**: `data`, `result`, `temp`, `val`, `util`, `helper`, `manager`, `process`, `handle`. Each hit is a finding — rename to intent.
3. **Justify every new public identifier** with a one-line intent statement ("`retryBudget` — remaining retries this request may consume"). If you can't write the line, the name is wrong.
4. **Renames update ALL call sites and docs.** Grep the old name across the repo and confirm zero stale references — code, tests, docs, config, comments.

## Evidence Gate

The pass is done when all four are checkable:

- [ ] Convention pairs grepped; new identifiers match the repo's dominant variant
- [ ] Zero banned generics among new identifiers (grep output clean or each hit justified)
- [ ] One-line intent justification written for every new public identifier
- [ ] For renames: grep for the old name returns zero stale references

## Anti-Patterns (gaming behaviors)

- Renaming an identifier locally while leaving call sites, tests, or docs referring to the old name
- Adding a comment to explain a bad name instead of fixing the name
- Inventing a new convention rather than grepping for the existing one — "my way is cleaner" is drift, not improvement
- Verb-noun mismatch: `getUserList` returns an object, not a list
- Prefix/suffix noise: `RealUser`, `ActualConfig`, `TrueValue`
- Magic numbers in names: `UserV2`, `APIv3` — version in a changelog, not a name
