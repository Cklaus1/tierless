# Threat Model: B2B SaaS File-Sharing Feature

## 1. Assets Worth Protecting

| Asset | Why It Matters |
|---|---|
| Uploaded files (content) | Confidential business data; exposure violates customer contracts and privacy laws. |
| Shareable links (URLs + tokens) | Act as the access credential for the link-based flow; compromise = unauthorized access. |
| Passwords (for password-protected links) | If weak or leaked, they nullify the password protection entirely. |
| User accounts / session tokens | Compromise enables an attacker to upload, share, or delete files on behalf of a legitimate user. |
| File metadata (names, sizes, upload timestamps, S3 keys) | Can reveal organizational structure, project names, or sensitive context even without file content. |
| S3 bucket configuration (ACLs, bucket policies, CORS settings) | Misconfiguration is the single most common cause of public data exposure in cloud storage. |
| Download logs / audit trails | Used for compliance and incident response; tampering hides attacker activity. |
| The SaaS application itself (source code, API endpoints, infrastructure) | A compromised file-sharing service can serve as a pivot into the broader platform. |

---

## 2. Realistic Attackers

| Attacker Profile | Capability | Motivation |
|---|---|---|
| **External unauthenticated attacker** | Internet-facing; no valid account. Can observe and manipulate HTTP traffic, guess URLs, run automated scanners. | Steal files from exposed links; harvest data. |
| **Authenticated user (lateral)** | Has a valid account in the same or a different tenant. Can upload files, create links, view their own uploads. | Access files shared by colleagues or other tenants (data exfiltration, competitive intelligence). |
| **Malicious insider (privileged user)** | Has elevated permissions (e.g., support engineer, admin). Can access logs, S3 buckets, or admin APIs. | Sabotage, data theft, or compliance violation. |
| **Compromised third-party service** | The SaaS app integrates with external services (e.g., email delivery, analytics, CDN). | Supply-chain pivot: attacker gains access via a weaker link in the chain. |
| **Search engine / crawler** | Not a traditional attacker; passively indexes public URLs. | Accidental or deliberate indexing of share links, making them discoverable. |

---

## 3. Data Flow and Trust Boundaries

```
[User Browser]
     |
     |  (1) Upload file  POST /api/files
     v
[App Server / API]  <--- Trust Boundary 1: Untrusted client -> Trusted service
     |
     |  (2) Store in S3  PUT s3://bucket/{tenant-id}/{file-id}
     v
[Cloud Object Storage (S3)]  <--- Trust Boundary 2: App server -> External storage
     |
     |  (3) Generate share link  GET /share/{token}
     v
[App Server / API]  <--- Trust Boundary 3: Unauthenticated user -> Trusted service
     |
     |  (4) Serve file  GET s3://bucket/{tenant-id}/{file-id}  (presigned URL or server-side fetch)
     v
[Recipient Browser]  (may or may not have an account)
```

Key trust boundaries:
- **Boundary 1**: Client-to-server (upload path). The browser is fully untrusted.
- **Boundary 2**: Server-to-S3. The app server is trusted; S3 must enforce least-privilege access.
- **Boundary 3**: Server-to-client (download path). The recipient may be unauthenticated and potentially malicious.

---

## 4. Threats (STRIDE-Based Enumeration)

### T1: Insecure Direct Object Reference (IDOR) on Share Links

- **STRIDE category**: Forgery / Authorization bypass
- **What could go wrong**: Share links use sequential or predictable tokens (e.g., `/share/abc123`). An attacker iterates tokens and downloads files they do not own. If the link is not scoped to the requesting user's tenant, cross-tenant data leakage occurs.
- **Mitigation**:
  - Use cryptographically random, high-entropy tokens (e.g., 128-bit UUIDs or URL-safe base64 tokens).
  - Enforce tenant isolation on every download request: verify the file belongs to the tenant associated with the link token.
  - Do not rely on "security through obscurity" -- treat link tokens as credentials, not as access control.

### T2: Link Enumeration / Brute-Force Scanning

- **STRIDE category**: Information disclosure
- **What could go wrong**: An attacker runs an automated scanner against the `/share/` endpoint, trying thousands of tokens per second. If tokens have low entropy or the rate limit is absent, the attacker can enumerate valid links and download files.
- **Mitigation**:
  - Use 128+ bits of entropy in link tokens.
  - Apply strict rate limiting on the share endpoint (e.g., 10 requests per minute per IP, with exponential backoff).
  - Return generic 404 responses for invalid tokens (do not distinguish "token not found" from "link expired").
  - Log and alert on anomalous scan patterns.

### T3: Missing Access Expiration (Perpetual Links)

- **STRIDE category**: Denial of service / Information disclosure
- **What could go wrong**: A user creates a share link without setting an expiration. The link remains valid indefinitely. If the link is ever posted publicly (e.g., on a forum, social media), the file is permanently exposed.
- **Mitigation**:
  - Enforce a maximum link lifetime (e.g., 30 days) configurable by the organization admin.
  - Default to a reasonable expiration (e.g., 7 days) that admins can tighten but not relax beyond the maximum.
  - Provide a "revoke link" action that immediately invalidates the token.
  - Periodically clean up expired links and their associated metadata.

### T4: Weak or Missing Password Protection

- **STRIDE category**: Forgery / Information disclosure
- **What could go wrong**:
  - Passwords are stored in plaintext or with a weak hash (e.g., MD5), allowing offline cracking if the database is compromised.
  - Passwords are too short or allow common patterns, enabling brute-force guessing.
  - No rate limiting on password verification, allowing rapid guessing.
  - Password is transmitted over HTTP (not HTTPS), allowing network interception.
- **Mitigation**:
  - Hash passwords with a memory-hard KDF (Argon2id or bcrypt with cost >= 12).
  - Enforce minimum password length (e.g., 8 characters) and optionally a complexity policy.
  - Rate-limit password verification attempts (e.g., 5 attempts per minute per link).
  - Enforce HTTPS for all link access; reject HTTP requests with a redirect to HTTPS.
  - Do not log or cache passwords in application logs, CDN logs, or proxy headers.

### T5: Cross-Tenant Data Leakage

- **STRIDE category**: Information disclosure / Authorization bypass
- **What could go wrong**: A bug in the download handler serves a file from tenant A to a request authenticated as tenant B (or unauthenticated). This can happen if the share link token is not properly mapped to the owning tenant, or if S3 bucket policies are too permissive.
- **Mitigation**:
  - Store a tenant ID alongside each share link token in the database and enforce it on every access.
  - Use per-tenant S3 key prefixes (e.g., `s3://bucket/tenant-{id}/`) and scope IAM policies to each prefix.
  - Use presigned URLs generated server-side with short TTLs, never expose raw S3 keys to clients.
  - Add automated regression tests that attempt cross-tenant access for every change to the download path.

### T6: Malicious File Upload (Weaponized Files)

- **STRIDE category**: Denial of service / Execution
- **What could go wrong**: An attacker uploads a file with a crafted name, type, or content that exploits the application:
  - **Path traversal** in the filename (e.g., `../../etc/passwd`) writes outside the intended directory.
  - **Double extensions** (e.g., `report.exe.pdf`) cause downstream systems to misinterpret the file type.
  - **Oversized files** exhaust disk or memory, causing denial of service.
  - **Malware-infected files** are later downloaded by other users, spreading malware.
  - **XML/JSON/CSV files** with malicious payloads trigger XXE, SSRF, or injection in downstream parsers.
- **Mitigation**:
  - Sanitize filenames: strip path separators, null bytes, and leading/trailing whitespace; use a safe character whitelist.
  - Enforce file size limits (e.g., 500 MB) and reject files exceeding the limit before any processing.
  - Validate and normalize MIME types by inspecting file magic bytes, not just the Content-Type header.
  - Store files in an isolated S3 bucket with no execute permissions; never serve files through a web server that could interpret them as code.
  - Scan uploaded files with a malware scanner (e.g., ClamAV) before making them available for download.
  - Use a Content-Disposition header with `attachment` to force download rather than inline rendering.

### T7: Denial of Service via File Upload

- **STRIDE category**: Denial of service
- **What could go wrong**: An attacker (authenticated or unauthenticated, if upload is open) floods the upload endpoint with large files, exhausting:
  - S3 storage quotas or incurring excessive costs.
  - Application server memory (if files are buffered in memory before upload).
  - Network bandwidth.
- **Mitigation**:
  - Use client-side presigned URLs for direct-to-S3 uploads so the application server never buffers file content.
  - Enforce per-user and per-tenant upload quotas (file count and total storage).
  - Set S3 bucket lifecycle policies to auto-delete files after a configurable period.
  - Enable S3 request cost alerts and budget alarms.
  - Limit concurrent upload sessions per user.

### T8: Link Token Leakage via Referrer Headers

- **STRIDE category**: Information disclosure
- **What could go wrong**: A user clicks a share link, then clicks an outbound link to a third-party site. The referrer header includes the full share URL (including the token), leaking the credential to the third party. If the third party logs referrers, the link becomes discoverable.
- **Mitigation**:
  - Set `Referrer-Policy: no-referrer-when-downgrade` or `no-referrer` on the share page.
  - Consider using a redirect page that strips the token before forwarding to the file download.
  - Document this risk in the product security FAQ for enterprise customers.

### T9: Link Token Leakage via Browser History / Logs

- **STRIDE category**: Information disclosure
- **What could go wrong**: Share links containing tokens are stored in browser history, proxy logs, DNS logs, or corporate firewall logs. A person with access to any of these (e.g., an IT admin, a shared workstation user) can replay the link.
- **Mitigation**:
  - Accept this as an inherent risk of URL-based credentials; mitigate with short expiration times and revocation capability.
  - For high-sensitivity use cases, offer a download page that requires a separate password (not embedded in the URL).
  - Educate users not to share links in public channels.

### T10: Server-Side Request Forgery (SSRF) via File URL

- **STRIDE category**: Request forgery
- **What could go wrong**: If the upload flow allows users to provide a URL to fetch a file from (e.g., "import from URL"), an attacker provides `http://localhost:8080/admin` or `http://169.254.169.254/latest/meta-data/` to access internal services or cloud metadata endpoints.
- **Mitigation**:
  - If URL-based import exists, validate the URL against an allowlist of permitted domains.
  - Block requests to private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16).
  - Use a dedicated egress proxy for outbound requests; do not allow the application server to make arbitrary outbound connections.

### T11: Insufficient Audit Logging

- **STRIDE category**: Information disclosure (post-incident)
- **What could go wrong**: File uploads, downloads, link creations, and deletions are not logged, or logs do not include sufficient detail (who, what, when, from where). After a data breach, the organization cannot determine the scope of exposure or comply with regulatory requirements.
- **Mitigation**:
  - Log every file upload, download, link creation, link revocation, and deletion event.
  - Include: user ID, tenant ID, file ID, share token, IP address, user agent, timestamp, and outcome (success/failure).
  - Store logs in an immutable, append-only store (e.g., S3 with object lock, or a WORM-compliant system).
  - Provide an audit log view for organization admins.
  - Alert on anomalous patterns (e.g., a single user downloading 100+ files in an hour).

### T12: Cross-Site Request Forgery (CSRF) on Upload / Link Management

- **STRIDE category**: Forgery
- **What could go wrong**: An authenticated user visits a malicious site that submits a POST to `/api/files` or `/api/links/revoke`. If the upload or link-management endpoints rely solely on cookie-based authentication without CSRF tokens, the attacker can force actions on behalf of the user.
- **Mitigation**:
  - Use CSRF tokens (Samesite=Strict or SameSite=Lax cookies, or double-submit cookie pattern) on all state-changing endpoints.
  - Require re-authentication for sensitive actions (e.g., deleting files, revoking links).
  - Use `Content-Type: application/json` requests and verify the Content-Type header server-side (browsers cannot set arbitrary Content-Type in cross-origin forms).

### T13: Cross-Site Scripting (XSS) via File Metadata

- **STRIDE category**: Input validation / Execution
- **What could go wrong**: A file name or metadata field (e.g., description, tags) contains script content (e.g., `<script>document.cookie</script>`). When another user views the file in a web UI, the malicious content is rendered as HTML/JavaScript, stealing session cookies or performing actions as the victim.
- **Mitigation**:
  - Escape all file metadata when rendering in HTML contexts (use a templating engine with auto-escaping).
  - Set `Content-Security-Policy: default-src 'self'` on all pages that display file metadata.
  - Validate and sanitize metadata fields on input; reject or strip HTML tags.
  - Use `X-Content-Type-Options: nosniff` to prevent MIME-type sniffing.

### T14: Insecure Direct Object Reference on S3 Keys

- **STRIDE category**: Authorization bypass
- **What could go wrong**: If the application exposes S3 object keys or presigned URLs directly to the client (e.g., in a response body or JavaScript), an attacker can reuse or modify these URLs to access files they should not see. Presigned URLs with long TTLs amplify this risk.
- **Mitigation**:
  - Never expose raw S3 keys to clients. Always generate presigned URLs server-side at request time.
  - Keep presigned URL TTLs short (e.g., 5-15 minutes).
  - Regenerate presigned URLs on each download request rather than caching them on the client.
  - Scope S3 IAM policies to the minimum required permissions (s3:GetObject only, no s3:PutObject or s3:DeleteObject).

### T15: CORS Misconfiguration

- **STRIDE category**: Authorization bypass / Information disclosure
- **What could go wrong**: The S3 bucket or the application server has an overly permissive CORS policy (e.g., `Access-Control-Allow-Origin: *`). This allows any website to make cross-origin requests to the file-sharing endpoints, potentially reading file contents or enumerating links from a browser context.
- **Mitigation**:
  - Restrict CORS `AllowedOrigin` to the application's actual domain(s).
  - Do not use `*` for CORS on any endpoint that returns sensitive data.
  - If the download endpoint is accessed by unauthenticated users, ensure CORS is configured to allow the application domain but not arbitrary origins.
  - Test CORS configuration with automated security scans.

### T16: Timing Side-Channel on Password Verification

- **STRIDE category**: Information disclosure
- **What could go wrong**: The password comparison uses a non-constant-time string comparison. An attacker measures response times across many requests and can determine, byte by byte, whether each character of the password is correct, accelerating brute-force attacks.
- **Mitigation**:
  - Use a constant-time comparison function (e.g., `crypto.timingSafeEqual` in Node.js, `hmac.compare_digest` in Python).
  - Add artificial delay (e.g., 200-500 ms) to password verification responses to further slow attackers.
  - Combine with rate limiting (see T4).

### T17: Data in Transit Interception (Man-in-the-Middle)

- **STRIDE category**: Information disclosure
- **What could go wrong**: File uploads or downloads occur over unencrypted HTTP, allowing a network attacker to intercept file content, tokens, or passwords. Even with HTTPS, a misconfigured TLS setup (weak ciphers, expired certificates, missing HSTS) can enable downgrade attacks.
- **Mitigation**:
  - Enforce HTTPS everywhere; redirect all HTTP traffic to HTTPS.
  - Use TLS 1.2 or higher; disable weak cipher suites.
  - Enable HSTS (HTTP Strict Transport Security) with a long max-age.
  - Use certificate pinning or mutual TLS for any internal service-to-service communication involving file data.
  - Validate S3 presigned URL generation uses HTTPS endpoints.

### T18: Link Sharing to Unauthorized Recipients (No Recipient Restriction)

- **STRIDE category**: Authorization bypass
- **What could go wrong**: A share link is sent to an unintended recipient (e.g., wrong email, public channel). Because anyone with the link can download the file, there is no mechanism to restrict access to specific individuals beyond the link itself.
- **Mitigation**:
  - Offer email-verified access: require the recipient to enter their email and verify it via a code before downloading.
  - Offer IP-based restrictions (e.g., allow downloads only from specific CIDR ranges).
  - Allow link creators to set a maximum download count (e.g., "this link works for 5 downloads, then expires").
  - Clearly communicate to users that share links are equivalent to passwords -- anyone with the link can access the file.

### T19: S3 Bucket-Level Security Misconfiguration

- **STRIDE category**: Information disclosure / Authorization bypass
- **What could go wrong**: The S3 bucket is accidentally set to public (e.g., `Block Public Access` is disabled, or a bucket policy grants `s3:GetObject` to `*`). This exposes all files in the bucket to the internet, regardless of share link controls.
- **Mitigation**:
  - Enable S3 Block Public Access at the bucket level (all four settings: block public ACLs, block public policies, restrict public shares, block public access).
  - Never grant `s3:GetObject` to `Principal: *` on the bucket policy.
  - Use S3 Access Points or prefix-based IAM policies to restrict access to specific tenants.
  - Run automated S3 configuration audits (e.g., AWS Config rules, CSPM tools) to detect and remediate misconfigurations.
  - Enable S3 server access logging and send logs to a separate, immutable bucket.

### T20: File Deletion / Tampering by Unauthorized User

- **STRIDE category**: Tampering / Denial of service
- **What could go wrong**: An authenticated user can delete files they did not upload, or delete files belonging to other tenants. This can be a bug in the authorization logic or a feature that is too permissive.
- **Mitigation**:
  - Enforce ownership-based authorization: users can only delete files they uploaded (or that their tenant admin explicitly permits).
  - Use soft deletes (mark as deleted, do not immediately remove from S3) with a configurable retention period.
  - Log all deletion events in the audit trail.
  - Provide a recycle bin / recovery window for accidental deletions.

---

## 5. Summary of Key Risk Areas

| Risk Area | Severity | Likelihood | Top Threats |
|---|---|---|---|
| Link token security | Critical | High | T1, T2, T8, T9 |
| Cross-tenant isolation | Critical | Medium | T5, T14, T19 |
| Upload input validation | High | High | T6, T7, T10 |
| Password protection | High | Medium | T4, T16 |
| TLS / transport security | Medium | Low | T17 |
| XSS / CSRF | Medium | Medium | T12, T13 |
| Audit & compliance | Medium | Medium | T11 |
| Recipient access control | Medium | High | T3, T18 |

---

## 6. Architectural Recommendations

1. **Presigned URLs, not server-side proxying**: Generate short-lived presigned URLs server-side and return them to the client. This avoids the application server becoming a bottleneck for file downloads and reduces the attack surface on the download path.

2. **Per-tenant S3 key prefixes with scoped IAM**: Each tenant's files live under `s3://bucket/tenant-{id}/`. IAM policies grant access only to the specific prefix. This provides defense-in-depth even if the application layer has a bug.

3. **Defense in depth for link tokens**: Combine high-entropy tokens with expiration, download limits, password protection, and revocation. No single control is sufficient.

4. **Zero trust on the download path**: Every download request must re-validate: valid token, not expired, not revoked, tenant match, rate limit check, and (if applicable) password check. Treat every request as untrusted.

5. **Immutable audit logging**: Log all file operations to an append-only store. This is the last line of defense for incident response and compliance.