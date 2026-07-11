---
name: security-review
description: Security-review skill — structured pass over a diff or feature for vulnerabilities, keyed to what the code actually touches
metadata:
  type: user
---

# Security Review — Vulnerability Hunt Skill

## Why

Smaller models write plausible code that handles the happy path and trusts its inputs. Security bugs are exactly the cases nobody wrote down. This skill is a structured pass that asks "who can abuse this?" with checklists keyed to what the code touches — so the review is specific, not a generic OWASP recital.

Adversarial-review asks "where does it break"; this skill asks "who can abuse it" — run this for depth on any surface the Conditional Lanes flag.

## The Rule

**Any change touching input handling, auth, secrets, file/network access, or user data gets a security pass before it ships.** The pass reviews only the categories the change actually touches — depth over breadth. This skill fires per tierless-router's Conditional Lanes (auth, input handling, secrets, user data) — not by its own judgment of whether the change "feels" security-relevant.

## How to Apply

1. Read the diff and list what security surfaces it touches (see categories below).
2. For each touched surface, work the checklist against specific lines.
3. Write findings to `.claude/plans/{task-name}-security.md` with severity and fix-or-accept decision for each.

## Surface Checklists

### Input handling (any data crossing a trust boundary)
- Is every external input validated for type, length, range, and format — at the boundary, not deep inside?
- Parameterized queries only — grep the diff for string-built SQL/NoSQL/shell commands
- Path inputs: canonicalized and checked against an allowed root before file access?
- Deserialization of untrusted data (pickle, yaml.load, eval, Function()) — flag on sight

### Auth & authorization
- Is the check on the server, on every route/action — not just hidden in the UI?
- Object-level checks: can user A pass user B's id and reach their data (IDOR)?
- Session/token: expiry set, invalidated on logout/password change, not logged
- Any role check done client-side only is a finding, always

### Secrets & config
- No credentials, API keys, or tokens in code, config files in the repo, or log output
- Grep the diff for `key`, `secret`, `token`, `password` literals
- Error responses: do they leak stack traces, paths, versions, or query text to the client?

### Output & injection
- User content rendered into HTML escaped or sanitized (XSS)?
- Data flowing into shell commands, templates, or headers escaped for that context?
- Redirects and links built from user input validated against an allowlist?

### Dependencies & platform
- New dependency? Check it's maintained, check for known CVEs (`npm audit` / `pip-audit`)
- Pinned versions, lockfile committed

## The Report

```markdown
## Security Review: {change}
Surfaces touched: {list}

### Findings
1. {file:line} — {vuln} — severity {critical/high/medium/low}
   Exploit: {concrete steps an attacker would take}
   Fix: {specific change} | Accepted because: {reason}

### Verdict: SHIP / FIX FIRST / BLOCKED
```

Every finding needs a concrete exploit path. "This could be insecure" is not a finding; "POST /api/orders/{id} does not check ownership, so any logged-in user can read any order" is.

## Anti-Patterns

- Reciting OWASP top-10 categories that don't apply to the diff
- Findings without an exploit path or a line number
- Marking everything critical (severity inflation makes real criticals invisible)
- Reviewing only the new code — a diff can make *existing* code exploitable (e.g., exposing an internal function on a route)
- Treating "we're behind a VPN / it's internal" as a blanket accept
