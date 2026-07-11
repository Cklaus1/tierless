# Implementation Plan: Password Reset via Email

## Overview

Add a password reset flow to the existing web app. The app already has a users table, session authentication, and an email-sending helper. The flow follows the standard token-based reset pattern: user requests reset -> system sends email with a time-limited, single-use token -> user clicks link and submits new password -> system validates token and updates password.

---

## Step 1 — Database: Add reset token columns to users table

**What to do:**

- Add two columns to the `users` table:
  - `reset_token` (VARCHAR 255, nullable) — stores the hashed reset token
  - `reset_token_expires` (TIMESTAMP, nullable) — stores when the token expires
- Add a database migration file so the change is version-controlled and reversible.

**Why:** The token must be stored server-side (hashed) so it cannot be guessed or replayed. The expiry prevents stale tokens from being valid indefinitely.

**Acceptance criteria:**

- Migration runs successfully against the development database.
- New users created after the migration have NULL for both columns.
- Existing users are unaffected (columns are nullable).

---

## Step 2 — Backend: Generate and store reset token

**What to do:**

- Create a server-side function `generateResetToken(userId)` that:
  1. Generates a cryptographically random token (at least 256 bits of entropy, e.g. using `crypto.randomBytes(32)`).
  2. Hashes the token with SHA-256 (never store the plain token).
  3. Stores the hash and an expiry timestamp (1 hour from now) in the `users` table for the given user ID.
  4. Returns the **plain** token to the caller.

**Why:** Storing only the hash means a database breach does not expose valid reset tokens. The 1-hour expiry limits the window for abuse.

**Acceptance criteria:**

- Calling `generateResetToken` produces a unique, 64-character hex string.
- The stored hash matches `SHA-256(token)`.
- The expiry is set to exactly 1 hour in the future.
- Calling it twice for the same user invalidates the previous token (overwrite).

---

## Step 3 — Backend: Create "request reset" endpoint

**What to do:**

- Add a POST endpoint `POST /api/auth/forgot-password` that:
  1. Accepts a JSON body with `email`.
  2. Looks up the user by email.
  3. If the user exists, generates a reset token (Step 2), builds a reset URL (`/reset?token=<token>&email=<email>`), and calls the existing email-sending helper to send the reset email.
  4. Always returns HTTP 200 with a generic message ("If an account exists for that email, you will receive a reset link.") — never reveal whether the email is registered.

**Why:** The generic response prevents email enumeration attacks. The token is embedded in the email URL, not in the request/response body.

**Acceptance criteria:**

- POST with a registered email returns 200 and an email is sent.
- POST with an unregistered email returns 200 and no email is sent.
- POST with an invalid email format returns 400.

---

## Step 4 — Email template: Build the reset email

**What to do:**

- Create an HTML email template with:
  - A clear subject line: "Reset your password"
  - A message explaining the purpose and that the link expires in 1 hour.
  - A prominent button or link that goes to `/reset?token=<token>&email=<email>`.
  - A fallback plain-text link for clients that block rich content.
  - No sensitive data in the email body other than the token in the URL.

**Why:** The email is the delivery mechanism for the secret token. It must be clear, accessible, and work across email clients.

**Acceptance criteria:**

- Email renders correctly in at least one major email client (Gmail, Apple Mail).
- The reset link contains both the token and the user's email as query parameters.
- The email includes an expiry notice.

---

## Step 5 — Frontend: Build the "Forgot Password" page

**What to do:**

- Create a page at `/forgot-password` with:
  - A single input field for email.
  - A submit button labeled "Send reset link".
  - Client-side email validation.
  - On success, show a confirmation message: "If an account exists for that email, you will receive a reset link shortly."
  - A link back to the login page.

**Acceptance criteria:**

- Submitting a valid email navigates to a success state (or shows an inline confirmation).
- Submitting an invalid email shows a validation error.
- The page is accessible (keyboard navigable, proper labels, sufficient contrast).

---

## Step 6 — Frontend: Build the "Reset Password" page

**What to do:**

- Create a page at `/reset` that:
  1. Reads `token` and `email` from the URL query parameters.
  2. If either parameter is missing, shows an error: "Invalid or missing reset link."
  3. Displays two fields: "New password" and "Confirm new password".
  4. Validates that both passwords match and meet minimum requirements (e.g., at least 8 characters).
  5. On submit, sends a POST to `POST /api/auth/reset-password` with `{ token, email, newPassword }`.
  6. On success, redirects to the login page with a message: "Your password has been reset. You can now log in."

**Acceptance criteria:**

- The page rejects mismatched passwords with a clear error.
- The page rejects passwords below the minimum length.
- A successful reset redirects to login.
- A page visited with an expired or used token shows: "This reset link has expired or has already been used. Please request a new one."

---

## Step 7 — Backend: Create "reset password" endpoint

**What to do:**

- Add a POST endpoint `POST /api/auth/reset-password` that:
  1. Accepts JSON body with `token`, `email`, and `newPassword`.
  2. Looks up the user by email.
  3. If the user exists:
     - Hashes the provided token with SHA-256.
     - Compares the hash to the stored `reset_token` in the database.
     - Checks that `reset_token_expires` is in the future.
     - If both checks pass, hashes the new password (using the app's existing password hashing scheme, e.g. bcrypt) and updates the `password_hash` column.
     - Clears `reset_token` and `reset_token_expires` (sets them to NULL) so the token cannot be reused.
     - Invalidates all existing sessions for this user (optional but recommended: clear active session tokens/records).
  4. Returns 200 on success.
  5. Returns 400 for invalid input, 401 for expired/invalid token, 404 if user not found.

**Why:** This is the critical security boundary. It must validate the token hash, check expiry, clear the token after use, and use the same password hashing as the rest of the app.

**Acceptance criteria:**

- Valid token + valid new password updates the password and clears the reset token.
- Expired token returns 401.
- Already-used token returns 401.
- Wrong token returns 401.
- After reset, the user cannot log in with the old password.
- After reset, all existing sessions for the user are invalidated.

---

## Step 8 — Security hardening and edge cases

**What to do:**

- **Rate limiting:** Add rate limiting to both `/api/auth/forgot-password` and `/api/auth/reset-password` (e.g., 5 requests per 15 minutes per IP) to prevent abuse.
- **Token comparison:** Use a constant-time comparison function (e.g., `crypto.timingSafeEqual`) when comparing the submitted token hash against the stored hash to prevent timing attacks.
- **Session invalidation:** After a successful password reset, invalidate all existing sessions/tokens for that user so an attacker with a stolen session is logged out.
- **HTTPS enforcement:** Ensure the reset link only works over HTTPS (set the `Secure` flag on any cookies issued during the reset flow).
- **Log without secrets:** Log reset events for audit purposes, but never log the token or password in plain text.

**Acceptance criteria:**

- More than 5 reset requests from the same IP within 15 minutes returns 429.
- Timing attack on token comparison does not leak information (use constant-time compare).
- After a password reset, an existing session for that user is invalidated.

---

## Step 9 — Testing

**What to do:**

- **Unit tests:**
  - `generateResetToken` produces unique, high-entropy tokens.
  - Token hash verification works correctly.
  - Expired tokens are rejected.
  - Password hashing uses the correct algorithm.
- **Integration tests:**
  - Full flow: request reset -> receive email -> click link -> submit new password -> log in with new password.
  - Token cannot be reused after a successful reset.
  - Expired token is rejected.
  - Rate limiting triggers after too many requests.
- **Manual QA:**
  - Test the full flow in a staging environment.
  - Verify email renders correctly in multiple clients.
  - Test on mobile and desktop browsers.

---

## Summary of endpoints and routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/forgot-password` | Request a reset token via email |
| POST | `/api/auth/reset-password` | Submit a new password with a reset token |
| GET | `/forgot-password` | Frontend: request reset page |
| GET | `/reset` | Frontend: set new password page |

## Files to create / modify

| File | Action |
|------|--------|
| `db/migrations/XXXX_add_reset_token_to_users.sql` | Create |
| `src/auth/generateResetToken.js` | Create |
| `src/auth/forgotPassword.js` | Create |
| `src/auth/resetPassword.js` | Create |
| `src/emails/resetPassword.html` | Create |
| `src/routes/auth.js` | Modify (add two new routes) |
| `src/pages/ForgotPassword.jsx` (or equivalent) | Create |
| `src/pages/ResetPassword.jsx` (or equivalent) | Create |
| `src/routes/pages.js` (or equivalent) | Modify (add two new page routes) |
| `src/middleware/rateLimit.js` | Modify (add rate limiting for auth endpoints) |