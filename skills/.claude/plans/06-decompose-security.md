## Security Review: Password Reset via Email
Surfaces touched: input handling (email addresses, password fields, token query params), auth & authorization (token validation, session invalidation, password update), secrets & config (token storage, password hashing), output & injection (email link construction, error messages).

### Findings

1. **Token storage — raw token must never be stored in the database**
   - file: Step 2 (POST /auth/reset-request)
   - vuln: Storing the raw reset token in `users.reset_token` means a database breach directly exposes all pending reset tokens, allowing an attacker to reset any user's password.
   - severity: critical
   - Exploit: An attacker with database read access queries `users.reset_token` for any user, then visits `/auth/reset?token=<value>` and sets a new password.
   - Fix: Store only `SHA-256(raw_token)` in the database. Compare by hashing the incoming token and doing a DB lookup. The raw token is only transmitted in the email link.

2. **Token entropy — must use cryptographically secure random generation**
   - file: Step 2 (POST /auth/reset-request)
   - vuln: Using a non-cryptographic random function (e.g., `Math.random()`, `rand()`, UUID v4 without crypto source) produces tokens with insufficient entropy. An attacker could brute-force or predict tokens.
   - severity: critical
   - Exploit: An attacker observes a valid token, guesses the generation algorithm, and generates candidate tokens until one matches a user's pending reset.
   - Fix: Use `crypto.randomBytes(32)` (Node.js) or equivalent CSPRNG to generate at least 256 bits of entropy. Hex-encode to produce a 64-character token.

3. **User enumeration via reset request**
   - file: Step 2 (POST /auth/reset-request)
   - vuln: If the response differs for registered vs. unregistered emails (e.g., different status codes, response times, or messages), an attacker can enumerate registered email addresses.
   - severity: high
   - Exploit: An attacker scripts requests to `/auth/reset-request` with a list of emails, observes which ones trigger an email send (via timing or response body difference), and builds a list of registered accounts.
   - Fix: Always return HTTP 200 with an identical JSON body regardless of whether the email exists. Do not log which emails triggered an actual email send in a way exposed to the client.

4. **Token expiry — must be enforced server-side and be short-lived**
   - file: Step 2 (POST /auth/reset-request), Step 4 (GET /auth/reset)
   - vuln: If the expiry is too long (e.g., 24 hours) or not enforced, a leaked or intercepted token remains valid for an extended window.
   - severity: medium
   - Exploit: An attacker intercepts a reset email (e.g., via email server compromise, MITM on unencrypted link, or mailbox access) and uses the token within its validity window.
   - Fix: Set expiry to 15 minutes or less. Always compare `reset_token_expires_at > NOW()` server-side on every access. Reject expired tokens even if the hash matches.

5. **Token reuse — consumed tokens must be invalidated immediately**
   - file: Step 5 (POST /auth/reset)
   - vuln: If the token is not deleted after a successful password change, the same token can be reused to change the password again (potentially by an attacker who intercepted the first reset).
   - severity: high
   - Exploit: Attacker intercepts the reset link, changes the password, then reuses the same token (or the attacker waits for the legitimate user to click, and the first click already succeeded).
   - Fix: Delete `reset_token` and `reset_token_expires_at` (set to NULL) immediately after a successful password update. This makes the token single-use.

6. **Session invalidation on password reset**
   - file: Step 5 (POST /auth/reset)
   - vuln: If existing sessions are not invalidated after a password reset, an attacker who performed the reset retains access via their active session. Conversely, if sessions are not invalidated, a legitimate user's other devices stay logged in with the old password.
   - severity: high
   - Exploit: Attacker resets the password, then continues using their existing session (if invalidation is missing). Or: legitimate user resets password on mobile, but desktop session remains active with old credentials.
   - Fix: Invalidate all existing sessions for the user. Either delete all rows in the sessions table for that user, or increment a `session_version` / `password_changed_at` column that existing sessions must check.

7. **Password must not be returned in any response or log**
   - file: Step 5 (POST /auth/reset)
   - vuln: If the new password is logged, included in error messages, or stored in plaintext in any audit trail, it becomes exposed.
   - severity: high
   - Exploit: An attacker triggers a reset with a malformed password, reads server logs or error responses to capture the password value.
   - Fix: Never log the password field. Never include it in error responses. Use parameterized queries and ensure the password hashing library does not echo the input.

8. **Email link must use HTTPS**
   - file: Step 3 (email-sending helper)
   - vuln: If the reset link uses `http://` instead of `https://`, the token is transmitted in cleartext over the network, vulnerable to interception.
   - severity: medium
   - Exploit: An attacker on the same network as the user (e.g., public Wi-Fi) intercepts the HTTP request to the reset page and captures the token.
   - Fix: Always construct the reset link with `https://`. Validate or configure the base URL in the email-sending helper to enforce HTTPS.

9. **Rate limiting on reset endpoints to prevent abuse**
   - file: Step 6 (rate limiting)
   - vuln: Without rate limiting, an attacker can flood users with reset emails (DoS) or brute-force tokens if entropy is insufficient.
   - severity: medium
   - Exploit: An attacker sends thousands of reset requests to a target email address, causing email service abuse or delivering a poor user experience.
   - Fix: Implement per-IP rate limiting (Step 6). Also consider per-email rate limiting (max 1 reset request per email per 5 minutes) to prevent targeting a single address.

10. **Password strength validation on reset**
    - file: Step 5 (POST /auth/reset)
    - vuln: If the new password is not validated for minimum strength, users can set weak passwords that are easily compromised.
    - severity: low
    - Exploit: A user sets a password like "12345678" which is trivially guessable or crackable.
    - Fix: Enforce a minimum password length (8 characters) and optionally check against a blocklist of common passwords. Reuse the existing password validation logic from the login/signup flow if available.

### Verdict: FIX FIRST

Findings 1, 2, 5, and 6 are critical/high severity and must be addressed in the implementation. The deconstruction plan already includes the correct fixes for most of these (SHA-256 hashing, CSPRNG, single-use tokens, session invalidation), but the plan text should be reviewed to confirm each fix is explicitly coded, not just described. Findings 3, 8, and 9 require explicit attention in the implementation of Steps 2, 3, and 6 respectively.