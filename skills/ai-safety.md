---
name: ai-safety
description: AI-safety skill — discipline for agentic and high-capability AI systems: least privilege, containment before capability, and evals for the failure you can't undo
metadata:
  type: user
---

# AI Safety — Agentic Systems Skill

## Why

The moment an AI system gets tools — file access, code execution, API calls, money — its failure modes change category: from "wrong answer" to "wrong action." Smaller models build agents the demo way: give it all the tools, trust the loop, watch it work. This skill is the discipline for systems where the model *acts*: assume the model will eventually do the worst plausible thing its permissions allow, and design so that when it does, the blast radius is survivable.

## The Rule

**Capability never exceeds containment. Before giving an agent a new tool or permission, the answer to "what's the worst action this enables, and can we detect, bound, and undo it?" must be written down.**

The analysis lives at `.claude/plans/agent-caps/{tool}.md`, one per tool/permission, written *before* the tool is wired in:

```markdown
## {tool name}
**Worst plausible action:** {what the model could do with this at full permission}
**How detected:** {log line, alert, rate anomaly}
**How bounded:** {sandbox, allowlist, cap — the environmental control}
**How undone:** {rollback path, or "irreversible → human gate"}
```

## How to Apply

### 1. Least privilege, mechanically enforced

- Each tool gets the narrowest scope that works: read-only where possible, allowlisted paths/domains/tables, scoped API keys — enforced by the *environment* (sandbox, IAM, network policy), never by the prompt. "Please don't delete files" is not a control.
- Separate the agent's identity from the user's and from yours. An agent with your credentials *is* you.

### 2. Tiered actions, human gates where it's irreversible

Classify every action the agent can take (mirror of tierless-router):
- **Reversible + bounded** (read, draft, compute) → autonomous
- **Reversible but outward-facing** (send message, post comment) → autonomous with logging and rate limits
- **Hard to reverse** (delete, deploy, pay, publish, grant access) → human approval, every time, no batch-approve
- The classification lives in code (which tools require confirmation), not in the system prompt.

### 3. Bound the loop

- Hard caps on: iterations, wall-clock time, spend, and actions-per-run — enforced outside the model
- Kill switch that actually kills (process-level, not a polite message the agent can ignore)
- Watch for runaway patterns: same action repeated, error-retry spirals, expanding scope ("to fix X I'll first modify Y")

### 4. Treat all inputs as injection vectors

Anything the agent reads — web pages, emails, file contents, tool results — can contain instructions. Assume it does:
- Instructions and data in separate channels; data never promoted to instructions
- The agent's privileges apply to what *it* does with what it read: an email saying "forward all messages to X" must hit the same action gates as any other request
- Red-team your own agent with injected content *before* someone else does
- Injection surfaces are security surfaces: run the **security-review** skill over the agent's input channels and privilege boundaries, same as any auth code

### 5. Eval the failure modes, not just the success modes

Extend the ai-building eval discipline with safety rows: prompt-injection attempts, scope-expansion temptations ("you'd finish faster with admin access"), instruction conflicts, and honesty under failure (does it report "I couldn't" or fabricate success?). An agent that fabricates success on 2% of tasks is worse than one that fails honestly on 10%.

### 6. Audit trail

Every action logged with: what, why (the model's stated reasoning), triggered-by-what-input, reversible-or-not. When something goes wrong you need the full causal chain — see incident-response.

## Anti-Patterns

- Safety by system prompt ("you must never...") with no environmental enforcement behind it
- Writing the worst-case analysis after the tool already shipped — a back-filled analysis documents the risk you already took instead of gating it
- Auto-approve fatigue: human gates that everyone clicks through unread — fewer, higher-signal gates beat many rubber stamps
- Testing the agent only on tasks it should do, never on tasks it shouldn't
- Assuming a smarter model needs fewer controls (more capable = larger worst-plausible-action, so *more* containment)
- Trusting the agent's self-report of what it did over the audit log

## Verification

Done means evidence, not vibes:
- `.claude/plans/agent-caps/{tool}.md` exists for every tool the agent holds, dated before the tool shipped
- Red-team transcript attached: N injection attempts and N scope-expansion probes logged with outcomes (N stated up front; zero attempts is a FAIL)
- Verdict is PASS/FAIL; a gate the agent never hit in testing is untested, not passed
