---
name: infra-ops
description: Infra-ops skill — discipline for servers, deployment, CI/CD, and IT operations: everything as code, changes staged and reversible, observability before features
metadata:
  type: user
---

# Infra Ops — Infrastructure & IT Skill

## Why

Infrastructure is where "it works" and "it keeps working" diverge. Smaller models configure servers the demo way: SSH in, fix it live, move on — leaving snowflake machines nobody can rebuild, deploys nobody can roll back, and outages nobody saw coming because nothing was measured. This skill is the operations discipline: every change is code, every deploy is reversible, and the system tells you it's sick before users do.

## The Rule

**If it isn't in version control, it doesn't exist. Manual changes to live systems are incidents waiting for a postmortem — every server, config, and deployment must be reproducible from the repo.**

## How to Apply

### 1. Everything as code

- Infrastructure (Terraform/Pulumi/CloudFormation), configuration (Ansible/cloud-init/Dockerfiles), and pipelines (CI config in-repo) — all versioned, all reviewed as diffs
- The rebuild test: could you recreate this server from the repo in an hour? If no, it's a snowflake — schedule its capture
- Secrets in a secret manager, never in the repo, never in CI logs; rotation is a documented procedure that has been *executed*, not just written

### 2. Changes are staged and reversible

- Same artifact promoted dev → staging → prod; staging is prod-shaped (same versions, same topology, scaled down) or it's theater
- Every deploy has a rollback that takes minutes and has been *tested*: previous artifact kept warm, migrations backward-compatible for one release (see data-migration)
- Risky changes ship behind flags or as canaries: small slice of traffic, watch the metrics, then promote — the metric watched is decided *before* the deploy
- No Friday-afternoon deploys of anything you can't roll back in your sleep

### 3. Observability before it's needed

The SRE knowledge (four golden signals, symptom-based alerting, structured logs) is knowledge you have — apply it. The process hooks that get skipped:
- The canary metric is decided *before* the deploy, in writing — not chosen from whatever dashboard looks green afterward
- Runbook per alert, written when the alert is created, not during the incident
- Every alert is actionable or it gets deleted

### 4. Capacity and hygiene are scheduled, not reactive

- Disk-full, cert-expiry, quota, and domain/renewal alarms at 80%, weeks ahead — these outages are the most preventable and the most embarrassing
- Patching cadence decided and automated; unpatched-forever boxes are the security-review skill's problem too
- Backup restores rehearsed on a calendar (the backup that's never been restored is a hope)
- Access reviewed: who can touch prod, offboarding actually revokes, break-glass procedure exists and is logged

### 5. When it breaks

Route through **incident-response** (mitigate → diagnose → fix). Infra-specific addendum: the fix is only done when it's *in the repo* — a live hotfix that isn't captured in code will be silently reverted by the next deploy, and that's incident number two.

## Anti-Patterns

- Marking rollback "tested" because it worked in dev once — the rollback that matters runs against prod-shaped state, recently
- Capturing the hotfix in a ticket instead of the repo — the ticket doesn't stop the next deploy from reverting it
- Staging that differs from prod in the exact dimension that breaks (different DB version, no TLS, one instance)
- Deploys that can't roll back because the migration already ran (expand/contract exists for this)
- Alerting on every metric that can be measured (100 alerts = 0 alerts)
- Backups that have never been restored; DR plans that have never been exercised
- The one server everyone is afraid of, that nobody can rebuild, that everything depends on
- CI that's green while prod is broken — the pipeline tests what's easy, not what matters

## Verification

Pre-deploy checklist — every line answered in the verify artifact before the deploy:
- [ ] Rollback path named and tested — *when* was it last tested?
- [ ] Canary metric named, before the deploy
- [ ] Staging parity confirmed (same versions, same topology)
- [ ] The change is in the repo — no live-only state

Verdict is PASS/FAIL; "rollback exists" without a test date is a FAIL.
