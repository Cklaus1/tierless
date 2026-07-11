## Task: Password Reset via Email
**Boundary:** In scope: (1) token generation and storage, (2) email sending with reset link, (3) reset page with form, (4) token validation and password update, (5) cleanup of used/expired tokens. Out of scope: (1) UI styling beyond functional markup, (2) two-factor authentication, (3) social login, (4) password strength policy changes, (5) rate-limiting infrastructure (add a basic per-IP throttle only), (6) database migrations beyond adding a column to users table, (7) admin dashboard for reset audit logs.

### Step 1: Add reset_token column and expiry to users table
- **Changes:** database — add `reset_token` (string, nullable, unique) and `reset_token_expires_at` (timestamp, nullable) columns to the existing `users` table.
- **Depends on:** nothing
- **Pass condition:** `ALTER TABLE users ADD COLUMN reset_token VARCHAR(255) NULL UNIQUE, ADD COLUMN reset_token_expires_at TIMESTAMP NULL;` runs without error; a new user row has NULL for both columns.

### Step 2: Implement "request reset" endpoint (POST /auth/reset-request)
- **Changes:** server route — accepts `email` from request body, validates email format, looks up user by email, generates a cryptographically random token (e.g., 32 bytes hex via crypto.randomBytes), stores SHA-256 hash of token in `users.reset_token`, sets `reset_token_expires_at` to now + 15 minutes, clears any existing token first. Always responds with a generic "if an account exists, an email was sent" message — never reveals whether the email is registered.
- **Depends on:** Step 1 (columns exist)
- **Pass condition:** POST with a registered email returns 200 with generic message; POST with unregistered email also returns 200 with same message (no enumeration); database shows token hash and expiry set for that user.

### Step 3: Implement email-sending helper for reset link
- **Changes:** email module — function `sendResetEmail(to, resetLink)` that composes an HTML + plain-text email with a link to the reset page including the raw (unhashed) token as a query parameter. Uses the existing email-sending helper already in the app. Link expires in 15 minutes (matches server-side expiry).
- **Depends on:** Step 2 (token is generated here; the raw token is available at this point)
- **Pass condition:** Calling `sendResetEmail("test@example.com", "https://app.com/reset?token=abc123")` invokes the existing email helper with correct to/subject/body; the link contains the raw token.

### Step 4: Implement reset page route (GET /auth/reset?token=xxx)
- **Changes:** server route — extracts `token` query parameter, hashes it with SHA-256, queries `users` for a matching `reset_token` where `reset_token_expires_at > now`. If found, renders a password reset form (fields: new_password, confirm_password). If token not found or expired, renders an error page with a link back to request reset.
- **Depends on:** Step 2 (token hashing logic must match), Step 1 (columns exist)
- **Pass condition:** GET with a valid, unexpired token returns the form page; GET with an expired or missing token returns an error page.

### Step 5: Implement password reset submission (POST /auth/reset)
- **Changes:** server route — accepts `token` (raw, from form) and `new_password`. Validates: (1) token exists and is not expired, (2) password meets minimum length (e.g., 8 chars), (3) passwords match. On success: hashes new password with existing password hasher, stores it, deletes `reset_token` and `reset_token_expires_at` (NULL them out), invalidates all existing sessions for that user (clear session table or increment a `session_version` column). Returns a success page.
- **Depends on:** Step 4 (route exists), Step 1 (columns exist), existing password hashing and session infrastructure
- **Pass condition:** POST with valid token + matching passwords >= 8 chars updates password, clears token, invalidates sessions, returns success page. POST with wrong token returns error. POST with mismatched passwords returns error. POST with short password returns error.

### Step 6: Add basic rate limiting on reset endpoints
- **Changes:** middleware or route-level — per-IP throttle on POST /auth/reset-request (max 3 requests per 15 minutes) and per-IP throttle on POST /auth/reset (max 5 requests per 15 minutes). Returns 429 with a retry-after header when exceeded.
- **Depends on:** nothing (can be added as middleware or inline)
- **Pass condition:** Sending 4 rapid requests to /auth/reset-request returns 429 on the 4th; waiting 15 minutes clears the throttle.

### Step 7: End-to-end integration test
- **Changes:** test file — automated test that exercises the full flow: request reset -> verify email contains link -> visit link -> submit new password -> verify login works with new password -> verify old sessions are invalidated -> verify token is consumed (cannot reuse).
- **Depends on:** Steps 1-6 all implemented
- **Pass condition:** Test suite passes; full flow executes without manual intervention.