# Threat Model: B2B SaaS File-Sharing Feature

## 1. Assets Worth Protecting

| Asset | Why It Matters |
|---|---|
| Uploaded files (content) | Confidential business documents, PII, intellectual property |
| Shareable links (URLs) | Act as access tokens; if leaked, grant unauthorized access |
| Passwords (if set) | Secondary access control; weak or leaked passwords bypass link security |
| User accounts / session tokens | Compromise enables bulk download, link generation abuse, or lateral movement |
| S3 bucket and its contents | Central storage; breach exposes all tenant data |
| Tenant isolation boundaries | Multi-tenant SaaS; cross-tenant data access is a critical failure |
| Audit logs | Required for compliance; tampering hides breaches |
| API keys / service credentials | Compromise enables direct S3 access or API abuse |
| Link metadata (expiry, password hash, download count) | Leaking metadata can aid targeted attacks |

---

## 2. Realistic Attackers

| Attacker Profile | Capability | Motivation |
|---|---|---|
| **External unauthenticated user** | Internet access, can guess or obtain share links | Steal files, exfiltrate data |
| **Malicious insider (tenant admin or user)** | Valid account, can generate links, view logs | Data exfiltration, sabotage, compliance violation |
| **Competitor / scraper** | Automated access, link enumeration | Industrial espionage, data harvesting |
| **Compromised third-party service** | Access to credentials or network path | Supply-chain attack, data theft |
| **Cloud provider insider** | Access to S3 infrastructure (theoretical) | Mass data breach |
| **Man-in-the-middle** | Network interception | Session hijacking, link interception |

---

## 3. Trust Boundaries

1. **Client <-> Application Server** (HTTPS)
2. **Application Server <-> S3** (internal network / VPC)
3. **Application Server <-> Authentication Provider** (OAuth / SAML / internal auth)
4. **S3 Bucket <-> External Internet** (should be blocked; access only via signed URLs or application server)
5. **Tenant A <-> Tenant B** (multi-tenant isolation)
6. **Authenticated user <-> Share link** (unauthenticated download path)

---

## 4. Threats, Attack Scenarios, and Mitigations

### T1: Public Link Enumeration / Brute-Forcing

**What could go wrong:** An attacker iterates through possible share link IDs (UUIDs, hashes) to discover valid links. If link IDs are sequential, short, or predictable, enumeration is trivial.

**Impact:** Unauthorized access to files; data breach.

**Mitigation:**
- Use cryptographically random, high-entropy link identifiers (e.g., 128+ bits of randomness, URL-safe base64 encoding).
- Rate-limit link access endpoints.
- Monitor for anomalous access patterns (high failure rate, scanning behavior).
- Consider link revocation API so users can invalidate links after sharing.

---

### T2: Link Interception (Man-in-the-Middle)

**What could go wrong:** A share link sent via email, chat, or messaging is intercepted in transit. Since the link is a bearer token, interception equals unauthorized access.

**Impact:** Unauthorized file access by any party who intercepts the link.

**Mitigation:**
- Enforce HTTPS for all link access with HSTS.
- Do not include sensitive identifiers in email body URLs that may be logged; use link shorteners or redirect endpoints that do not leak the full URL in referer headers.
- Optionally, bind links to the recipient's email address (require email verification before download).

---

### T3: Link Persistence / No Expiry

**What could go wrong:** If the user does not set an expiry, the link remains valid indefinitely. Compromised email accounts, forwarded links, or leaked URLs grant permanent access.

**Impact:** Long-tail exposure; files accessible years after they should have been.

**Mitigation:**
- Enforce a maximum link lifetime (e.g., 30 days) as a system default.
- Require expiry as the default; make it opt-out only with admin approval.
- Provide automatic link revocation after a set number of downloads.

---

### T4: Password Protection Weaknesses

**What could go wrong (a):** Passwords stored as plaintext or weak hashes (MD5, unsalted SHA-256) in the database. A database breach reveals all share-link passwords.

**What could go wrong (b):** No rate limiting on password verification. An attacker can brute-force weak passwords (e.g., "password123") at high speed.

**What could go wrong (c):** Password transmitted in plaintext over HTTP.

**Impact:** Unauthorized access to password-protected files.

**Mitigation:**
- Store passwords using bcrypt, scrypt, or Argon2id with appropriate work factors.
- Enforce a minimum password complexity policy (e.g., 8+ characters, mixed case, or numeric).
- Rate-limit password verification attempts (e.g., 5 attempts per minute per IP).
- Enforce HTTPS; never transmit passwords over unencrypted connections.
- Consider using a single-use token instead of a password for simpler, more secure access control.

---

### T5: S3 Direct Access / Bypassing Application Server

**What could go wrong:** The S3 bucket is misconfigured to allow public read access, or signed URLs are generated with overly permissive policies (e.g., no IP restriction, no user binding, excessively long TTL). An attacker obtains a signed URL through logs, referer headers, or URL sharing and accesses files without application-server authorization checks.

**Impact:** Complete bypass of application-level access controls; mass data exfiltration.

**Mitigation:**
- S3 bucket must have no public access; all access must go through the application server or use short-lived, signed URLs.
- Signed URLs must be short-lived (e.g., 5-15 minutes).
- Bind signed URLs to the requesting user's session or IP where feasible.
- Use S3 bucket policies that deny requests without `x-amz-server-side-encryption` and `x-amz-security-token` headers.
- Enable S3 access logging and monitor for anomalous download patterns.

---

### T6: Cross-Tenant Data Access (Multi-Tenant Isolation Failure)

**What could go wrong:** A bug in the application server allows a user from Tenant A to access files belonging to Tenant B. This could happen if:
- File IDs are not scoped to tenant and are globally guessable.
- The tenant context is derived from the share link alone without verifying the generating user's tenant.
- S3 object keys do not include tenant identifiers, or the prefix scheme is bypassed.

**Impact:** Catastrophic data breach across all tenants; regulatory and legal liability.

**Mitigation:**
- Scope all file IDs and S3 object keys to tenant ID (e.g., `tenant-{id}/{file-id}`).
- Verify tenant context on every request, including share-link access.
- Use separate S3 prefixes or separate buckets per tenant.
- Implement automated tenant isolation tests in CI.
- Apply the principle of least privilege to S3 IAM policies (tenant-scoped policies).

---

### T7: Malicious File Upload (Server Compromise)

**What could go wrong:** An attacker uploads a file designed to exploit the application server or downstream consumers:
- A file with a malicious filename (e.g., path traversal: `../../etc/passwd`).
- A file with a deceptive extension (e.g., `document.pdf.exe`).
- A very large file that causes disk exhaustion (DoS).
- A file containing embedded scripts or malicious payloads that execute when previewed or downloaded.

**Impact:** Server compromise, data loss, malware distribution to recipients.

**Mitigation:**
- Sanitize and canonicalize filenames; reject path traversal characters.
- Validate file content by magic bytes / MIME type, not just extension.
- Store files with opaque names (UUIDs) mapped to original filenames in metadata.
- Enforce file size limits (e.g., 500 MB).
- Scan uploaded files with antivirus / malware scanning.
- Serve files with `Content-Disposition: attachment` and appropriate `Content-Type` headers.
- If file preview is offered, render in a sandboxed environment (e.g., headless browser with no network access, or convert to PDF/image).

---

### T8: Denial of Service via File Upload / Storage Exhaustion

**What could go wrong:** An attacker (or compromised account) uploads many large files or creates many share links, exhausting storage quota, API rate limits, or compute resources.

**Impact:** Service degradation or outage for all tenants.

**Mitigation:**
- Enforce per-user and per-tenant storage quotas.
- Rate-limit upload requests and share-link creation.
- Implement file type and size restrictions.
- Use cloud storage with auto-scaling and set budget alerts.
- Consider a quarantine / review period for new users before they can share files.

---

### T9: Insider Threat — Bulk Data Exfiltration

**What could go wrong:** A malicious tenant admin or power user generates share links for sensitive files and distributes them externally. Since the user has legitimate access, this is hard to detect.

**Impact:** Data exfiltration by authorized user; compliance violation.

**Mitigation:**
- Log all link creation, access, and download events with user identity, IP, timestamp, and file metadata.
- Provide admin dashboards showing file-sharing activity per user.
- Alert on anomalous patterns (e.g., one user sharing 100+ files, or sharing to many external domains).
- Support DLP (data loss prevention) scanning on uploaded files to detect PII, credentials, or sensitive content.
- Require admin approval for sharing files marked as sensitive.

---

### T10: Audit Log Tampering or Loss

**What could go wrong:** An attacker (insider or external) deletes or modifies audit logs to cover their tracks after accessing or exfiltrating files.

**Impact:** Inability to detect, investigate, or prove a breach; compliance failure.

**Mitigation:**
- Store audit logs in an append-only, tamper-evident store (e.g., WORM storage, signed log entries).
- Replicate logs to a separate account or region.
- Restrict log access to read-only for audit roles.
- Alert on log deletion or modification attempts.

---

### T11: Session / Account Takeover Leading to File Access

**What could go wrong:** An attacker compromises a user's account (via phishing, credential stuffing, or session hijacking) and gains access to all files the user can share or download.

**Impact:** Unauthorized access to all files accessible by the compromised account.

**Mitigation:**
- Enforce MFA for all users, especially admins.
- Implement credential stuffing protection (rate limiting, CAPTCHA, breach password checks).
- Use short-lived session tokens with refresh token rotation.
- Detect and alert on anomalous login locations / devices.

---

### T12: Share Link Forwarding / Unauthorized Redistribution

**What could go wrong:** A legitimate recipient forwards a share link to someone else. Since the link is a bearer token, the unauthorized recipient can download the file without any additional authentication.

**Impact:** Loss of control over who accesses the file; potential data leak.

**Mitigation:**
- Bind share links to recipient email (require email verification before download).
- Set download limits (e.g., link valid for 3 downloads).
- Require password for sensitive files.
- Provide link revocation so the original sharer can invalidate the link at any time.
- Log all downloads with IP address and user agent for traceability.

---

### T13: Referrer Header Leakage

**What could go wrong:** When a user clicks a share link from a web page, the full URL (including any tokens or identifiers) may be sent in the `Referer` header to third-party analytics or ad trackers embedded on the page.

**Impact:** Share link leaked to third parties; potential unauthorized access.

**Mitigation:**
- Set `Referrer-Policy: no-referrer` or `strict-origin-when-cross-origin` on the share-link landing page.
- Use a redirect endpoint that strips the token before forwarding to the actual download.
- Do not embed share link tokens in URL paths that could be logged; consider POST-based access where feasible.

---

### T14: Time-of-Check to Time-of-Use (TOCTOU) on Link Access

**What could go wrong:** An application checks authorization at link generation time but not at download time. A link that was valid when created may be accessed after the user's account is deactivated, the file is deleted, or the tenant is suspended.

**Impact:** Access to files after access should have been revoked.

**Mitigation:**
- Perform authorization check on every download request, not just at link creation.
- Check user account status, tenant status, and file existence on each access.
- Invalidate all links when a user account is deactivated or a tenant is suspended.

---

### T15: S3 Metadata / Object Key Leakage

**What could go wrong:** S3 object keys or metadata contain sensitive information (e.g., original filename, tenant ID, user email) that is visible to anyone with S3 read access. If S3 access is ever compromised, this metadata aids reconnaissance.

**Impact:** Information disclosure; aids targeted attacks.

**Mitigation:**
- Store sensitive metadata in the application database, not in S3 object metadata.
- Use opaque S3 object keys that do not reveal tenant or user information.
- Encrypt S3 objects with server-side encryption (SSE-KMS or SSE-S3).
- Use KMS keys with access policies scoped to the application role.

---

### T16: API Abuse — Unauthorized Link Creation at Scale

**What could go wrong:** The share-link creation API lacks proper authentication or authorization checks. An unauthenticated or low-privilege user can create share links for files they do not own or have access to.

**Impact:** Mass unauthorized file sharing; data breach.

**Mitigation:**
- Require authentication on all API endpoints.
- Verify that the requesting user owns the file or has explicit sharing permission.
- Rate-limit the share-link creation API.
- Log all link creation events.

---

### T17: Downloaded File Integrity / Tampering

**What could go wrong:** A file is replaced in S3 after the original user uploads it but before a recipient downloads it (e.g., via a compromised application server or S3 breach). The recipient receives a tampered file.

**Impact:** Data integrity violation; malware distribution.

**Mitigation:**
- Use S3 versioning to track file changes.
- Provide file checksums (SHA-256) at upload time and verify at download time.
- Use signed URLs that are generated per-request with short TTL.
- Log file modification events and alert on unexpected changes.

---

### T18: Cloud Provider / Supply Chain Compromise

**What could go wrong:** The cloud provider (e.g., AWS) or a third-party library used in the application is compromised, potentially exposing all stored files or enabling arbitrary code execution.

**Impact:** Mass data breach; system-wide compromise.

**Mitigation:**
- Encrypt all files at rest using customer-managed KMS keys (not provider-managed).
- Pin and verify dependencies (SBOM, signed packages).
- Implement network segmentation (VPC, security groups) to limit blast radius.
- Monitor cloud provider security advisories and patch promptly.
- Consider multi-cloud or cross-region replication for critical data.

---

### T19: Email Delivery / Link Distribution Channel Risk

**What could go wrong:** Share links are distributed via email. Email is inherently insecure:
- Emails may be stored unencrypted on mail servers.
- Emails may be forwarded or accessed by unauthorized parties.
- Email providers may scan content and log URLs.

**Impact:** Share link exposed through email channel.

**Mitigation:**
- Do not include the full share link in the email body; use a branded landing page that requires the recipient to verify their email before revealing the link or downloading.
- Use link tracking parameters that do not expose the actual share token.
- Consider in-app notifications (push, dashboard) as an alternative to email for link distribution.

---

### T20: Compliance and Data Residency Violations

**What could go wrong:** Files containing regulated data (PII, PHI, financial records) are shared without considering data residency requirements. S3 buckets in the wrong region or shared with recipients in restricted jurisdictions create compliance violations (GDPR, HIPAA, etc.).

**Impact:** Regulatory fines; legal liability; loss of customer trust.

**Mitigation:**
- Tag files with data classification labels at upload time.
- Enforce data residency rules based on tenant configuration.
- Restrict sharing of classified files to users within allowed jurisdictions.
- Provide compliance reporting (who accessed what, when, from where).
- Support data subject access requests (DSAR) and right-to-be-forgotten workflows.

---

## 5. Summary Risk Matrix

| Threat | Likelihood | Impact | Priority |
|---|---|---|---|
| T1: Link enumeration | Medium | High | High |
| T2: Link interception | Medium | High | High |
| T3: No expiry | High | Medium | High |
| T4: Password weaknesses | Medium | High | High |
| T5: S3 bypass | Low | Critical | High |
| T6: Cross-tenant access | Low | Critical | High |
| T7: Malicious upload | Medium | Critical | High |
| T8: DoS via upload | Medium | Medium | Medium |
| T9: Insider exfiltration | Medium | High | High |
| T10: Log tampering | Low | High | Medium |
| T11: Account takeover | Medium | High | High |
| T12: Link forwarding | High | Medium | Medium |
| T13: Referrer leakage | Medium | Medium | Medium |
| T14: TOCTOU | Low | High | Medium |
| T15: S3 metadata leak | Low | Medium | Medium |
| T16: API abuse | Low | High | High |
| T17: File tampering | Low | High | Medium |
| T18: Supply chain | Low | Critical | Medium |
| T19: Email channel risk | High | Medium | Medium |
| T20: Compliance violation | Medium | High | High |

---

## 6. Key Design Gaps in the Spec

The specification as stated is minimal and leaves several critical decisions undefined:

1. **Link identity format** is unspecified. Without cryptographic randomness, links are vulnerable to enumeration (T1).
2. **Default expiry policy** is not defined. The spec says "can optionally expire" but does not specify a system default, creating T3 risk.
3. **Password storage mechanism** is not specified. Without Argon2id/bcrypt, passwords are vulnerable to offline cracking (T4).
4. **S3 access architecture** is not specified. Direct public bucket access would bypass all application controls (T5).
5. **Multi-tenant isolation** is not addressed. In a B2B SaaS app, this is the highest-severity risk (T6).
6. **File validation** is not mentioned. Without content validation, malicious uploads are trivial (T7).
7. **Audit logging** is not mentioned. Without it, incidents are undetectable (T9, T10).
8. **Link revocation** is not mentioned. Without it, compromised links remain valid (T3, T12).
9. **Rate limiting** is not mentioned. Without it, the system is vulnerable to enumeration, brute-force, and DoS (T1, T4, T8).
10. **Data classification / compliance** is not addressed. B2B customers will require this for regulatory reasons (T20).