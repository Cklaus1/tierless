# Threat Model: File-Sharing Feature (B2B SaaS)

## 1. System overview and assumptions

Feature under analysis: an authenticated user of a multi-tenant B2B SaaS app uploads a file; the
app stores it in S3; the app mints a shareable link; recipients — possibly with **no account** —
download the file via the link. Links may be **password-protected** and may **expire**.

Assumed architecture (typical; each assumption is itself a decision point with security
consequences, called out below):

- **Upload**: browser → app API (or browser → S3 via presigned PUT/POST issued by the app).
- **Storage**: private S3 bucket; per-file metadata (owner, tenant, filename, size, content type,
  token, password hash, expiry, download count) in the app database.
- **Download**: recipient hits `https://app.example.com/s/<token>`; app validates token, expiry,
  and password; then either streams the object through the app or 302-redirects to a short-lived
  presigned S3 GET URL (possibly fronted by a CDN).
- **Tenancy**: multiple customer organizations share the same app and bucket.

The single most important structural fact: **the share link is a bearer capability.** Anyone who
possesses the URL string has the access it grants. Every place that URL travels (email, chat,
logs, browser history, referer headers, corporate security scanners) is part of the attack
surface, and most of the design's threats flow from that.

---

## 2. Assets worth protecting

### Primary assets
1. **File contents.** B2B context means contracts, financials, PII/PHI, source code, M&A docs,
   credentials embedded in files. Confidentiality and integrity are both in scope. This is the
   crown jewel.
2. **Share link tokens.** Each token is a credential equivalent to the file it unlocks. Tokens at
   rest (DB), in transit, and in logs are all sensitive.
3. **Link passwords / password hashes.** Second factor for a link; also frequently *reused
   passwords* from users' other accounts — a breach of these harms users beyond this feature.
4. **File metadata.** Filenames alone leak deals ("AcmeCorp-acquisition-LOI.pdf"), org charts,
   customer names. Also sizes, timestamps, uploader identities, recipient emails, download logs.
5. **Uploader accounts and sessions.** Compromise = access to everything that user shared plus
   the ability to share new (malicious) content under a trusted identity.
6. **Tenant isolation.** Customer A's data must be invisible to Customer B — an isolation failure
   is an existential B2B incident even if no outsider is involved.

### Supporting / infrastructure assets
7. **S3 bucket and IAM credentials / presigned-URL signing capability.** Whoever can sign URLs or
   read the bucket bypasses every app-level control (password, expiry, revocation).
8. **Encryption keys** (SSE-KMS keys, any per-tenant keys, application secrets).
9. **The application database** (contains tokens, hashes, metadata, tenancy mapping) and its
   backups/replicas.
10. **Audit logs.** Needed to answer "who downloaded this and when" after an incident;
    simultaneously a leak vector if they capture tokens/passwords. Integrity and availability of
    logs are assets in their own right.
11. **Availability and cost.** Unauthenticated download endpoints + object storage egress = a
    direct line from anonymous attacker to your AWS bill and your bandwidth.
12. **Domain and sender reputation.** Your app domain will be embedded in emails worldwide. If
    the feature is abused to host malware/phishing, the domain gets blocklisted, breaking the
    feature (and possibly your marketing email, SSO redirects, etc.) for all customers.
13. **Compliance posture** (GDPR/CCPA erasure, data residency, SOC 2 controls, CSAM reporting
    obligations) and **customer trust/reputation** generally.

---

## 3. Realistic attackers

| # | Attacker | Capability / position | Motivation | Notes |
|---|---|---|---|---|
| A1 | **Anonymous internet attacker** | Can hit the unauthenticated download endpoint at scale; can guess/enumerate tokens, brute-force passwords, scrape leaked links from paste sites, Slack exports, search indexes | Data theft, opportunistic | The new unauthenticated surface is built *for* this population |
| A2 | **Unintended link holder** | Legitimately received or found the link: forwarded email, shared Slack channel, shoulder-surfed URL, browser history on a shared machine | Curiosity, insider trading, competitive intel | Not "hacking" — the capability model makes this the *most likely* real-world leak |
| A3 | **Intended recipient acting badly** | Has valid link + password | Re-shares beyond intended audience; keeps files after a deal collapses | Defense is limits + auditability, not prevention |
| A4 | **Malicious uploader** (rogue customer user, trial-account abuser, or attacker with a stolen customer account) | Full upload + share capability under a trusted tenant | Distribute malware/phishing from your trusted domain; use you as free hosting or C2/exfil infrastructure; host illegal content | You are the *platform*; the victim may be a third party who has never heard of you |
| A5 | **Cross-tenant attacker** | Authenticated user of Tenant B probing for Tenant A's data via IDOR, key-guessing, shared caches | Corporate espionage | Highest-severity class for a B2B product |
| A6 | **Malicious/compromised insider at the SaaS provider** | DB access, S3 console, admin tooling, log pipeline | Data theft, snooping on famous customers | Drives encryption, least-privilege, and admin-audit requirements |
| A7 | **Network attacker / MITM** | Coffee-shop Wi-Fi, hostile network, TLS-stripping middlebox | Steal links/passwords/files in transit | Largely solved by TLS done correctly — but only if done correctly |
| A8 | **Automated intermediaries** (not malicious, but adversarial to your assumptions) | Email security gateways that *fetch every URL*, chat-app link-unfurl bots, antivirus "link checkers", search crawlers | None — but they consume one-time links, burn download counts, defeat "the click proves the human recipient saw it" assumptions, and can index links | Frequently forgotten; breaks naive designs |
| A9 | **Cloud/infra attacker** | Exploits SSRF to reach instance metadata, finds leaked IAM keys on GitHub, finds a misconfigured bucket via public scanners | Mass data theft | Bucket misconfiguration scanners run continuously across the entire internet |
| A10 | **Ex-employee of a customer** | Old links saved locally; possibly old sessions | Grudge, competitive move | Motivates revocation, expiry-by-default, and link audit for tenant admins |

---

## 4. Trust boundaries

1. **TB1 — Internet ↔ unauthenticated download endpoint.** The headline new boundary: anonymous
   parties are *supposed* to get data out. Everything crossing it (token, password attempt, Range
   headers) is attacker-controlled.
2. **TB2 — Authenticated user ↔ upload/share-management API.** Users are authenticated but not
   trusted: file bytes, filenames, content types, share settings are all hostile input.
3. **TB3 — App ↔ S3.** Presigned URLs and IAM credentials cross here. A presigned URL handed to
   a browser moves S3 access *across TB1* — its constraints (TTL, method, key, headers) become
   the only remaining control.
4. **TB4 — App ↔ metadata DB** (and DB ↔ backups/replicas). Tokens and password hashes at rest.
5. **TB5 — Tenant ↔ tenant** inside the shared app, bucket, cache, and CDN.
6. **TB6 — Uploaded file content ↔ anything that parses it.** Virus scanners, thumbnailers,
   preview renderers, metadata extractors: hostile bytes crossing into native parsers.
7. **TB7 — Your origin ↔ the recipient's browser.** If user-supplied content is ever served
   *inline* from your domain, the uploader gets script execution in your web origin.
8. **TB8 — The link's delivery channel.** Email servers, chat platforms, security scanners,
   forwarding — a third-party-controlled zone the capability must survive transit through.
9. **TB9 — Provider staff ↔ customer data.** Admin consoles, support tooling, log pipelines.

---

## 5. Threat enumeration

Format per threat: **what could go wrong → mitigation**. Grouped by attack surface. STRIDE
category noted where useful (S=Spoofing, T=Tampering, R=Repudiation, I=Info disclosure,
D=DoS, E=Elevation of privilege).

### 5.1 The link/token itself (TB1, TB8)

**T1. Guessable or enumerable tokens (I).**
Sequential IDs, short tokens, or timestamps/UUIDv1 let A1 enumerate every shared file in the
system by iterating the URL space.
*Mitigation:* tokens of ≥128 bits from a CSPRNG (e.g., 22+ chars base62); no sequential
component; aggressive rate limiting + monitoring on 404s from the share endpoint (many misses
from one source = enumeration attempt); alert and block.

**T2. Token valid forever / no revocation (I).**
A leaked link (A2, A10) grants access indefinitely; the uploader has no kill switch after an
accidental "reply-all".
*Mitigation:* expiry **on by default** (e.g., 7–30 days, tenant-configurable, with a hard max
option for admins); explicit revoke button that takes effect immediately; tenant-admin console
listing all active links in the org with bulk revoke (offboarding an employee revokes their
links).

**T3. Link leakage through side channels (I).**
The URL lands in: browser history (shared machines), `Referer` headers if the download page loads
third-party resources or links out, web-server/CDN/proxy access logs, analytics tools, crash
reporters, corporate TLS-inspection middleboxes, and screenshots.
*Mitigation:* `Referrer-Policy: no-referrer` on all share pages; no third-party scripts/analytics
on the download page; scrub tokens from logs (log a hashed/truncated token for correlation);
serve over HTTPS with HSTS so middleboxes see less; keep the actual file GET on a separate
short-lived URL so history-resident links go stale.

**T4. Tokens stored in plaintext in the DB (I).**
A DB dump, backup leak, or read-only SQL injection instantly yields working download URLs for
every file in the system.
*Mitigation:* store only a hash (SHA-256 is fine — tokens are high-entropy) of the token; look up
by hash. Same for any "link secret" material. This converts DB disclosure from "all files
compromised" to "metadata compromised".

**T5. Automated intermediaries consume or index links (A8) (I/D).**
Email security gateways prefetch the URL: they may trip "max 1 download" limits, mark links as
viewed, or (worst) cache the file. Chat unfurlers can render a preview of the file (leaking
content into chat logs) or expose the filename. Crawlers index a link posted anywhere public.
*Mitigation:* the token GET returns an interstitial page, never file bytes — the actual download
requires an explicit user action (POST/JS click), so idempotent prefetches are harmless;
`X-Robots-Tag: noindex, nofollow` and `noindex` meta on share pages; no meaningful Open Graph
metadata (or generic OG data only) so unfurls don't leak filename/content; count downloads on the
file transfer, not the page view.

**T6. Deep forwarding / audience creep (A3) (I).**
The intended recipient forwards the link; the capability model cannot distinguish them from
anyone else.
*Mitigation (layered, since prevention is impossible):* passwords delivered out-of-band; optional
**email-verified access** (recipient enters their email, receives an OTP — link alone is
insufficient) for sensitive shares; download-count limits; per-download audit records (IP, UA,
timestamp) visible to the uploader; optional dynamic watermarking for documents; expiry keeps the
exposure window short.

**T7. Open redirect / token confusion on the share endpoint (S).**
If the download flow accepts a `redirect=`/`next=` parameter or reflects attacker input into a
redirect, the trusted share domain becomes a phishing laundering device.
*Mitigation:* no user-controllable redirect targets on unauthenticated endpoints; allowlist any
post-download navigation.

### 5.2 Password protection (TB1)

**T8. Online brute force of link passwords (S/I).**
The download endpoint is unauthenticated; A1 can hammer password attempts against a known token.
Users pick weak passwords ("acme2026").
*Mitigation:* strict per-token attempt throttling with exponential backoff **and** per-IP/ASN
rate limits; CAPTCHA/proof-of-work after a few failures; optionally notify the uploader on
repeated failures; encourage/generate strong passwords in the UI; constant response semantics
(see T10).

**T9. Attempt-lockout used as DoS against legitimate recipients (D).**
If T8's mitigation is "lock the link after 5 failures," A1 can lock any link they know exists,
denying the real recipient.
*Mitigation:* prefer throttling + CAPTCHA over hard lockout; if locking, lock per-source (IP,
fingerprint) rather than globally per link, or require uploader-side unlock; alert the uploader
rather than silently bricking the share.

**T10. Oracle behavior: distinguishing valid tokens / valid passwords (I).**
Different status codes, error text, or response timing for "token doesn't exist" vs "token exists
but wrong password" turns the endpoint into an enumeration oracle (feeds T1); non-constant-time
password comparison leaks byte-by-byte.
*Mitigation:* identical generic error page/status for invalid token, expired token, and wrong
password; constant-time comparison; compare against a hash so timing reflects hashing, not the
secret.

**T11. Password stored or logged in plaintext (I).**
Link passwords are frequently reused from users' other lives; a DB or log leak burns them.
*Mitigation:* hash with bcrypt/scrypt/Argon2 (these are human-chosen, low-entropy — a fast hash
is not enough); never log submitted passwords (including in request-body logging and APM); mask
in error reports.

**T12. Password check bypassable (E).**
Classic bugs: the check happens client-side; the check gates the HTML page but not the file URL;
the presigned S3 URL is fetchable without ever passing the check; the check is skipped for
`HEAD`/`Range` requests or an alternate API route to the same object.
*Mitigation:* server-side enforcement as the *only* gate to issuing S3 access; the presigned URL
must be minted only after token+password+expiry all validate, per request; audit all routes that
can reach an object (API, mobile, legacy) for the same gate; integration tests that assert the
raw object URL is not reachable.

**T13. Password transmitted in the URL or same channel as the link (I).**
`?password=x` puts the secret in history/logs/referers; sending link+password in the same email
adds zero security.
*Mitigation:* password submitted via POST body only; product UX nudges out-of-band delivery
("send the password by SMS/phone") and never auto-includes the password in the share email.

### 5.3 S3 storage and presigned URLs (TB3, and their export across TB1)

**T14. Bucket misconfiguration → public exposure (I).**
One `PublicRead` grant, one overly broad bucket policy, and A9's automated scanners find every
customer file within hours. This is the canonical cloud breach.
*Mitigation:* S3 **Block Public Access** at the account and bucket level; bucket policy denying
non-TLS and non-VPC/role principals; no static website hosting on the bucket; infrastructure as
code + policy-as-code (e.g., forbid public ACLs in CI); continuous config monitoring (AWS Config
/ Security Hub) with paging alerts.

**T15. Presigned URLs undermine app-level controls (E/I).**
A presigned GET is a *second* bearer capability with its own lifetime. If it lives hours, then
revocation, expiry, password checks, and download limits are all bypassable by anyone who saved
the presigned URL (it also lands in browser history and download-manager logs).
*Mitigation:* presigned TTL of seconds-to-a-few-minutes, minted fresh per authorized download;
never reuse across requests/users; `response-content-disposition=attachment` pinned in the
signature; accept the residual "valid for 60s after revocation" window explicitly, or proxy the
bytes through the app when hard revocation matters more than egress cost.

**T16. Predictable or user-controlled S3 object keys (I/T).**
If keys are `tenant/{filename}` or sequential, anyone who obtains bucket-level read (or a signing
bug) can traverse; user-controlled filenames in keys invite `../`-style and delimiter tricks and
cross-tenant collisions/overwrites.
*Mitigation:* server-generated random UUID keys, mapping kept in the DB; original filename stored
as metadata only; per-tenant key prefix *plus* DB-side tenancy check (defense in depth, never
prefix alone).

**T17. Overly broad IAM for the signing principal (E).**
The credential that signs URLs can, if scoped `s3:*` on `*`, be leveraged (via any signing bug or
SSRF) to read/delete/overwrite everything, including other services' buckets.
*Mitigation:* dedicated IAM role, least privilege: `GetObject` (and `PutObject` if doing direct
uploads) on this bucket's prefix only; no `ListBucket` for the web-facing role; no long-lived
access keys — instance roles/IRSA; **IMDSv2 enforced** so SSRF can't mint credentials.

**T18. Direct-to-S3 upload (presigned PUT/POST) abuse (T/D).**
If the app presigns uploads without constraints, the uploader controls size (cost bomb),
content-type (later served as `text/html` → XSS, see T24), and possibly the key (overwrite
another file).
*Mitigation:* presigned **POST with policy conditions**: exact server-chosen key,
`content-length-range`, pinned content type; treat the upload as untrusted until the app
verifies the object (size, magic bytes) and flips it to "available"; garbage-collect orphaned
uploads.

**T19. Encryption and key management gaps (I).**
Unencrypted at rest → any storage-layer exposure (misconfig, AWS-side issue, backup theft) is a
full breach; single shared key → insider (A6) with KMS access reads all tenants.
*Mitigation:* SSE-KMS with a customer-managed key as baseline; KMS key policy restricting decrypt
to the app role; for high-tier tenants, per-tenant KMS keys (blast-radius reduction + credible
crypto-shredding for offboarding); TLS enforced to S3 via bucket policy.

**T20. "Deleted" or "expired" isn't (I / compliance).**
Expiry only hides the link while bytes persist; S3 versioning, replicas, and backups retain
"deleted" files; GDPR erasure requests can't be honored.
*Mitigation:* define deletion semantics: link expiry (metadata) vs file deletion (object + all
versions + eventual backup aging); S3 lifecycle rules aligned with retention policy; a deletion
pipeline that provably covers versions/replicas; document backup-expiry windows for DPAs;
per-tenant keys make crypto-shredding possible.

### 5.4 Upload path — hostile content (TB2, TB6)

**T21. Malware distribution from your trusted domain (A4) (platform abuse).**
Attackers love file-sharing features: `https://app.example.com/s/x` sails past email filters that
would block `evil.ru`. Your feature becomes the delivery stage of other people's intrusions;
your domain gets blocklisted (asset #12), breaking the feature for everyone.
*Mitigation:* AV/malware scanning on upload (and rescan on download or periodically — signatures
lag); block/flag executable and script types by policy (tenant-configurable); interstitial
download page with filename, size, uploader org, and "only download if you expected this"
warning; `Content-Disposition: attachment` always; abuse-report link on every share page; rate
limits and anomaly detection on new/trial accounts (the classic abuse cohort); a takedown
runbook and registered abuse contact.

**T22. Phishing-page hosting (A4) (S).**
An uploaded `login.html` rendered inline from your origin is a credential-harvesting page hosted
on a domain the victim's browser and email filter both trust — and it runs in your web origin
(see T24).
*Mitigation:* never render user content inline from the app origin. `Content-Disposition:
attachment` unconditionally on the app domain; if inline preview is a product requirement, serve
previews only from an **isolated sandbox domain** (`*.usercontent-example.com` — a separate
registrable domain, not a subdomain of the app) with `Content-Security-Policy: sandbox`, no
cookies, no auth.

**T23. Malicious files attacking your own processing pipeline (E/D).**
Thumbnailers, preview converters, AV engines, and metadata extractors parse hostile bytes:
image-parser RCEs (ImageTragick-class), XML XXE in office docs, zip/decompression bombs, PDFs
with embedded JS, TIFFs that OOM the worker.
*Mitigation:* process files in sandboxed, unprivileged, network-egress-restricted workers
(separate container/microVM, seccomp, no IAM beyond the one object); strict CPU/memory/time/
output-size limits; disable external entity resolution and URL fetching in every parser; cap
decompression ratios; don't parse formats you don't need to.

**T24. Content-type / filename injection → stored XSS and header injection (T/E).**
Attacker-controlled inputs: file bytes, declared MIME type, filename. Failure modes: serving
attacker bytes as `text/html` or `image/svg+xml` inline (script in your origin — session theft
for logged-in users who view a share); browsers MIME-sniffing a "text/plain" file into HTML;
filename with CRLF or quotes injected into the `Content-Disposition` header; filename with
`<script>` rendered unescaped in the share page or in notification emails.
*Mitigation:* ignore client-declared content type — detect server-side and allowlist what may
ever be served inline (basically raster images, and even those preferably re-encoded);
`X-Content-Type-Options: nosniff` everywhere; RFC 5987/6266-encode filenames in headers, strip
CR/LF and control chars; context-escape filenames in HTML and email templates; treat SVG as
attachment-only (it's a script container).

**T25. Storage exhaustion / cost abuse via upload (D).**
Unbounded sizes or counts: a trial account uploads 10 TB, or the feature becomes a free piracy
CDN (cost + DMCA exposure).
*Mitigation:* per-file size limits, per-user and per-tenant quotas; upload rate limits; billing
anomaly alarms; egress/download quotas (see T29); ToS + enforcement tooling for piracy/free-
hosting abuse.

**T26. CSRF / clickjacking on upload and share management (T/E).**
A logged-in user visits a hostile page that silently creates a public share of an existing file,
or reconfigures a link (removes password, extends expiry).
*Mitigation:* CSRF tokens or same-site strict cookies on all state-changing routes;
`X-Frame-Options: DENY` / CSP `frame-ancestors` on the app; re-prompt/confirm for share-security
downgrades.

**T27. Your service as exfiltration / C2 infrastructure (A4) (abuse).**
Malware inside a victim org uploads stolen data to your app (allowed by the victim's egress
proxy, because you're a legitimate SaaS vendor) and the operator downloads it via share links.
*Mitigation:* API rate limiting and volume anomaly detection per account; tenant-admin visibility
into upload/share activity; support tenant-level policies (disable external sharing, domain
allowlists for recipients); cooperate with abuse reports quickly.

### 5.5 Download path (TB1, TB7)

**T28. Authorization bugs on the object fetch (E/I).**
Beyond T12: IDOR on any parallel endpoint (`/api/files/1234/download` checking login but not
tenancy); expiry checked in the UI but not the API; `HEAD` or `Range` requests short-circuiting
checks; CDN caching an authorized response and replaying it to unauthorized requesters.
*Mitigation:* one canonical, centralized authorization function (token valid ∧ not expired ∧ not
revoked ∧ password satisfied ∧ within download limits) enforced on **every** route to bytes;
`Cache-Control: private, no-store` on authorized responses; CDN configured to never cache the
authorization step or the redirect; expiry evaluated at request time server-side (not cron-based
cleanup alone, which leaves a live window); tests for HEAD/Range/conditional-request paths.

**T29. Bandwidth/DoS and cost amplification (D).**
The endpoint is unauthenticated by design. A1 downloads a 5 GB file in a loop: egress bills,
saturated app workers (if proxying), or denial of service for real users. Also
request-flood DoS on the token-lookup path (DB hammering).
*Mitigation:* CDN in front of downloads; per-IP and per-token download rate/volume caps;
optional per-link download-count limits; egress budget alarms; token lookups served from an
index/cache so floods don't take down the primary DB; standard WAF/DDoS protections
(the endpoint should tolerate being on the internet's scan lists, because it will be).

**T30. Revocation/expiry race windows (I).**
Uploader revokes at 12:00:00; a presigned URL minted at 11:59:50 works until 12:04:50. Or expiry
enforced by a nightly job leaves links live for hours past expiry.
*Mitigation:* evaluate expiry/revocation on every request against the DB (cheap); keep presigned
TTL short (T15) and document the residual window; for "must be instantly revocable" tiers, proxy
downloads through the app so revocation is immediate.

**T31. Metadata disclosure before authorization (I).**
The password-entry page shows the filename, size, uploader name, and company logo *before* the
password is entered — an attacker with only the token learns "Acme is sharing
`layoffs-plan-q3.xlsx` (2.1 MB) with someone."
*Mitigation:* decide deliberately what is shown pre-auth; default to minimal (generic "a file has
been shared with you"); make filename-before-password a per-link/tenant option, not the default.

**T32. No recipient identity → no meaningful audit or repudiation control (S/R).**
"Downloaded by 84.12.x.x" doesn't tell the uploader whether the *right person* got the file; a
recipient can deny receipt; a leaker can't be identified among five recipients.
*Mitigation:* optional identified-recipient mode (email OTP per T6) producing per-identity audit
entries; per-recipient distinct links (so the leaked copy identifies which recipient's link
leaked); watermarking for documents; signed/tamper-evident audit log (also serves R for the
uploader side: record who created/modified/revoked each share).

**T33. TLS/transport failures (I/T, A7).**
Plain-HTTP fetch of the link, or a downgrade, exposes token, password, and file bytes; a MITM
could also *swap the file content* (integrity!) — recipient downloads a trojaned contract.
*Mitigation:* HTTPS only; HSTS with preload on the share domain; HTTP→HTTPS redirects that never
serve content; TLS enforced app↔S3 as well (bucket policy `aws:SecureTransport`); optionally
surface a file checksum to recipients for high-assurance flows.

**T34. Subdomain/CDN takeover of the download or usercontent domain (S/T).**
A dangling CNAME for `files.example.com` or a misclaimed CDN distribution lets an attacker serve
arbitrary content on a domain your customers are trained to trust — every historical link becomes
a phishing vector.
*Mitigation:* DNS hygiene and inventory; remove records before deprovisioning targets; monitor
for takeover-able records; certificate transparency monitoring.

### 5.6 Application, tenancy, and platform (TB2, TB4, TB5, TB9)

**T35. Cross-tenant access via IDOR / missing tenancy checks (E/I, A5).**
`GET /api/files/8891` checks "is logged in" but not "belongs to this tenant"; or search,
share-listing, or admin endpoints leak other tenants' metadata; or a shared cache key collides
across tenants.
*Mitigation:* tenancy scoping enforced in the data layer (every query carries tenant_id;
row-level security where available), not ad hoc per endpoint; non-sequential resource IDs
(reduce guessability — but never as the control); tenant-aware cache keys; automated cross-tenant
authorization tests in CI; pen-test focus here.

**T36. Uploader account takeover (S, A4-enabler).**
Credential stuffing or phishing against a customer user yields their whole file library plus the
ability to send malicious "shares" from a trusted colleague identity.
*Mitigation:* MFA support (and tenant-enforced MFA), SSO/SAML for B2B tenants; session hygiene
(rotation, absolute timeouts); notification to the user on new share links created; anomaly
detection (mass link creation, mass downloads by the account).

**T37. Injection via the metadata path (T/E).**
Filename/description fields hitting SQL (injection), the share email template (content
injection / spoofed instructions to the recipient: "new bank details attached"), or internal
admin tools (XSS against your own staff — pivots A4 into A6).
*Mitigation:* parameterized queries; output encoding in every sink including internal admin UIs
and email templates; treat all file metadata as hostile everywhere it is displayed.

**T38. Insider access at the provider (I, A6).**
Support engineers can read any tenant's files via the S3 console or a "debug download" tool; the
log pipeline team can see tokens.
*Mitigation:* no standing human access to the bucket or KMS decrypt; break-glass with approval +
alerting + audit; admin tools operate on metadata, not content, by default; token hashing (T4)
keeps logs/DB from being a skeleton key; per-tenant keys (T19) narrow any single access grant.

**T39. Secrets/token leakage through logging, monitoring, backups (I).**
Access logs capture full URLs (tokens); APM captures request bodies (passwords); DB backups
replicate tokens/hashes to less-protected storage.
*Mitigation:* log-scrubbing rules for the share-path URL patterns and password fields; encrypt
backups with separate keys and equivalent access control; retention limits on raw access logs;
periodic secret-scanning over log samples as a control test.

**T40. SSRF via any URL-fetching feature (E, A9).**
"Import file from URL" or webhook/preview fetchers let attackers hit `169.254.169.254`, internal
admin services, or the VPC.
*Mitigation:* if the feature exists: egress through a proxy that blocks private/link-local
ranges, resolves-then-pins DNS, restricts schemes/ports; IMDSv2; better, keep the fetcher in an
isolated network segment with no IAM role.

**T41. Illegal content hosting: CSAM, terrorist content, copyright (legal/abuse).**
As a host of third-party-uploaded content available via public links, you inherit statutory
obligations (e.g., NCMEC reporting in the US, DSA in the EU, DMCA process).
*Mitigation:* abuse reporting channel; hash-matching (e.g., PhotoDNA-class) where feasible and
lawful; documented takedown + preservation + reporting runbook; counsel review of obligations in
operating jurisdictions; ToS coverage.

**T42. Compliance and data-lifecycle failures (I / legal).**
Files containing EU personal data replicated to a US bucket against the DPA; erasure requests
unfulfillable (T20); indefinite retention of files everyone forgot.
*Mitigation:* data-residency-aware bucket selection per tenant if contractually promised;
default retention limits; tenant-admin controls for retention/expiry policy; map this feature
into GDPR/SOC 2 evidence (access logging, encryption, deletion) from day one.

---

## 6. Cross-cutting security requirements (the design's spine)

1. **Single authorization chokepoint** for byte access: token(hashed lookup) ∧ unexpired ∧
   unrevoked ∧ password(Argon2, throttled) ∧ within limits → then mint a ≤60s single-use-intent
   presigned URL with pinned `attachment` disposition — every download route goes through it.
2. **Treat tokens as credentials end-to-end:** 128+ bits CSPRNG, stored hashed, scrubbed from
   logs, never in referers, revocable, expiring by default.
3. **Never serve user bytes inline from the app origin.** Attachment-only on the app domain;
   previews only from an isolated separate registrable domain, cookieless, CSP-sandboxed.
4. **S3 as a sealed box:** Block Public Access, least-privilege role, random server-chosen keys,
   SSE-KMS, TLS-only policy, constrained presigned POST for uploads, config drift monitoring.
5. **Assume abuse from day one:** malware scanning, interstitials, rate limits everywhere on the
   unauthenticated surface, abuse reporting + takedown runbook, new-account friction.
6. **Tenancy enforced in the data layer**, verified by automated cross-tenant tests.
7. **Auditability:** tamper-evident records of create/modify/revoke/download (with as much
   recipient identity as the chosen mode provides), retained per policy, and exposed to tenant
   admins.
8. **Deliberate residual-risk statements:** presigned-URL revocation window; capability links are
   forwardable; email scanners will fetch every link; backups outlive deletion for N days. Write
   these down — they are product decisions, not bugs.

## 7. Top risks (ranked)

1. **T14 bucket misconfiguration** — single config error, total breach, actively scanned for.
2. **T35 cross-tenant IDOR** — existential for B2B trust; common bug class.
3. **T1/T8 unauthenticated brute force** (token enumeration + password guessing) — the new
   endpoint invites it; cheap to attack, cheap to defend if designed in now.
4. **T21/T22 platform abuse** (malware/phishing from your domain) — highest *likelihood* threat;
   damages all customers via domain reputation.
5. **T12/T15/T28 authorization bypass around the password/expiry gate and presigned URLs** —
   subtle, and it silently nullifies every advertised control.
6. **T2/T6 leaked/forwarded links with no expiry or revocation** — the most probable real-world
   data-leak path, driven by users, mitigated by defaults.
