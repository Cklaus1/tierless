# Task 05 — Security Review

The code in `context/routes.py` is an invoice API for a multi-tenant B2B app, up for
review before merge. Authentication is already handled (the `@require_auth` decorator
validates the session and sets `request.user` with `.id` and `.org_id`).

Review this code. Is it safe to merge?
