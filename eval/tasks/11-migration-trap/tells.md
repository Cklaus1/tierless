# GRADER-ONLY — Task 11 tells

## The trap
A model that knows "expand → migrate → contract" can recite it — but this migration has
several traps that the *rote* pattern misses, and reciting the pattern without engaging the
specifics is the failure mode. Task 04 rewarded knowing the pattern; task 11 requires
APPLYING it against concrete hazards a naive sequence gets wrong.

## The hazards a correct plan must handle (each a tell)
**H1 — dual-write must cover BOTH directions AND the derived value.** During rolling deploy,
old code writes `status`, new code writes `state`/`settled_at`. The plan must keep them in
sync BOTH ways (old writes → new columns, new writes → old column) via triggers or dual-write,
OR the reconciliation job and analytics that read `status='done'` will see stale/missing data.
Naive "app dual-writes" forgets that OLD app servers still write only `status` mid-deploy —
so a DB trigger (not just app code) is needed to catch old-code writes. THE subtle one.

**H2 — external readers of `status` block the contract step.** The nightly reconciliation job
and dashboards query `WHERE status='done'` directly on the replica. `status` cannot be dropped
until those are migrated too — the plan must inventory and migrate/notify those consumers, not
just the app. A plan that drops `status` after the app is cut over, ignoring the external
`status='done'` readers, is broken.

**H3 — the `payments_status_idx` index + a new index on `state`.** Dropping `status` drops
its index; queries on `state` need a new index, created CONCURRENTLY (can't take an
ACCESS EXCLUSIVE lock on a 50M-row hot table). Building the index non-concurrently locks writes
and takes the payments table down during peak.

**H4 — backfilling `settled_at` from `updated_at` is a one-time snapshot with a correctness
trap.** `updated_at` changes on ANY update, so a row touched after going 'done' has an
`updated_at` LATER than its true settle time — the backfilled `settled_at` is approximate/
wrong for such rows. A correct plan flags that `updated_at` is not a faithful settle
timestamp and either accepts it explicitly (documented) or sources the real time from an audit
log / event history. Reciting the mapping without noticing this = MISS.

**H5 — enum type migration hazard.** Adding a Postgres enum and backfilling 50M rows must be
batched (H-style), and adding a value to / changing an enum has its own locking rules; a plan
that does a single `UPDATE ... SET state = ...` on 50M rows locks/bloats. (Batched backfill +
concurrent-safe enum handling.)

## Tells (binary)
- **T1 — expand/migrate/contract phasing, reversible, drop-last**: the baseline (as task 04).
  Present = HIT. Absent (single-shot) = MISS everything.
- **T2 — H1: bidirectional sync via a DB TRIGGER, not just app dual-write** — explicitly
  reasons that OLD app servers mid-deploy write only `status`, so app-level dual-write is
  insufficient; a trigger keeps columns in sync. (App-only dual-write mention = PARTIAL.)
- **T3 — H2: inventories the external `status='done'` readers** (reconciliation job,
  dashboards) and blocks the contract/drop until they're migrated. Ignoring them = MISS.
- **T4 — H3: new index built CONCURRENTLY** (and notes dropping status drops its index).
  A plan that adds an index without `CONCURRENTLY` on a 50M-row hot table = MISS on T4.
- **T5 — H4: flags that `updated_at` is NOT a faithful settle time** for rows updated after
  settling — the backfill is approximate. Catching this data-quality trap is the sharpest
  discriminator. Blindly using the given mapping = MISS.
- **T6 — H5 / batched backfill at 50M scale**: backfill runs in throttled batches, not one
  UPDATE; verified by counting before contract. (As task 04's T3/T6 but must be present here too.)
- **T7 — no naive recitation**: the plan engages THIS table's specifics (rolling deploy,
  external readers, index, updated_at). A generic expand/migrate/contract essay that never
  mentions the trigger, the external readers, or the updated_at trap scores low even if the
  pattern is 'correct'.

## Skill lineage
data-migration (expand/migrate/contract, reversibility, verify-by-counting, backfill batching),
plan-mode (specific ordering, edge cases). Skills arm gets data-migration.
Hypothesis: bare models recite expand/migrate/contract and hit T1/T6 but MISS T2 (trigger vs
app dual-write), T3 (external readers), T5 (updated_at trap). Skills arm following
data-migration's "dual-write from code... backfill... verify by counting... external readers"
plus its rehearsal/reversibility rigor should catch more — but T5 (the updated_at correctness
trap) is headroom for EVERY arm; it's the real discriminator between reciting and reasoning.
Headroom: HIGH — five distinct hazards, most invisible to pattern-matching.
