# Database Design Review: Multi-Tenant B2B SaaS Schema

## 1. Data Type Issues

### 1.1 `orders.amount` uses `float` for currency (CRITICAL)

`float` (alias for `double precision`, an 8-byte IEEE 754 floating-point number) is fundamentally unsuited for monetary values. Floating-point arithmetic introduces rounding errors: `0.1 + 0.2 != 0.3` in IEEE 754. A dollar amount stored as `float` can produce incorrect totals, tax calculations, and reconciliation mismatches.

**Fix:** Use `numeric(12,2)` or `numeric(15,2)` (or `decimal` equivalent) to store exact decimal dollar amounts. This guarantees that `19.99 + 5.00` equals exactly `24.99`.

### 1.2 `org_id`, `user_id` in `orders` are `int` but referenced columns are `serial` (MEDIUM)

`serial` in PostgreSQL creates a `bigint`-backed sequence (effectively `int8`). The `users.id` column is `serial` (i.e., `bigint`), but `orders.user_id` is declared as plain `int` (4-byte, `int4`). This is a type mismatch: `int` can hold values up to ~2.1 billion, which is fine for most cases, but the join between `int` and `bigint` forces implicit type coercion at query time, which can prevent index usage and cause subtle casting issues.

**Fix:** Make `orders.user_id` match the referenced type: `bigint` (or use `GENERATED ALWAYS AS IDENTITY` consistently across all tables).

### 1.3 No `created_at` on `users` or `orgs` tables (LOW)

The `orgs` and `users` tables lack `created_at` / `updated_at` timestamps. For audit trails, debugging, and understanding data lifecycle, these are standard.

---

## 2. Missing Constraints (CRITICAL for Data Integrity)

### 2.1 No foreign keys on any relationship (CRITICAL)

Neither `users.org_id` nor `orders.user_id` has a foreign key constraint. This means:

- A user can belong to a non-existent organization (`users.org_id` can reference an `orgs.id` that does not exist).
- An order can reference a non-existent user (`orders.user_id` can reference a `users.id` that does not exist).
- An order can exist for a user in a different organization, violating the multi-tenant data model with no enforcement.
- Deleting an org or user cascades silently (or fails unpredictably) because there is no `ON DELETE` / `ON UPDATE` behavior defined.

**Impact:** Data integrity is entirely application-enforced, which is fragile. Application bugs, direct SQL writes, or data migrations can silently corrupt the tenant boundary.

**Fix:** Add explicit foreign keys:
```sql
ALTER TABLE users ADD CONSTRAINT fk_users_org
  FOREIGN KEY (org_id) REFERENCES orgs(id) ON DELETE CASCADE;
ALTER TABLE orders ADD CONSTRAINT fk_orders_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### 2.2 No `UNIQUE` constraint on `users.email` (HIGH)

Email addresses should be unique within an organization (or globally). Without a unique constraint, the same user can be created multiple times with the same email in the same org, leading to duplicate accounts, authentication confusion, and order attribution errors.

**Fix:** Add `UNIQUE (org_id, email)` to enforce one account per email per organization.

### 2.3 No `CHECK` constraints on `users.role` or `orders.status` (MEDIUM)

Both `users.role` and `orders.status` are untyped `text` columns. Any value can be stored: `'admin'`, `'superadmin'`, `'god'`, `''`, `NULL`. There is no database-level enforcement of valid values.

**Impact:** Application code must validate every insert/update, and any bug or direct SQL write can introduce invalid states. Queries filtering on `status = 'paid'` may miss rows stored as `'PAID'`, `'Paid'`, `'paid '`, etc.

**Fix:** Use `CHECK` constraints or, better, PostgreSQL `ENUM` types or lookup/reference tables:
```sql
ALTER TABLE users ADD CONSTRAINT chk_user_role
  CHECK (role IN ('admin', 'member', 'viewer'));
ALTER TABLE orders ADD CONSTRAINT chk_order_status
  CHECK (status IN ('pending', 'paid', 'refunded'));
```

### 2.4 No `NOT NULL` constraints on critical columns (MEDIUM)

- `users.org_id` can be `NULL` -- a user not belonging to any organization breaks the multi-tenant model.
- `users.email` can be `NULL` -- meaningless without an email.
- `users.role` can be `NULL` -- no role means no access control.
- `orders.user_id` can be `NULL` -- an order with no owner.
- `orders.amount` can be `NULL` -- an order with no amount.
- `orders.status` can be `NULL` -- an order with no status.

**Fix:** Add `NOT NULL` to all required columns.

---

## 3. Multi-Tenancy Issues (CRITICAL for a B2B SaaS)

### 3.1 No tenant isolation enforcement at the database level (CRITICAL)

The query filters by `u.org_id = 42` in the application layer, but there is no database-level mechanism to prevent a user from accessing another organization's data. If any query omits the `org_id` filter (which is easy to forget), the user sees data from all organizations.

**Impact:** A single missed `WHERE u.org_id = ?` clause is a full data breach across all tenants. This is the most common class of vulnerability in multi-tenant applications.

**Fix options:**
- Use PostgreSQL Row Level Security (RLS) policies tied to a session variable (`SET app.current_org_id = 42`), which automatically appends tenant filtering to every query.
- Use a `current_org()` function and enforce via RLS:
  ```sql
  ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
  CREATE POLICY tenant_isolation ON orders
    USING (user_id IN (SELECT id FROM users WHERE org_id = current_org()));
  ```
- Use PostgreSQL schemas per tenant (schema-per-tenant model) for stronger isolation.

### 3.2 The query joins through `users` to filter `orders` by `org_id` (MEDIUM)

The query `WHERE u.org_id = 42` requires joining `orders` to `users` just to filter by organization. This means:

- Every order query must go through the `users` table, adding join overhead.
- There is no direct way to filter orders by organization without the join.
- If a user is deleted (and orders cascade), the org_id filter still works, but the join adds unnecessary complexity.

**Fix:** Add `org_id` directly to the `orders` table as a denormalized column (with application-level consistency guarantees). This is a common and accepted pattern in multi-tenant systems:
```sql
ALTER TABLE orders ADD COLUMN org_id bigint NOT NULL;
-- Populate from existing data, then add FK
ALTER TABLE orders ADD CONSTRAINT fk_orders_org
  FOREIGN KEY (org_id) REFERENCES orgs(id);
```
Then the query becomes:
```sql
SELECT o.*, u.email
FROM orders o JOIN users u ON u.id = o.user_id
WHERE o.org_id = 42
ORDER BY o.created_at DESC;
```
This is faster (no join needed for the WHERE clause) and more resilient.

### 3.3 No mechanism to prevent cross-tenant data creation (CRITICAL)

There is nothing preventing application code from inserting an order with a `user_id` belonging to a different organization than the current tenant context. Without RLS or application-level enforcement (which is fragile), this is a silent data leak.

---

## 4. Performance Issues

### 4.1 No indexes on any foreign key or filter columns (HIGH)

The query filters on `u.org_id = 42` and orders by `o.created_at DESC`. Without indexes:

- The `WHERE u.org_id = 42` clause requires a sequential scan of the entire `users` table to find matching users.
- The `ORDER BY o.created_at DESC` requires a full sort of all matching rows.
- The join between `orders` and `users` on `u.id = o.user_id` cannot use an index on `orders.user_id` (because there is no index).

**Impact:** On a production dataset with thousands of users and millions of orders, this query will be extremely slow -- potentially seconds or minutes per page load. Since it runs on every dashboard load, this directly impacts user experience and server costs.

**Fix:** Add indexes:
```sql
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
-- Composite index for the common query pattern
CREATE INDEX idx_orders_org_user_created ON orders(user_id, created_at DESC);
```

### 4.2 `SELECT o.*` is a broad select (LOW)

Selecting all columns from `orders` on every page load may retrieve more data than needed. If the dashboard only displays a subset of columns, this wastes bandwidth and memory. However, this is a minor concern compared to the missing indexes.

### 4.3 `serial` columns use 4-byte sequences, but `int` references are also 4-byte (MEDIUM)

As noted in 1.2, `serial` creates a `bigint`-backed sequence but the column type is `int4`. This is actually consistent within each table, but the cross-table mismatch (`users.id` is `int4` via `serial`, `orders.user_id` is `int4`) is fine. The real issue is that `serial` is deprecated in favor of `GENERATED ALWAYS AS IDENTITY`. If the schema is migrated to use `bigint` for IDs (for scale), the type mismatch becomes a real problem.

---

## 5. Schema Design Issues

### 5.1 No soft-delete support (MEDIUM)

There is no `deleted_at` or `is_active` column on any table. Deleting a user or org is a hard delete with cascading effects. In a B2B SaaS context, soft deletes are important for:

- Audit compliance (GDPR, SOC2) -- you need to retain order history even if a user leaves.
- Undo operations -- accidental deletions cannot be recovered.
- Historical accuracy -- an order placed by a user who later gets deactivated should still be attributable.

**Fix:** Add `deleted_at timestamp NULL` to each table and filter queries accordingly, or use RLS policies that exclude soft-deleted rows.

### 5.2 No audit / change tracking (MEDIUM)

There is no mechanism to track who created or modified records and when. For a B2B SaaS with compliance requirements, this is often mandatory.

**Fix:** Add `created_by`, `updated_by`, `created_at`, `updated_at` columns, or use PostgreSQL triggers / audit tables.

### 5.3 No default value or constraint on `orders.status` (MEDIUM)

New orders have no default status. An order inserted without an explicit status will be `NULL`, which is not one of the expected values (`'pending'`, `'paid'`, `'refunded'`). This can cause queries filtering on `status = 'pending'` to miss newly created orders.

**Fix:** Add a default:
```sql
ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending';
```

### 5.4 `orgs.name` has no length limit (LOW)

The `name text` column has no `VARCHAR(n)` limit or `CHECK (char_length(name) <= N)`. While PostgreSQL handles arbitrary-length text fine, unbounded text fields can cause issues with:

- Index size growth
- Application display truncation
- Potential abuse (a 10MB org name)

**Fix:** Use `name varchar(255) NOT NULL` or add a check constraint.

### 5.5 `users.email` has no length limit or format validation (LOW)

Same as above for email. Additionally, there is no check that the email contains an `@` symbol or follows a basic format.

**Fix:** Use `email varchar(255) NOT NULL UNIQUE` and consider a `CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')` constraint.

---

## 6. Operational / Infrastructure Issues

### 6.1 No connection pooling strategy mentioned (LOW)

The schema itself does not address connection pooling. For a multi-tenant SaaS with many concurrent dashboard loads, connection pooling (PgBouncer, etc.) is essential. This is not a schema issue per se, but the lack of indexes (see 4.1) makes connection pooling even more critical -- long-running queries hold connections longer.

### 6.2 No partitioning strategy for `orders` (MEDIUM)

The `orders` table has no partitioning. As it grows (which it will in a B2B SaaS), queries filtering by date or organization will degrade. Partitioning by `created_at` (range) or by `org_id` (list) would help.

**Fix:** Consider range partitioning by month or quarter:
```sql
CREATE TABLE orders (...) PARTITION BY RANGE (created_at);
CREATE TABLE orders_y2026m01 PARTITION OF orders
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### 6.3 No backup / retention strategy (LOW)

Not a schema issue, but the lack of `updated_at` timestamps and soft-delete columns makes point-in-time recovery and data retention policies harder to implement.

### 6.4 `serial` is legacy (LOW)

`serial` is a PostgreSQL legacy feature. The modern approach is `GENERATED ALWAYS AS IDENTITY`, which is SQL-standard and has better behavior (e.g., `ALTER TABLE ... ALTER COLUMN ... RESTART` is more predictable).

---

## 7. Security Issues

### 7.1 No row-level security (CRITICAL -- repeated from 3.1)

This is the single most important finding. Without RLS, multi-tenant data isolation is entirely application-enforced. A single application bug (missing `org_id` filter, incorrect tenant context, race condition in session setup) exposes all tenants' data to every user.

### 7.2 No encryption at rest or in transit specified (LOW)

Not a schema issue, but sensitive data (emails, order amounts) should be encrypted. Consider column-level encryption for PII if required by compliance.

---

## Summary of Findings by Severity

| Severity | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 4 | No foreign keys; no RLS / tenant isolation; `float` for currency; cross-tenant data creation possible |
| HIGH | 2 | No indexes on FK/filter columns; no unique constraint on email |
| MEDIUM | 8 | Type mismatch (`int` vs `serial`); no NOT NULL constraints; no CHECK constraints; no soft delete; no audit trail; no default status; broad SELECT; no partitioning |
| LOW | 5 | No timestamps on orgs/users; no length limits; `serial` is legacy; connection pooling; encryption |

## Recommended Priority Order for Fixes

1. **Add foreign keys** -- prevents data integrity corruption immediately.
2. **Add Row Level Security** -- prevents data breaches across tenants.
3. **Add indexes** -- prevents performance degradation on every page load.
4. **Change `amount` from `float` to `numeric`** -- prevents financial calculation errors.
5. **Add `NOT NULL` and `CHECK` constraints** -- enforces data quality at the database level.
6. **Add `UNIQUE (org_id, email)`** -- prevents duplicate accounts.
7. **Add `org_id` to `orders`** -- simplifies queries and improves performance.
8. **Add soft-delete columns and audit fields** -- supports compliance and operational needs.
9. **Consider partitioning and modern identity columns** -- for scale and maintainability.