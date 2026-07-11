---
name: threat-modeling
description: Threat-modeling skill — design-time security: enumerate assets, attackers, and attack surfaces BEFORE code exists, so security is architecture rather than patches
metadata:
  type: user
---

# Threat Modeling — Design-Time Security Skill

## Why

security-review finds vulnerabilities in a diff — after the design decided where the vulnerabilities could live. Smaller models treat security entirely at that review stage: design the feature for the happy path, then patch what the review catches. But the expensive security failures are *architectural* — the trust boundary in the wrong place, the token that shouldn't exist, the service that never needed access to the data it leaks — and no diff review fixes those; they're load-bearing by review time. This skill asks "who can abuse this?" while the design is still cheap to change: at compose/plan-mode time, before code exists.

## The Rule

**Any Tier 2+ design that crosses a trust boundary gets a threat model before implementation begins — assets, attackers, entry points, and the mitigations that shape the design itself.** Security added at review time is a patch; security decided at design time is architecture.

Fires per tierless-router's lanes alongside compose: new external interface, new auth/permission surface, new data store holding user data, new third-party integration, or any agentic/AI system (with ai-safety).

## How to Apply

Write `.claude/plans/{task-name}-threats.md` during compose/plan-mode:

### 1. What are we protecting? (assets)

Enumerate concretely: which data (credentials, PII, payment records, tokens), which capabilities (send email as the user, spend money, execute code), which properties (availability, integrity of records). "The system" is not an asset; "the session tokens in Redis" is.

### 2. Who attacks, with what access? (attackers)

Realistic tiers, not movie villains: anonymous internet traffic; an authenticated user of the free tier; a malicious org member attacking their own org's admin; a compromised dependency or stolen laptop; the insider with the database password. Each tier has different reach — the design must name which tiers it defends against and which it explicitly does not (that's a documented risk acceptance, not an omission).

### 3. Where do they get in? (surfaces, on the design diagram)

Walk the proposed design and mark every trust boundary: network entry points, user input paths, inter-service calls, third-party callbacks/webhooks, file uploads, background jobs consuming queues. For each boundary, the STRIDE-shaped questions — can they pretend to be someone else here (spoofing)? alter data in transit/at rest (tampering)? see what they shouldn't (disclosure)? flood it (DoS)? do more than their role allows (elevation)? deny they did it (no audit)?

### 4. Rank and decide — the output is design changes

For each credible threat: likelihood × impact (same scale as compose's risk rows), then one of:
- **Redesign** — the best outcome: the threat dies structurally (don't store the data, split the service, move the check server-side)
- **Mitigate** — a named control at a named boundary, which becomes a plan-mode step and later a security-review checkpoint
- **Accept** — written, with the reasoning and the attacker tier it concedes to — surfaced to the user, never silent

The test of a real threat model: it *changed the design*. A threat model that blessed the original design unchanged is usually a rubber stamp (occasionally the design was right — say why).

### 5. Hand off to the pipeline

The threat model's mitigations become plan-mode steps; its boundaries become security-review's target list when the diff arrives (that skill verifies the controls exist; this one decided where they go). Revisit the model when the design changes materially — an escalation trigger, same as tierless-router's.

## Anti-Patterns (gaming behaviors)

- Writing the threat model after implementation, shaped to bless what was built — the back-filled analysis documents risk instead of gating it (same fraud as ai-safety's back-filled capability analysis)
- Threat-modeling the movie plot (nation-state cracks the crypto) while skipping the boring reality (user A changes the id in the URL to user B's)
- "Accepting" every inconvenient threat with a one-word reason — acceptance as a rubber stamp instead of a decision with an owner
- Listing threats without ranking — a 40-item list where nothing is prioritized defends nothing
- Modeling only the new component and ignoring what it *connects to* — the new service is fine; the credentials it holds to the old one are the finding
- Treating a passed security-review later as retroactive proof the threat model was complete — review checks the controls you decided on; it can't see the surface you never modeled

## Verification

Done means evidence, not vibes:
- [ ] `.claude/plans/{task-name}-threats.md` exists, dated before implementation began
- [ ] Assets and attacker tiers concrete (named data/capabilities, named access levels) — no "the system"/"hackers"
- [ ] Every trust boundary on the design has its STRIDE walk
- [ ] Every credible threat carries redesign/mitigate/accept — mitigations traceable to plan-mode steps, acceptances written with reasons
- [ ] The "what changed in the design because of this" line is filled in (or the explicit "nothing, because…" justification)

Verdict is PASS/FAIL; a threat model dated after the implementation is a FAIL.
