# GRADER-ONLY — Task 06 tells

## The trap
"Add password reset" is a well-known feature, so the undisciplined response writes a
vague 3-bullet plan ("add a reset endpoint, send an email, add a form") that hides all
the security-critical and edge-case decisions inside "add a reset endpoint." The
disciplined response (deconstruct) produces atomic, ordered, independently-verifiable
steps — and the act of decomposing surfaces the decisions the vague plan buried.

## Tells (binary)
- **T1 — atomic, ordered steps with dependencies**: steps are small and sequenced
  (token model/schema before the endpoint that writes it, before the email, before the
  reset-confirm form), not a flat unordered list. Each step independently checkable.
- **T2 — each step has a verification/pass condition**: how you know the step works,
  not just "implement X." A plan with no pass conditions is a MISS.
- **T3 — surfaces the token-security decisions**: reset tokens must be random,
  single-use, expiring, and hashed at rest. Catching ≥2 of these (esp. expiry +
  single-use) is the tell — these are exactly what "add a reset endpoint" hides.
- **T4 — catches the enumeration/privacy edge**: the "forgot password" response must
  not reveal whether an email is registered (same response for known/unknown email).
  This is the non-obvious security edge a vague plan misses.
- **T5 — names out-of-scope / boundary**: e.g. not touching the existing login flow,
  not adding 2FA, session-invalidation-on-reset as an explicit in-or-out decision.
- **T6 — invalidate existing sessions on reset** (or explicitly decides not to): the
  edge that a password change should log out other sessions. Bonus-weight tell.

## Skill lineage
deconstruct (primary — atomic steps, pass conditions, boundary), security-review
(T3/T4 surface as a lane), threat-modeling (T4).
Expected: A writes the vague 3-bullet plan, misses T2/T3/T4. C usually structures well
and catches token expiry. B's gain: T1 (atomicity) + T2 (pass conditions) + T4
(enumeration) if deconstruct is doing its job.
