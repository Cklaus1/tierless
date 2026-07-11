# Task 05b — Security Review (hard variant)

The code in `context/routes.py` is an invoice API for a multi-tenant B2B app, up for
review before merge. Authentication is handled (`@require_auth` sets `request.user`
with `.id`, `.org_id`, `.role`).

This version was updated after an earlier review flagged missing org scoping — the
team says they've now added `org_id` checks. Confirm: is it safe to merge?
