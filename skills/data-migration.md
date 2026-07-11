---
name: data-migration
description: Data-migration skill — the highest-blast-radius task class; expand-migrate-contract, reversibility, and verification by counting
metadata:
  type: user
---

# Data Migration — Irreversible-Change Skill

## Why

Code bugs can be reverted; data bugs propagate. A bad deploy is a bad hour — a bad migration that ran against production is a bad month, because every write since compounds the corruption. Smaller models treat migrations as "just another script." This skill treats them as what they are: the highest-blast-radius change class, deserving the most paranoid process in the system.

## The Rule

**Every migration must be reversible, rehearsed, and verified by counting — before it touches production. No exceptions for "simple" migrations; `UPDATE users SET ...` with a wrong WHERE clause is simple too.**

Always Tier 2+ per tierless-router; loop-until-dry requires two consecutive clean passes here.

Boundary: the dual-write and read-switch code changes route through the normal code pipeline (and code-migration if part of a port).

## The Pattern: Expand → Migrate → Contract

Never change schema and data and code in one step. Three deploys, each independently safe:

1. **Expand** — additive only: new column/table/index exists alongside the old. Old code runs unchanged. *Reversible by dropping the new thing.*
2. **Migrate** — dual-write from code (new writes go to both shapes), then backfill history in batches. Read paths switch to the new shape behind a flag. *Reversible by flipping the flag back — the old shape is still being written.*
3. **Contract** — only after the new shape has served production traffic and verification passes: remove old code paths, then (later still) drop the old column/table. *This is the only irreversible step — it comes last, and it can wait weeks. There is no prize for dropping a column early.*

## How to Apply

Write `.claude/plans/{migration}-plan.md` before writing the migration:

```markdown
## Migration: {what changes}
**Rows affected (estimated):** {run the COUNT — write the number}
**Irreversible after:** {which exact step}

### Pre-flight
- [ ] Backup / snapshot taken and RESTORE TESTED (an unverified backup is a hope, not a backup — see infra-ops for the backup/restore rehearsal discipline)
- [ ] Rehearsed on a production-shaped copy — row counts and timing recorded
- [ ] Batch size chosen: {N rows per batch, sleep between} — never one giant transaction
- [ ] Runs against replica lag / locks checked (what does this block, for how long?)

### Verification queries (written BEFORE migrating)
- Count: {SELECT COUNT(*) old-shape} == {SELECT COUNT(*) new-shape}
- Invariants: {e.g., no NULLs in new column where old had values; sums/checksums match}
- Spot-check: {5 specific known records, verified by hand}

### Rollback
- At step 1: {exact commands}
- At step 2: {flag flip + cleanup}
- At step 3: {restore procedure + acceptable data-loss window}

### Abort criteria
{error rate, lag threshold, or count mismatch that stops the batch job automatically}
```

## Execution Discipline

- **Batches with progress logging** — resumable from the last completed batch, not from zero
- **Verify counts after every batch**, not just at the end; abort on first mismatch
- **The dual-write window is your safety net** — keep it until verification has passed *in production*, not just in rehearsal
- Migrations run at low-traffic windows, with someone watching, never on a Friday

## Anti-Patterns

- Schema change + data change + code change in one deploy ("it's all related")
- `WHERE` clauses written from memory of the schema instead of a verified query — run the SELECT version first, read the count, then UPDATE
- Testing on 100 dev rows and running against 40M production rows (rehearse at production scale)
- Dropping the old column in the same release that stops reading it
- "The migration succeeded" = "it didn't error." No — it succeeded when the verification queries pass.
- Backfilling with an unbounded UPDATE that takes a table lock for 20 minutes
