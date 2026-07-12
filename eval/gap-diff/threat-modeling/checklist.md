# GRADER checklist — threat-modeling (13 threats a thorough model enumerates)

1 predictable/guessable link IDs (enumeration of others' files): r"predictable|guessable|enumerat|sequential id|brute.?force.*(link|url|id)|unguessable|random.*(token|id)"
2 link leakage (referrer, logs, chat, shared): r"leak|referrer|shared.*(link|url)|forwarded|logs?.*(url|link|token)|url in (history|logs)"
3 no expiry enforcement / expiry bypass: r"expir|ttl|time.?limit|link.*(never|forever|permanent)|expiry.*(bypass|enforc)"
4 password brute-force (no rate limit on password links): r"brute.?force.*password|rate.?limit|password.*(guess|attempt)|no.*(throttle|lockout)"
5 malware/malicious file upload (no scanning): r"malware|virus|malicious (file|upload|content)|scan|antivirus|dangerous file"
6 stored XSS / content-type (HTML file served inline): r"xss|content.?type|content-disposition|inline|html.*(upload|served|render)|mime|served as html"
7 direct S3 access / bucket misconfig / signed URL leakage: r"s3.*(public|misconfig|acl|bucket|direct)|signed url|presigned|object storage.*(access|permission)|bucket policy"
8 authz: uploader can't be verified as owner / cross-tenant file access: r"authoriz|ownership|cross.?tenant|access other|IDOR|tenant isolation|only.*(owner|their)"
9 unbounded upload size / storage exhaustion / DoS: r"size limit|unbounded|storage exhaust|dos|denial of service|large file|quota|upload.*(limit|abuse)"
10 data retention / deletion (file lingers after link expires/deleted): r"retention|deletion|lingers|orphan|still (accessible|stored)|delete.*(actual|storage|s3)|scrub"
11 PII / data exfiltration via sharing (insider or compromised account): r"exfiltrat|insider|data (leak|loss|theft)|sensitive|PII|compromised account|leak.*(data|file)"
12 no audit log of downloads / who accessed: r"audit|access log|download log|who (downloaded|accessed)|logging.*(access|download)|traceab"
13 password sent/stored insecurely / link+password in same channel: r"password.*(plain|hash|storage|same channel|with the link)|store.*password|hash.*password"

## Scoring: each present = 1, /13. Classic enumeration task (STRIDE-style). Does the model
## systematically walk the surfaces or list the obvious 4-5.
