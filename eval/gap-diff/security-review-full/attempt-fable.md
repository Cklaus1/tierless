# Security Review — Flask Password-Reset Flow

Every finding below is a real, exploitable weakness in the code as written. They are
ordered roughly by severity. The first three combine into a **remote, unauthenticated
account-takeover of any user**, so they should be treated as critical.

---

## 1. Predictable / forgeable reset tokens (CRITICAL — account takeover)

```python
token = hashlib.md5((email + str(time.time())).encode()).hexdigest()
```

The token is a pure function of two values the attacker either knows or can brute-force:

- `email` — the victim's address, which the attacker supplies and therefore knows exactly.
- `str(time.time())` — the server wall-clock time at the moment the request is handled.

There is **no secret and no cryptographic randomness** anywhere in the token. MD5 is not
a keyed function, so anyone who can guess the inputs can reproduce the exact token.

**Concrete exploit path:**

1. Attacker POSTs `{"email": "victim@example.com"}` to `/forgot`. This is allowed because
   `/forgot` only requires knowing the victim's email. The server creates a real token and
   stores `reset_tokens[token] = "victim@example.com"`.
2. The attacker notes the approximate time the request was served (from the HTTP `Date`
   response header, which is exact to the second, plus their own send/receive timestamps).
3. Offline, the attacker computes `md5("victim@example.com" + str(t))` for every candidate
   `t` in a small window around that second. `time.time()` yields values like
   `1712345678.1234567`; the integer part is known from the `Date` header, leaving only the
   fractional part to enumerate. Even at microsecond granularity that is ~10^6–10^7
   candidates for a one-second window, and MD5 is billions/sec on commodity hardware — the
   search completes in well under a second.
4. Each candidate is checked by POSTing it to `/reset` (or the attacker can pre-compute and
   submit the small set of matches). One of them is the real token. The attacker sets a new
   password and owns the account.

This works against **any** account, because the attacker can trigger the reset themselves.

**Fix:** Generate tokens from a CSPRNG, e.g. `secrets.token_urlsafe(32)`. Never derive a
security token from `time.time()` or any guessable value, and never use MD5 (or any fast,
unkeyed hash) for anything security-sensitive. Store only a hash of the token server-side
(see #6-adjacent note below) so a DB/memory leak doesn't expose live tokens.

---

## 2. Tokens never expire (HIGH)

```python
reset_tokens[token] = email     # no timestamp, no TTL
```

A token is valid indefinitely. Password-reset links routinely leak through browser history,
proxy/CDN logs, `Referer` headers, email forwarding, corporate mail archiving, and shared
devices. Any such leaked link remains a working master key to the account forever.

The unbounded, never-pruned dictionary is also a slow **memory-exhaustion DoS**: every
`/forgot` call (which has no rate limit — see #4) permanently adds an entry.

**Fix:** Store an expiry timestamp with each token and reject tokens older than a short
window (e.g. 15–60 minutes). Prune/expire entries. Prefer a store with native TTL (Redis,
or a DB column with an `expires_at`).

---

## 3. Tokens are not single-use / not invalidated after reset (HIGH)

```python
db.users.update_one({'email': email}, {'$set': {'password': new_password}})
return {'ok': True}
# token is never removed from reset_tokens
```

After a successful reset the token stays in `reset_tokens`, so it can be replayed to reset
the password again and again. If a token ever leaks *after* the legitimate user has used it,
the attacker can still take over the account. It also means a single reset link can be used
by multiple parties.

**Fix:** Delete the token atomically as part of consuming it —
`email = reset_tokens.pop(token, None)` — and ideally invalidate *all* outstanding reset
tokens for that user on any successful reset or password change.

---

## 4. No rate limiting on either endpoint (HIGH)

Neither `/forgot` nor `/reset` is throttled. Consequences:

- `/reset` can be hammered to brute-force tokens (amplifies #1; also makes even a
  hypothetically-random 128-bit token guessing infeasible only *because* of the token size,
  not because of any control here).
- `/forgot` can be abused for **email bombing** — flooding a victim's inbox with reset
  emails — and for user enumeration at scale (see #5).
- Unbounded `/forgot` calls feed the memory-growth issue in #2.

**Fix:** Per-IP and per-account rate limiting / lockout (e.g. Flask-Limiter), plus caps on
reset emails per account per hour.

---

## 5. User / account enumeration (MEDIUM)

```python
if not user:
    return {'error': 'no account with that email'}, 404
```

The endpoint returns a distinct 404 + message for non-existent emails and a 200 for existing
ones. An attacker can enumerate which email addresses have accounts, which is valuable for
targeted phishing and credential-stuffing. The differing DB code path also creates a
**timing** oracle even if the status/body were unified.

**Fix:** Always return the same generic 200 response ("If an account exists, a reset link
has been sent") regardless of whether the user exists, and keep the timing uniform.

---

## 6. New password stored in plaintext (CRITICAL — for stored data)

```python
db.users.update_one({'email': email}, {'$set': {'password': new_password}})
```

The submitted password is written directly to the database with **no hashing**. Any
database compromise, backup leak, log capture, or insider immediately exposes every user's
plaintext credentials — which are then reusable across other sites via credential stuffing.
The `/forgot` field name `password` here strongly implies the whole system stores plaintext.

**Fix:** Hash with a slow, salted password KDF before storing —
`argon2`, `bcrypt`, or `scrypt` (e.g. `werkzeug.security.generate_password_hash` with a
strong scheme, or `argon2-cffi`). Never store or log the raw password.

---

## 7. No password validation / strength requirements (MEDIUM)

`new_password` is accepted verbatim. There is no length check, no complexity/entropy check,
and no rejection of empty strings — `{"new_password": ""}` would set an empty password. This
lets accounts be left with trivially guessable or blank credentials.

**Fix:** Enforce minimum length and basic strength server-side; reject empty/whitespace-only
values.

---

## 8. In-memory token store breaks under real deployment (MEDIUM — reliability/security)

```python
reset_tokens = {}   # module-level global
```

- Under a multi-process WSGI server (gunicorn/uWSGI with >1 worker), a token created in
  worker A is invisible to worker B, so resets fail nondeterministically — and correctness of
  a *security* control silently depends on load-balancing luck.
- Tokens are lost on every restart/deploy.
- Combined with #2/#4, the dict grows without bound (DoS).

**Fix:** Use a shared, persistent store with TTL (Redis or the database), not a
per-process dict.

---

## 9. Missing / unsafe input handling (LOW–MEDIUM)

```python
email = request.json['email']
token = request.json['token']
new_password = request.json['new_password']
```

- `request.json` is `None` if the client doesn't send `Content-Type: application/json`,
  raising `TypeError`; missing keys raise `KeyError`. Both surface as unhandled `500`s. If
  `app.debug`/the interactive debugger is ever enabled in a reachable environment, the
  traceback (and potentially the Werkzeug debugger PIN/RCE console) is exposed.
- No type checking: `email`/`token` could be a dict, enabling **NoSQL/operator injection**
  into `db.users.find_one({'email': email})` and the `update_one` filter. For example a JSON
  body `{"email": {"$ne": null}}` to `/forgot` matches an arbitrary user; more dangerously,
  if an attacker can influence the `/reset` filter via a crafted stored value, operator
  injection into Mongo queries becomes possible. Always coerce/validate these to strings.

**Fix:** Validate that each field is present and is a string; use `request.get_json(silent=True)`
with explicit error handling; never pass raw JSON values straight into Mongo query documents.

---

## 10. Reset link delivered over the reset itself with no second factor / notification (LOW)

Possession of the token is the *only* thing required to change the password, and the real
account owner is never notified that their password changed. Even after fixing token
generation, a leaked link alone yields takeover, and the victim gets no signal.

**Fix:** Send a "your password was changed" notification email to the account on every
successful reset, and consider invalidating active sessions on password change.

---

## Summary of the critical chain

Findings **#1 + #4 (+ helped by #2, #3, #5)** compose into a practical, unauthenticated,
remote account-takeover of *any* user: trigger a reset for the victim, reconstruct the
deterministic MD5(email + time) token, and submit it to `/reset`. Finding **#6** means that
even absent the takeover, a single database leak hands out every user's plaintext password.
Both should be fixed before this code goes anywhere near production.

### Minimal corrected sketch

```python
import secrets, time
from werkzeug.security import generate_password_hash

TTL = 900  # 15 minutes

@app.route('/forgot', methods=['POST'])
def forgot():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    if isinstance(email, str):
        user = db.users.find_one({'email': email})
        if user:
            token = secrets.token_urlsafe(32)
            # store a HASH of the token, with expiry, in a shared store
            store.set(hash_token(token), email, ex=TTL)
            send_email(email, f"Reset here: https://app.com/reset?token={token}")
    return {'ok': True}   # identical response regardless of existence

@app.route('/reset', methods=['POST'])
def reset():
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    new_password = data.get('new_password')
    if not isinstance(token, str) or not isinstance(new_password, str) or len(new_password) < 12:
        return {'error': 'invalid request'}, 400
    email = store.get_and_delete(hash_token(token))  # single-use + TTL enforced
    if not email:
        return {'error': 'invalid or expired token'}, 400
    db.users.update_one({'email': email},
                        {'$set': {'password': generate_password_hash(new_password)}})
    # invalidate sessions + send "password changed" notification here
    return {'ok': True}
```
(Rate limiting via Flask-Limiter on both routes is assumed in addition to the above.)
