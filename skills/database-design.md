---
name: database-design
description: Database-design skill — discipline for schema, queries, and data integrity: constraints in the database, queries proven with EXPLAIN, scale numbers written down
metadata:
  type: user
---

# Database Design — Data Layer Skill

## Why

The database outlives every application that talks to it. Smaller models design schemas as an afterthought of the code — nullable everything, integrity enforced "in the app," indexes added when someone complains — and each shortcut becomes permanent the moment production data arrives. This skill treats the data layer as what it is: the part of the system where mistakes compound daily and cleanups require the data-migration skill's full ceremony.

## The Rule

**Integrity lives in the database, not in application code.** The app has bugs, gets bypassed by scripts and future services, and is rewritten; constraints survive all three. (Proving queries with EXPLAIN is the verification gate — see the end of this skill.)

## How to Apply

### 1. Model the data before the code

For each entity, fill this template in the plan-mode artifact:

```markdown
### {entity}
- **Key:** {natural vs surrogate, uniqueness constraints}
- **Nullability:** {per column: NOT NULL or why NULL is a valid state}
- **FKs + delete behavior:** {each relationship: CASCADE / RESTRICT / SET NULL, chosen on purpose}
- **Constraints:** {CHECKs, enums via lookup table}
- **Scale numbers:** {rows now, rows in a year, hottest queries}
```

- Natural key vs surrogate key, and the *uniqueness constraints that encode business rules* (`UNIQUE(org_id, email)` is a requirement, not an optimization)
- Nullability as a decision per column — NULL means "unknown/absent" is a valid state; if it isn't, say NOT NULL
- Relationships with real foreign keys, and the delete behavior chosen on purpose (CASCADE / RESTRICT / SET NULL each encode a business decision)
- Enums/status fields constrained (CHECK or lookup table), not free text
- Expected scale: rows now, rows in a year, hottest queries — numbers, not adjectives (this drives indexing and partitioning decisions later; guessing costs a migration)

### 2. Constraints are the spec that can't be bypassed

Everything the business says is "always true" becomes a constraint: NOT NULL, UNIQUE, CHECK, FK. When app-level validation and DB constraints disagree, the DB is right. (Type choices — exact types for money, timezone handling — are knowledge you have; apply them.)

### 3. Prove queries before shipping them

- `EXPLAIN` every query that runs on a user-facing path, against a dataset of realistic size — a query plan on 200 dev rows is fiction
- Index for the queries you actually run (the WHERE/JOIN/ORDER BY columns), not for the columns that look important; each index taxes every write, so it needs a query to justify it
- N+1s are found by looking at the query log for one request, not by intuition — one request should be a handful of queries, not a hundred; when a query is slow and the fix isn't obvious, route through **performance-optimization**
- Transactions: state what each one must hold atomically, keep them short, and know your isolation level's actual anomalies (most defaults are not SERIALIZABLE)

### 4. Change with ceremony

Every schema change routes through the **data-migration** skill (expand → migrate → contract). No exceptions for "just adding a column" — a NOT NULL column with a default on a large table can still lock it, and every ORM "auto-migration" is a migration you didn't review.

### 5. Operational floor

- Backups exist *and restore has been tested* (an untested backup is a wish)
- Slow-query logging on from day one — the regressions announce themselves if you're listening
- Retention/deletion story decided when the table is created (GDPR-shaped requests arrive after the data does)

## Anti-Patterns

- Running EXPLAIN on 200 dev rows and calling the gate passed — the plan changes when the optimizer sees real cardinalities
- JSON columns as the schema (fine for genuinely schemaless payloads; a smell when it holds fields you query and constrain)
- SELECT * in production code paths — column changes now break consumers invisibly
- Adding indexes speculatively or removing them blind (both are measured decisions)
- Soft-delete everywhere by reflex, hard-delete nowhere, and no one can say why
- Testing against an empty database and shipping into a full one

## Verification

Done means evidence, not vibes:
- EXPLAIN output attached to the verify artifact for **every user-facing query**, with the row count of the test dataset it ran against stated alongside — the row count is what makes the plan credible
- The per-entity template from §1 exists in the plan artifact
- Verdict is PASS/FAIL; EXPLAIN against a dataset smaller than production-realistic is a FAIL, not a smaller PASS
