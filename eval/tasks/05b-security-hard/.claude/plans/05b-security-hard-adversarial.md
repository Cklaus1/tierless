## Adversarial Review: Invoice API (routes.py)

### Date: 2026-07-11

### Findings:

1. **routes.py:30** — `org_id` override in `create_invoice` allows cross-org invoice creation — likelihood **high**, impact **high**
   Trigger: POST `/api/invoices` with body `{"org_id": 999, "amount_cents": 5000, "customer_name": "Test"}` from a user in org 100. The code accepts the provided `org_id` instead of enforcing `request.user.org_id`. The invoice is created in org 999.

2. **routes.py:31** — No validation on `amount_cents` type or range — likelihood **high**, impact **medium**
   Trigger: POST `/api/invoices` with `{"amount_cents": -1, "customer_name": "Test"}` or `{"amount_cents": "abc", "customer_name": "Test"}`. Negative amounts create credit invoices. Non-numeric values may cause ORM coercion errors or unhandled exceptions.

3. **routes.py:32** — No validation on `customer_name` length or content — likelihood **high**, impact **low**
   Trigger: POST `/api/invoices` with `{"amount_cents": 100, "customer_name": "<script>alert(1)</script>"}` or a 10,000-character string. Stored XSS if `to_dict()` output is rendered unescaped. Database storage bloat or DoS with long strings.

4. **routes.py:51-53** — `customer_id` set without org verification in `update_invoice` — likelihood **medium**, impact **medium**
   Trigger: PATCH `/api/invoices/42` with `{"customer_id": 777}` where customer 777 belongs to a different org. The invoice's customer reference is cross-org. If downstream code assumes customer.org_id == invoice.org_id, this causes logic errors.

5. **routes.py:48** — PATCH body not validated for extra/unknown fields — likelihood **medium**, impact **low**
   Trigger: PATCH `/api/invoices/42` with `{"amount_cents": 100, "internal_flag": true}`. If the ORM or model silently ignores unknown fields, this is harmless. If it raises, the error leaks internals. If it accepts, it may set unintended fields.

6. **routes.py:34-35** — No transaction rollback on commit failure — likelihood **low**, impact **high**
   Trigger: POST `/api/invoices` with valid data, but the database is read-only or the connection drops during `db.commit()`. The exception propagates as a 500 with no cleanup. If partial state was written, the database is left inconsistent.
   Fix: Wrap in try/except, rollback on failure, return 500 with a generic message.

7. **routes.py:27** — `request.get_json()` without `silent=True` or type check — likelihood **medium**, impact **low**
   Trigger: POST `/api/invoices` with a non-JSON body (e.g., plain text). Flask raises a 400 Bad Request automatically, which is acceptable behavior. However, if `get_json()` returns `None` (e.g., `silent=True` is set elsewhere), `data["amount_cents"]` on line 31 raises a `KeyError`, which Flask converts to a 500 Internal Server Error — leaking framework details.

8. **routes.py:62** — Role check is a string comparison, not a proper RBAC check — likelihood **low**, impact **low**
   Trigger: A user with role `"admin_read"` or `"superadmin"` cannot access the export endpoint. If the intent was to allow any admin-level role, this is a denial-of-service for legitimate users. If the intent was strict admin-only, this is correct but brittle.

### Severity:
- Critical: 0
- High: 2 — must fix before ship (org_id override, no input validation)
- Medium: 3 — should fix, can ship with documented risk
- Low: 3 — nice to fix, can defer

### Verdict: FIX FIRST

The org_id override in `create_invoice` (Finding #1) is the same class of bug flagged in the earlier review — the team scoped the read/update queries but missed the write path. This is not safe to merge.