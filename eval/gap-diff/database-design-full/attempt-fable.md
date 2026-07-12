# Database Design Review — Multi-Tenant B2B SaaS (orgs / users / orders)

Below is every real problem I can find, grouped by area. The most severe issues are flagged **[CRITICAL]**.

---

## 1. Correctness / Data-Type Problems

### 1.1 `amount float` for money **[CRITICAL]**
Binary floating point cannot represent most decimal fractions exactly (`0.1 + 0.2 ≠ 0.3`). Consequences:
- Per-row rounding errors that compound in `SUM(amount)` — dashboard totals, invoices, and reconciliation against the payment processor will drift.
- Equality comparisons (`WHERE amount = 19.99`) silently fail.
- `float` is also `double precision`'s 4-byte sibling in some ports — either way it's wrong for currency.

**Fix:** `numeric(12,2)` (or integer cents as `bigint`). Add `CHECK (amount >= 0)` unless negative amounts are an intentional refund representation — and if refunds are represented as separate negative rows vs. a status flip, pick one; right now both are possible simultaneously (a `status='refunded'` row still carries its positive amount, so what does "refunded" mean for reporting? Partial refunds are unrepresentable).

Also: the comment says "dollars" — there is **no currency column**. The moment a second currency appears, every stored amount is ambiguous. Add `currency char(3)` (ISO 4217) now or document single-currency as an explicit invariant.

### 1.2 `created_at timestamp` (without time zone) 
`timestamp` stores a wall-clock time with no zone. If the server timezone ever changes (config change, migration to a new host/region, DST edge cases in client sessions), stored values become ambiguous and ordering/comparisons across sources break.

**Fix:** `timestamptz`. Also note the column is **nullable** — `DEFAULT now()` does not prevent an explicit `INSERT ... (created_at) VALUES (NULL)`. Add `NOT NULL`.

### 1.3 `status text` free-form **[CRITICAL for integrity]**
Nothing prevents `'PAID'`, `'Paid '`, `'shipped'`, `''`, or `NULL`. Every consumer must defensively normalize, and a typo in one code path silently creates unreachable orders.

**Fix:** one of:
- `CHECK (status IN ('pending','paid','refunded'))` + `NOT NULL` (easiest to evolve),
- a Postgres `ENUM` type (careful: removing values is painful),
- a lookup/reference table with an FK.

Beyond the domain constraint, the **state machine is unenforced**: nothing stops `refunded → pending`. Enforce transitions in one code path (or a trigger), and consider an `order_status_history` / `order_events` table — for a payments domain you will need an audit trail of who changed status when (support disputes, chargebacks, compliance).

### 1.4 `role text` free-form
Same problem as status: `'admin'` vs `'Admin'` vs `'owner'`. Authorization decisions based on unconstrained string comparison is a security bug factory. Constrain with CHECK/enum/lookup table, `NOT NULL` with a default.

Also a **modeling question**: `role` on `users` plus a single `org_id` means a user belongs to exactly one org with one role. Most B2B SaaS eventually needs multi-org membership (consultants, agencies). If that's plausible, model a `memberships(user_id, org_id, role)` join table now — retrofitting is painful.

### 1.5 `email text` unconstrained
- No `NOT NULL`, no `UNIQUE` — duplicate accounts are possible.
- No case normalization: `Bob@X.com` and `bob@x.com` are distinct rows. Use `citext`, or a unique index on `lower(email)`.
- Decide the uniqueness scope explicitly: globally unique (login identity) vs. unique per org — `UNIQUE (org_id, email)` — depending on your auth model.
- Optionally a basic format CHECK (or validate in app; but NOT NULL + UNIQUE belong in the DB).

### 1.6 `orgs.name` nullable, unconstrained
An org with `NULL` name is legal. Add `NOT NULL`, probably a non-empty CHECK. (Uniqueness of org names is a product decision — flag it either way.)

---

## 2. Referential Integrity — no foreign keys anywhere **[CRITICAL]**

- `users.org_id` has no FK to `orgs(id)` and is nullable → users pointing at nonexistent orgs, or at no org (whose orders then appear on *no* dashboard).
- `orders.user_id` has no FK to `users(id)` and is nullable → orphaned orders.

Consequences beyond bad data:
- **Silent revenue disappearance:** the dashboard query is an INNER JOIN. If a user row is deleted (offboarding), all of their orders vanish from every report — no error, just missing money. This is a correctness bug in the reporting pipeline, enabled by the missing FK.
- No `ON DELETE` semantics were ever decided. You almost certainly want `ON DELETE RESTRICT` for `orders.user_id` (orders are financial records — never cascade-delete them) and a **soft-delete / deactivation** flag on users instead of physical deletes. For `users.org_id → orgs`, `RESTRICT` as well.

**Fix:**
```sql
ALTER TABLE users  ADD CONSTRAINT users_org_fk  FOREIGN KEY (org_id)  REFERENCES orgs(id)  ON DELETE RESTRICT;
ALTER TABLE orders ADD CONSTRAINT orders_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
ALTER TABLE users  ALTER COLUMN org_id  SET NOT NULL;
ALTER TABLE orders ALTER COLUMN user_id SET NOT NULL;
```
(And note: FKs on `orders.user_id` need an index — see §4 — both for the query and because FK enforcement on parent deletes seq-scans the child otherwise.)

Also related: **PII/GDPR tension.** `email` is personal data; "right to erasure" collides with FK-protected financial records. Plan for anonymization (null/scramble the email, keep the row) rather than deletion — the soft-delete design above supports this.

---

## 3. Multi-Tenancy Design **[CRITICAL]**

### 3.1 Orders have no `org_id` — tenancy is only *derived* through the user join
This is the single biggest structural flaw:

1. **Orders silently change tenants.** If a user is moved to a different org (`UPDATE users SET org_id = ...`), all their historical orders instantly migrate to the new org's dashboards and revenue reports, and disappear from the old org's. Order tenancy must be **pinned at creation time**.
2. **No efficient tenant filter.** Every tenant-scoped query on orders must join through users (see §4).
3. **No way to apply Row-Level Security to orders** without a subquery-per-row policy.

**Fix:** add `org_id` to `orders`, `NOT NULL`, FK to `orgs`, populated at insert. To guarantee consistency between `orders.org_id` and the user's org at creation time, add `UNIQUE (id, org_id)` on `users` and a composite FK `orders(user_id, org_id) REFERENCES users(id, org_id)` — though note that composite FK *re-couples* order tenancy to the user's current org (breaks on user org moves), so if users can move orgs, prefer plain FK + application/trigger enforcement at insert, keeping the order's org_id immutable.

### 3.2 No Row-Level Security — tenancy enforced only by remembering the WHERE clause
Every query written by every engineer forever must include the tenant predicate. One forgotten `WHERE u.org_id = ?` = cross-tenant data leak (the classic multi-tenant breach). Postgres RLS is the belt-and-suspenders fix:

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON orders
  USING (org_id = current_setting('app.current_org_id')::int);
```
with the app setting `app.current_org_id` per request/transaction, and the app connecting as a non-superuser, non-table-owner role (owners bypass RLS unless `FORCE ROW LEVEL SECURITY`). Same for `users`.

### 3.3 The literal `42` in the query
If that literal is built by string interpolation, it's a **SQL injection** vector; even if not, unparameterized queries defeat plan caching. Use a bind parameter, and ensure the org id comes from the server-side session, never from a client-supplied value (IDOR).

---

## 4. Query & Index Performance **[CRITICAL at any real scale]**

The query runs **on every page load** and as written:

### 4.1 No index on `users(org_id)`
The `WHERE u.org_id = 42` filter requires a sequential scan of `users`.

### 4.2 No index on `orders(user_id)`
The join has no index on the FK side → Postgres will seq-scan/hash the entire `orders` table (all tenants' orders) on **every dashboard load**. This is O(total orders in the system) per page view; it will fall over as data grows and creates cross-tenant performance coupling (one big tenant slows everyone).

### 4.3 The `ORDER BY o.created_at DESC` cannot use an index
Because rows come from a join across many users, Postgres must materialize all of the org's orders and sort them every time. There's no index that can serve a pre-sorted scan for this shape.

### 4.4 No `LIMIT` — unbounded result set
The query returns the org's **entire order history** on every dashboard load. For a mature tenant that's potentially millions of rows sorted, serialized, and shipped to the app per page view. A dashboard almost certainly needs a page (or an aggregate), not everything.

**Fixes (combined with §3.1):**
```sql
-- after adding orders.org_id:
CREATE INDEX orders_org_created_idx ON orders (org_id, created_at DESC, id DESC);
CREATE INDEX users_org_idx ON users (org_id);
CREATE INDEX orders_user_idx ON orders (user_id);   -- for FK checks & per-user queries

SELECT o.id, o.amount, o.status, o.created_at, u.email
FROM orders o JOIN users u ON u.id = o.user_id
WHERE o.org_id = $1
ORDER BY o.created_at DESC, o.id DESC
LIMIT 50;
```
This turns the hot path into a backwards index scan on `(org_id, created_at)` with an early-out LIMIT — microseconds instead of a full sort.

### 4.5 Pagination details
- `created_at` is not unique → ordering is nondeterministic for ties, and OFFSET/keyset pagination will skip/duplicate rows. **Always tie-break on `id`** (as above).
- Prefer **keyset pagination** (`WHERE (created_at, id) < ($last_ts, $last_id)`) over `OFFSET` — OFFSET re-scans and discards N rows per page.

### 4.6 `SELECT o.*`
- Fetches every column, including any wide ones added later — silent payload/IO growth, prevents index-only scans.
- Breaks/behaves surprisingly under schema evolution (column order/name collisions in some ORMs, `email` colliding if orders ever grows an `email`).
- Select explicit columns.

### 4.7 It runs on *every* page load
Even after indexing, question whether the dashboard needs live rows per load. Candidates: cache the first page briefly, or precompute the aggregates the dashboard actually displays (materialized view / rollup table / Redis) and fetch detail rows on demand.

---

## 5. Key & ID Design

### 5.1 `serial` (32-bit int) primary keys
- `orders.id` is the table most likely to exceed 2,147,483,647 rows; running out of int space in production is a famously painful outage (the migration to bigint on a huge hot table requires careful online rewrite). Use **`bigint`** for `orders` now; it's nearly free.
- `serial` is the legacy mechanism; modern Postgres prefers `GENERATED ALWAYS AS IDENTITY` (SQL standard, cleaner permission/ownership semantics, prevents accidental manual inserts into the sequence range).

### 5.2 Sequential IDs exposed externally
If these ids appear in URLs/APIs: they leak **business volume** (competitors watch order ids grow) and invite **enumeration/IDOR** probing. Keep sequential PKs internally if you like, but expose a random public identifier (`uuid` / prefixed random token) for anything user-facing.

---

## 6. Missing Columns / Auditability

- No `updated_at` on any table (and no trigger to maintain one) — you can't answer "when did this order change?"
- No status-transition timestamps: `paid_at`, `refunded_at` are usually needed for finance reporting (a `refunded` order's `created_at` tells you nothing about when the refund happened).
- No audit/event history for orders (see §1.3) — first support escalation or chargeback dispute will demand it.
- `orgs` and `users` have no `created_at` at all.
- Refund modeling is thin: partial refunds, refund amount, refund reason, and linkage to the payment processor's ids (charge id, refund id, idempotency key) are all absent. At minimum store the processor reference for reconciliation.

---

## 7. Concurrency & Operational

- **Double-processing risk:** with no version column and no enforced state machine, two concurrent requests can both flip `pending → paid` or both issue a refund. Use `UPDATE ... WHERE status = 'pending'` compare-and-set semantics, `SELECT ... FOR UPDATE`, or an optimistic-locking version column — plus idempotency keys for payment webhooks.
- **Table growth / archival:** `orders` grows forever. Plan for time-based partitioning (`PARTITION BY RANGE (created_at)`) *before* the table is huge if retention/archival is anticipated — retrofitting partitioning onto a large live table is a project. Partitioning also localizes vacuum/bloat on the hot recent partition.
- **Migrations discipline:** adding the NOT NULLs/FKs above on a live table needs care (`NOT VALID` + `VALIDATE CONSTRAINT`, `CREATE INDEX CONCURRENTLY`) to avoid long locks.
- **`now()` semantics:** fine for most uses, but note it's transaction start time — long transactions stamp all rows with the same instant; use `clock_timestamp()` only if per-statement precision matters.
- Unbounded `text` everywhere is idiomatic Postgres, but consider sanity CHECKs (e.g., `length(email) < 320`, non-empty names) to stop garbage/abuse (multi-MB "names") at the boundary.

---

## 8. Corrected Schema (illustrative)

```sql
CREATE TABLE orgs (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        text NOT NULL CHECK (name <> ''),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id      bigint NOT NULL REFERENCES orgs(id) ON DELETE RESTRICT,
  email       citext NOT NULL,
  role        text   NOT NULL DEFAULT 'member'
                CHECK (role IN ('owner','admin','member')),
  deactivated_at timestamptz,            -- soft delete; never hard-delete users with orders
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (email)                          -- or UNIQUE (org_id, email), per auth model
);
CREATE INDEX users_org_idx ON users (org_id);

CREATE TABLE orders (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id      bigint NOT NULL REFERENCES orgs(id) ON DELETE RESTRICT,  -- tenancy pinned at creation
  user_id     bigint NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  amount      numeric(12,2) NOT NULL CHECK (amount >= 0),
  currency    char(3) NOT NULL DEFAULT 'USD',
  status      text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','paid','refunded')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  paid_at     timestamptz,
  refunded_at timestamptz
);
CREATE INDEX orders_org_created_idx ON orders (org_id, created_at DESC, id DESC);
CREATE INDEX orders_user_idx ON orders (user_id);

-- RLS on tenant tables (app connects as non-owner role, sets app.current_org_id per txn)
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY orders_tenant ON orders
  USING (org_id = current_setting('app.current_org_id')::bigint);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_tenant ON users
  USING (org_id = current_setting('app.current_org_id')::bigint);
```

And the hot-path query:

```sql
SELECT o.id, o.amount, o.currency, o.status, o.created_at, u.email
FROM orders o
JOIN users u ON u.id = o.user_id
WHERE o.org_id = $1
ORDER BY o.created_at DESC, o.id DESC
LIMIT $2;          -- keyset-paginate subsequent pages on (created_at, id)
```

---

## 9. Summary of the Top Issues (severity-ordered)

1. **`float` for money** — financial correctness bug.
2. **No `org_id` on orders** — tenancy derived through a mutable join; orders silently change tenants when a user moves orgs; no efficient/RLS-enforceable tenant filter.
3. **No foreign keys / no NOT NULLs** — orphaned rows; INNER JOIN silently drops orders of deleted users from revenue reports.
4. **No indexes for the hot query + no LIMIT** — full-table scan and full sort of all tenants' orders on every page load, returning unbounded results.
5. **No RLS / app-only tenancy enforcement** — one missing WHERE clause is a cross-tenant data leak; interpolated literal suggests injection risk too.
6. **Unconstrained `status`/`role`/`email` text** — garbage domains, no state machine, duplicate/case-variant accounts.
7. **`timestamp` without time zone, nullable** — ambiguity across zones/DST.
8. **`serial` int ids on orders** — 2^31 exhaustion risk; sequential ids leak volume/enable enumeration if exposed.
9. **No audit trail / status timestamps / updated_at / currency / refund detail** — unanswerable finance and support questions.
10. **No concurrency control on status transitions** — double-refund/double-capture risk.
