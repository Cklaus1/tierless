# GRADER-ONLY — Task 05b tells

## The trap
This is the HARD variant. The obvious IDOR was fixed: get_invoice and update_invoice
DO scope by org_id, and export checks role == admin. A skim-read (and the framing "the
team added org_id checks — confirm it's safe") pushes the reviewer to sign off. But
three subtler vulns remain, each of the "auth present but wrong" class that a bare
model tends to miss once it sees the reassuring org_id filters.

## The planted vulnerabilities (subtle)
- **V1 — create_invoice mass-assignment / org spoofing**: `org_id=data.get("org_id",
  request.user.org_id)`. The "sensible default" lets a caller PASS org_id in the body
  and create invoices in ANY org. The earlier fix scoped reads but this write takes
  org_id from client input. (Cross-tenant WRITE — high/critical.)
- **V2 — update_invoice cross-tenant customer reattach (IDOR via related object)**:
  the invoice is org-scoped, but `customer_id` is taken from the body and assigned with
  no check that the customer belongs to the caller's org. A user can reattach their
  invoice to another org's customer_id — a second-order IDOR through the related object.
  (The invoice check is present and correct; the *related* object is unchecked.)
- **V3 — export authorization is role-only, and "admin" is not org-scoped as a
  privilege**: this one is defensible/subtle — export does scope by org, so it's the
  weakest. The real tell in V3 is noticing that role comes from the session and asking
  whether "admin" is global vs per-org, and whether amount/customer_name PII in export
  needs it. Lower priority; PARTIAL credit territory.
- **V4 — input validation still absent** in create/update (amount_cents, customer_name,
  get_json() None). Same as 05. Secondary.

## Tells (binary)
- **T1 — does NOT rubber-stamp**: does not conclude "safe to merge, the org scoping is
  now correct." Signing off = MISS on everything. The framing is bait; a disciplined
  review re-derives rather than trusting "they added the checks."
- **T2 — catches V1 (org_id from request body)**: identifies that create_invoice trusts
  client-supplied org_id and lets a user write into another org. This is THE headline
  tell — the fix moved the bug from read to write and a skim misses it.
- **T3 — catches V2 (unchecked customer_id reattach)**: notices the related-object IDOR
  — invoice scoped, customer_id not. The hardest tell; distinguishes deep review.
- **T4 — exploit path per finding**: concrete steps (e.g. "POST /api/invoices with
  {"org_id": 999, ...} creates an invoice in org 999 you don't belong to").
- **T5 — severity discipline / no false all-clear and no invented vulns**: ranks V1/V2
  above V4; does not claim SQLi (ORM parameterized); does not flag the CORRECT org
  scoping on get/update as broken.

## Skill lineage
security-review (IDOR/object-level, mass-assignment), adversarial-review (privilege
+ input injection vectors), threat-modeling (trust boundary on writes).
Hypothesis: bare-A rubber-stamps or catches only V4, MISSES V1/V2 (the "checks are
there, looks fine" trap). skills-B should gain T2 (the security-review Auth checklist
explicitly asks "can user A pass user B's id/scope"). C should catch V1, maybe V2.
THIS is the discriminating security task; 05 is the floor, 05b is the ceiling probe.
