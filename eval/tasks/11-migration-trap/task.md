# Task 11 — Migration With a Hidden Ordering Trap

A production system needs a schema change. Plan it.

**Current state:**
- Postgres, one always-on API (many app servers, rolling deploys — old and new code run
  simultaneously during any deploy).
- Table `payments` has a column `status` (text): values `'pending'`, `'done'`, `'failed'`.
- ~50 million rows. High write volume (thousands of inserts/updates per second during peak).

**The requested change:** Product wants to split `status` into two columns —
`state` (enum: `pending`/`settled`/`failed`) and `settled_at` (timestamp, null unless
settled). The mapping: old `'done'` → `state='settled'` + `settled_at` = the row's existing
`updated_at`; `'pending'`/`'failed'` map by name with `settled_at` NULL.

Also: there is a **`payments_status_idx` index on `status`**, and a nightly reconciliation
job and several analytics dashboards that **query `WHERE status = 'done'`** directly against
the replica.

Plan this migration end to end. Be specific about ordering and what could go wrong.
