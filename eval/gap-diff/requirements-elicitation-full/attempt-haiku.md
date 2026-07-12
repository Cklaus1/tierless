# Requirements Elicitation: "Export My Data" Button

## 1. Immediate Questions to Ask the PM

### Scope and Intent
- **What does "everything" mean?** Does this mean all data the user has ever created, all data the system holds about the user (including logs, preferences, third-party integrations), or something narrower?
- **Is this a legal compliance requirement or a product feature?** The phrase "Legal wants it" strongly suggests a regulatory driver (GDPR Article 20 data portability, CCPA/CPRA right to access, LGPD, etc.). If so, the requirements are far more prescriptive than a casual "download button."
- **Which regulations apply?** GDPR (EU users), CCPA/CPRA (California), LGPD (Brazil), PIPEDA (Canada), and other jurisdictions each have different requirements for format, delivery timeline, scope, and verification.
- **Is there a companion "delete my data" (right to erasure) request coming?** These two rights are typically paired. If Legal is thinking about data export now, they are likely thinking about erasure next.

### User and Format
- **What format does Legal expect?** GDPR Article 20 specifically requires a "commonly used, machine-readable format." Does Legal have a preference (JSON, CSV, XML, ZIP of files)?
- **Should the export be immediate (button click) or asynchronous (email notification when ready)?** For large datasets, a synchronous download will time out or hang.
- **Should users be able to choose what to export?** Partial export (only their posts, only their uploaded files, a date range) or full dump?

### Security and Verification
- **How do we verify the requester is the legitimate account owner?** Any export flow must include identity verification to prevent unauthorized data disclosure. What is the current auth model?
- **Should the exported file be encrypted or password-protected?** Best practice for data portability exports is to protect the file in transit and at rest.
- **Is there a rate limit or frequency cap?** Should a user be able to export once per day? Once per month?

---

## 2. Regulatory and Legal Considerations (Assuming GDPR/CCPA)

### GDPR Article 20 — Right to Data Portability
- The user has the right to receive their personal data in a **structured, commonly used, machine-readable format**.
- The user has the right to have that data **transmitted directly to another controller** where technically feasible. This is not just a download button; it may require an API or direct transfer mechanism.
- The right applies only to data the user **provided** (not inferred/derived data like analytics scores or ML predictions). This distinction matters for what we include.
- The right does not adversely affect the rights of others. If the user's data contains other people's personal data (e.g., messages they received, comments on their posts), those must be redacted or handled separately.

### GDPR Article 15 — Right of Access
- Broader than portability. The user can request any personal data we process about them. This may include data not covered by Article 20 (e.g., login history, IP addresses, device info, communication logs).

### CCPA/CPRA — Right to Access and Know
- Requires disclosure of categories of personal information collected, sources, purposes, and specific pieces of information.
- Must be provided in a **portable and readily usable format**.
- For-profit businesses with over $25M annual gross revenue, or that buy/sell/share personal information of 100K+ consumers, are subject to these requirements.
- CCPA requires a "Do Not Sell or Share My Personal Information" link on the website.

### Other Jurisdictions
- **LGPD (Brazil)**: Similar to GDPR, requires data portability upon request.
- **PIPEDA (Canada)**: Requires access to personal information upon request.
- **HIPAA (US, if health data)**: If the product handles health information, HIPAA Subpart E grants patients the right to access and amend their records, with specific format and timeline requirements (30 days).
- **Sector-specific laws**: Financial data (GLBA), education (FERPA), etc.

### Delivery Timeline
- **GDPR**: Response within **one month** (extendable by two months for complex requests).
- **CCPA**: Response within **45 days** (with extension possibility).
- These are legal deadlines. The "button" must trigger a process that can meet these SLAs.

---

## 3. Technical Architecture Considerations

### Data Inventory — What Actually Exists?
Before building anything, we need a complete data map:
- **User-provided data**: Profile info, content created (posts, messages, uploads), preferences.
- **Derived data**: Analytics, scoring, ML model outputs, tags, recommendations.
- **System-generated data**: Login logs, IP addresses, device fingerprints, session data, error logs.
- **Third-party data**: Data ingested from connected accounts (Google, Facebook, etc.).
- **Data held about the user by others**: Messages received, comments, shares — data that references the user but was created by other users.

### Export Mechanism Options
1. **Synchronous download**: User clicks button, server generates file, browser downloads. Simple but fails for large datasets. Risk of timeout, memory exhaustion, or server overload.
2. **Asynchronous export with notification**: User requests export, system queues the job, sends email when ready, user downloads from a secure link with expiration. More robust, better UX for large data.
3. **Direct transfer to third party**: GDPR Article 20 requires this "where technically feasible." Could be a secure API endpoint the user gives to another service, or a shareable link.

### Data Aggregation Complexity
- **Multi-tenant data**: If users share data (messages, comments, collaborative documents), we must separate the requesting user's data from other users' data.
- **Cross-account data**: If a user has linked accounts (Google, Facebook, GitHub), do we export data from all of them?
- **Deleted data**: Do we include data the user previously deleted? GDPR says yes for personal data we still process.
- **Backups and archives**: GDPR and CCPA both have nuances around backup data. Some jurisdictions require inclusion; others allow deferral until backup rotation.

### File Format and Structure
- **Machine-readable**: JSON or CSV are the standard expectations.
- **Structured**: Should include metadata (timestamps, data sources, data categories).
- **Nested data**: How do we represent relational data (e.g., a user's posts with comments) in a flat format?
- **File size**: A single JSON file for a power user could be gigabytes. Should we split into multiple files by category?

### Storage and Retention of Exports
- **Where is the export file stored temporarily?** It must be on a secure, access-controlled path.
- **How long does the export remain available?** Should expire after a short window (e.g., 24-72 hours).
- **Who can access the export link?** Should require re-authentication.
- **Audit trail**: Every export request must be logged (who, when, what data scope, delivery method) for compliance purposes.

---

## 4. Security and Privacy Considerations

### Authentication and Authorization
- **Re-authentication required**: Before initiating an export, the user must re-enter their password or complete MFA. This prevents session hijacking from triggering exports.
- **No export for suspended/deleted accounts**: Or handle gracefully (e.g., allow export within 30 days of account deletion).
- **Admin access**: Can an admin trigger an export on behalf of a user? If so, what audit requirements apply?

### Data Leakage Prevention
- **PII redaction**: If the export contains other people's data, it must be redacted.
- **API keys and tokens**: Should NOT be included in exports (or must be masked).
- **Sensitive data flags**: Some data may be classified as sensitive (health, financial, identity documents) and require special handling.

### Threat Model
- **Mass export attack**: Could an attacker script export requests to exhaust server resources? Rate limiting is essential.
- **Data exfiltration by compromised account**: If an account is compromised, the attacker can export all data. This is a feature, not a bug — but it means account compromise has severe consequences. Consider additional verification for large exports.
- **Export link interception**: If the download link is shared, anyone with the link can download. Use short-lived, single-use tokens.

---

## 5. Product and UX Considerations

### User Experience
- **Where does the button live?** Settings page? Privacy section? Account management?
- **What does the user see while it's processing?** If asynchronous, a clear status page with progress indicator.
- **What format options do we offer?** Default to the most useful format (likely JSON), but offer CSV for tabular data.
- **Can users select subsets?** A power user may only want their photos, not their login history.

### Communication
- **Privacy policy update**: The privacy policy must describe the export process, what data is included, and how to request it.
- **In-product messaging**: Users should understand what they are getting before they click. A tooltip or modal explaining the scope.
- **Email notification**: If asynchronous, the email should clearly state what data is included and that the link expires.

### Accessibility
- The export feature must be accessible to all users, including those using screen readers or assistive technologies.
- Consider users in jurisdictions with limited bandwidth — large exports over slow connections need to be manageable.

---

## 6. Operational and Business Considerations

### Cost and Infrastructure
- **Storage costs**: Storing export files temporarily, especially for large datasets, has infrastructure costs.
- **Compute costs**: Generating exports for thousands of users simultaneously could spike compute costs.
- **Bandwidth costs**: Large file downloads consume significant egress bandwidth.
- **Scalability**: If 10,000 users request exports in a week (e.g., after a data breach announcement), can the system handle it?

### Compliance and Audit
- **Record keeping**: Every export request must be logged with timestamp, user ID, data scope, delivery method, and completion status.
- **Regulatory reporting**: Legal may need to report export requests to regulators.
- **Data retention policy for exports**: How long are export logs retained? How are they secured?

### Edge Cases
- **What if the user's data is spread across multiple services/microservices?** Aggregating requires coordination across teams.
- **What if the user has data in multiple regions?** GDPR requires data to stay in certain jurisdictions. An export may need to respect data residency.
- **What about data in legacy formats or deprecated schemas?** The export system must be able to read and translate old data formats.
- **What if the user's account is part of an organization?** Enterprise accounts may have different export policies (admin approval required, data stays within org).

---

## 7. What I Would Flag to Legal Directly

1. **"Just a button" is not sufficient.** GDPR Article 20 requires a machine-readable format and potentially direct transfer to another controller. A simple download button may not meet the full requirement.
2. **We need a formal data subject request (DSR) process.** Not every export request should go through the same UI. Some may come via email, legal channels, or third-party DSR platforms. The backend process should be the same regardless of entry point.
3. **We need to define what "personal data" means in our context.** A data inventory exercise is required before we can confidently say what gets exported.
4. **We need to handle the "rights of others" problem.** If User A's data contains messages from User B, we cannot simply export all of it. We need a redaction or separation strategy.
5. **We need a timeline.** Legal says "this quarter" but GDPR gives us one month to respond to individual requests. The system must be built and tested well before the first real request arrives.
6. **We should anticipate the erasure request.** If we are building the export infrastructure, we should design it so the erasure flow is parallelizable, not dependent on completing the export flow first.

---

## 8. Proposed Next Steps

1. **Schedule a meeting with Legal** to clarify which regulations apply, what format they expect, and whether there is a formal DSR process already in place.
2. **Conduct a data inventory** to catalog all data points held about users, their sources, storage locations, and retention policies.
3. **Define the MVP scope**: Start with a synchronous JSON export of user-provided data for a single data source. Then iterate to cover derived data, multi-source aggregation, and alternative formats.
4. **Design the async export pipeline**: Queue system, file generation, secure storage, expiration, and notification.
5. **Build the audit logging infrastructure** before the first export request.
6. **Create a test plan** that validates: correct data inclusion/exclusion, format compliance, security (re-auth, rate limiting), performance (large datasets), and edge cases (empty accounts, deleted data, cross-user data).