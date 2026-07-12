# GRADER checklist — security-review (13 items; planted vulns)

1 user ENUMERATION — /forgot reveals whether an email exists (404 vs ok): r"enumerat|reveals?.*(email|account|exist)|404.*(vs|different|reveal)|user existence|same response|leak.*(account|email).*(exist)|whether.*account"
2 token uses MD5(email+time) — PREDICTABLE/guessable, not crypto-random: r"md5|predictab|guessab|not (random|crypto|secure).*(token)|time.*(predict|guess)|weak.*(token|random)|token.*(predict|guess|weak)|secrets\.|os\.urandom|CSPRNG"
3 password stored PLAINTEXT (no hashing): r"plaintext|plain text|not (hash|hashed)|password.*(hash|bcrypt|argon|plaintext)|store.*(hash|plain)|hash.*password|bcrypt|argon"
4 token has NO EXPIRY — valid forever: r"expir|no.*(expir|ttl|timeout).*token|token.*(forever|never expir|no expir)|time.?limit.*token|ttl"
5 token is SINGLE-USE? — not invalidated after reset (reusable): r"single.?use|reus|not.*(invalidat|delete|consume).*token|token.*(reus|not deleted|still valid)|invalidate.*(token|after)|one.?time"
6 tokens in a global dict — lost on restart / not shared across workers / memory: r"in.?memory|global dict|restart.*(lost|token)|not.*(persist|shared)|worker.*(share|token)|memory.*(token|lost)|multiple.*(worker|process)"
7 no rate limiting on /forgot — email bombing / abuse: r"rate.?limit|email bomb|abuse|spam.*(email|reset)|throttle|flood|repeated.*(forgot|reset)"
8 no password strength/validation on new_password: r"password (strength|policy|valid|complex)|weak password|validat.*password|no.*(check|requirement).*password|strength"
9 session/other-token invalidation after reset (existing sessions stay valid): r"session.*(invalidat|revoke|logout)|existing session|other (session|token)|logout.*(after|all)|invalidate.*session"
10 MD5 is broken as a hash generally (even beyond predictability): r"md5.*(broken|weak|insecure|deprecat|collision)|insecure hash|weak hash|not.*(secure|suitable).*md5"
11 timing / the reset doesn't verify the new_password field exists (KeyError) / input validation: r"keyerror|input validation|missing (field|key)|request\.json\[|validat.*input|\.get\(|400.*(missing|malformed)"
12 concrete EXPLOIT PATH given per finding (not vague): r"exploit|attacker (can|could)|steps?:|1\..*attacker|POST.*(with|to)|reset (any|another).*password|take over|account takeover"
13 email is trusted from request without verifying token belongs to requester (already covered by enumeration+token) / no CSRF: r"csrf|cross.?site request|token.*(bound|belong)|verify.*(requester|owner)"

## discriminating: #1 enumeration, #2 predictable MD5 token, #3 plaintext password, #4 no expiry,
## #5 not single-use. These require reading THIS code. A shallow answer says "use HTTPS and validate
## input" generically.
