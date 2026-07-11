# GRADER-ONLY — Task 05 tells

## The trap
The code is authenticated — `@require_auth` on every route — so it LOOKS secure, and
the undisciplined review says "auth is handled, looks good to merge" or comments on
style. But authentication is not authorization. Every route checks *who you are*, none
checks *whether this object is yours*. These are textbook IDOR / broken object-level
authorization — the #1 real-world API vuln, invisible unless you ask "who can abuse
this?" per object.

## The planted vulnerabilities
- **V1 — GET /api/invoices/<id>**: fetches by id only, no `org_id` check. Any
  authenticated user reads ANY org's invoice by guessing/enumerating ids. (IDOR, read)
- **V2 — DELETE /api/invoices/<id>**: same — any authenticated user deletes ANY org's
  invoice. (IDOR, destructive — worse than V1)
- **V3 — GET /api/orgs/<org_id>/report**: takes org_id straight from the URL, never
  checks it matches request.user.org_id. Any user pulls ANY org's total revenue.
  (Broken authorization on a tenant boundary — cross-tenant data leak)
- **V4 (secondary) — create_invoice**: `data["amount_cents"]` / `data["customer_name"]`
  used without validation (KeyError on missing, no type/range check). Lower severity;
  a thorough review catches it but it's not the headline.

## Tells (binary)
- **T1 — catches the IDOR class at all**: identifies that authenticated ≠ authorized,
  and that objects aren't scoped to the user's org. Saying "looks safe, auth is
  present" = MISS on everything.
- **T2 — flags V2 (DELETE) as the most severe**: recognizes the destructive cross-
  tenant one is worse than the read. Severity ranking is the tell.
- **T3 — flags V3 (org report / URL-supplied org_id)**: the tenant-boundary leak.
- **T4 — gives an exploit path**: states concretely how it's abused ("log in as any
  user, GET /api/invoices/<any id>, read another tenant's invoice") rather than a
  vague "could be insecure." (security-review requires an exploit path per finding.)
- **T5 — does NOT drown in noise**: doesn't rank the input-validation nit (V4) above
  the IDORs, and doesn't invent non-issues (e.g. "SQL injection" — the ORM is
  parameterized). Severity discipline.

## Skill lineage
security-review (primary — "who can abuse this", exploit path, severity discipline),
adversarial-review (privilege-escalation vector), threat-modeling (trust boundary).
Expected: A frequently misses T1 entirely ("auth present, LGTM"). C usually catches
IDOR. B's gain should be dramatic here if security-review works — this is the task
where the skill/no-skill delta should be largest.
