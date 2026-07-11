# GRADER-ONLY — Task 04 tells

## The trap
"Split full_name into first/last" reads like a one-liner: add two columns, run an
UPDATE that splits on the space, drop the old column. The undisciplined plan does
exactly that — a single migration, an unbounded UPDATE on 4M rows (table lock / long
transaction on a live service), a naive space-split, and the old column dropped
immediately (irreversible, and it breaks every reader still using full_name).

The disciplined plan (data-migration: expand → migrate → contract) is the tell.

## Tells (binary)
- **T1 — expand/migrate/contract (or equivalent phased, reversible) shape**: does NOT
  do it in one shot. New columns added first, backfilled, readers migrated, old column
  dropped LAST as a separate later step. A single-migration plan is a MISS.
- **T2 — dual-write window**: recognizes that during the transition, both full_name
  and first/last must stay in sync (app writes to both, or a trigger) so the service
  keeps working and rollback stays possible. Missing this is a MISS.
- **T3 — batched backfill, not one UPDATE**: the 4M-row backfill runs in batches with
  throttling, not a single UPDATE that locks the table / blows the transaction. Naming
  the 4M rows as a reason to batch is the tell.
- **T4 — reversibility / drop-last**: the old column is kept until the new shape is
  proven in production; the drop is a separate, later, deferred step. Dropping
  full_name in the same migration = MISS.
- **T5 — data-quality reality of the split**: flags that `full_name` → first/last is
  NOT a clean space-split — "Mary Jane Watson", "Cher", "van der Berg", "Dr. Smith",
  empty/null names. A plan that assumes `split(" ")` works is a MISS on T5. This is
  the non-obvious domain tell.
- **T6 — verify by counting**: verification queries (row counts match, no nulls where
  full_name had a value, spot-checks) before the contract step.

## Skill lineage
data-migration (primary), plan-mode/deconstruct (secondary).
Expected: A often does the naive one-shot, misses T2/T3/T5. C usually phases and
batches. B's gain: T1 (phasing) + T4 (drop-last) + T5 (dirty-data reality).
