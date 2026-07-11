## Security Review: Invoice API (routes.py) — Multi-tenant B2B

Surfaces touched: input handling, auth & authorization (org scoping), secrets/config (none visible), output & injection, dependencies (Flask + ORM).

### Findings

1. **routes.py:31** — Missing input validation on `amount_cents` and `customer_name` in `create_invoice` — severity **high**
   Exploit: An attacker sends `{"amount_cents": -999999999, "customer_name": ""}`. The API accepts negative amounts with no range check, allowing creation of credit invoices that reduce org balances. No max cap either — `amount_cents: 999999999999999` is accepted.
   Fix: Validate `amount_cents > 0` and `amount_cents <= MAX_CENTS`. Validate `customer_name` is non-empty, within a max length (e.g., 256 chars), and stripped of control characters.

2. **routes.py:30** — `org_id` is overridable by the client in `create_invoice` — severity **high**
   Exploit: A user in org 100 sends `{"org_id": 200, "amount_cents": 5000, "customer_name": "Shell Corp"}`. The code uses `data.get("org_id", request.user.org_id)`, which means a provided `org_id` is accepted without verification. The user can create invoices in any organization, not just their own. The org_id check was only added to the GET/UPDATE queries, not to the CREATE endpoint.
   Fix: Remove `data.get("org_id", ...)` entirely. Always set `org_id=request.user.org_id`. If org assignment is a legitimate feature, add an explicit authorization check that the user's role permits creating invoices in the target org.

3. **routes.py:51-53** — `customer_id` is set without verifying the customer belongs to the same org — severity **medium**
   Exploit: In `update_invoice`, a user updates their invoice and sets `customer_id` to a customer belonging to a different organization. The invoice is now cross-org — it references a customer from another tenant. While the invoice itself stays scoped to the user's org, the customer record may leak cross-org relationships or cause data integrity issues downstream.
   Fix: After loading the customer by `customer_id`, verify `Customer.org_id == request.user.org_id` (or however cross-references are modeled). Alternatively, only allow customer IDs that are already associated with the user's org.

4. **routes.py:48** — No input validation on PATCH fields — severity **medium**
   Exploit: A client sends `{"amount_cents": "not_a_number"}` or `{"customer_id": null}`. Flask/JSON parsing accepts the value, and the ORM may coerce it or raise an unhandled error. If the ORM coerces silently, the invoice gets corrupted data. If it raises, the error may leak stack traces or internal details.
   Fix: Validate types before assignment. Wrap in try/except with a clean 400 response.

5. **routes.py:62** — Role check uses string equality, not a proper role-based access control check — severity **low**
   Exploit: If roles are ever extended (e.g., "admin_read", "admin_write"), the string comparison `request.user.role == "admin"` would grant access to unintended roles. This is a future-proofing issue, not an active exploit.
   Fix: Use a role hierarchy or permission check function (e.g., `has_permission(request.user, "invoices.export")`).

6. **routes.py:21, 36, 55, 66** — `to_dict()` may leak internal fields — severity **low**
   Exploit: If `Invoice.to_dict()` returns all model fields (including internal IDs, timestamps, or flags like `is_deleted`), this data leaks to API consumers. A customer could see internal invoice states or IDs of other invoices.
   Fix: Audit `to_dict()` to ensure it only returns fields appropriate for the caller's role. Consider a separate serializer per endpoint.

### Verdict: FIX FIRST

Two high-severity findings must be resolved before merge:
- **Finding #2** (org_id override in create) is a direct multi-tenant data integrity breach — any user can create invoices in any org.
- **Finding #1** (no input validation) allows negative/unbounded amounts.

The org scoping on GET and UPDATE is correct, but the CREATE endpoint was missed entirely. The team addressed the earlier review's concern for read/update paths but did not apply the same discipline to the write path.