---
name: software-architecture
description: Software-architecture skill — discipline for system-level design: boundaries by change-rate, decisions recorded with reasons, boring by default
metadata:
  type: user
---

# Software Architecture — System Design Skill

## Why

Architecture is the set of decisions that are expensive to reverse. Smaller models make these decisions implicitly — a database chosen because the tutorial used it, a microservice split because it felt modern, coupling added one import at a time — and by the time the cost is visible, it's load-bearing. This skill makes the expensive-to-reverse decisions explicit, deliberate, and recorded, and keeps everything else flexible enough that it doesn't matter.

## The Rule

**Every hard-to-reverse decision gets written down with its reasons and its losing alternatives, before it's implemented. Everything else stays boring and replaceable.** The architecture is what you can't easily change — so decide it on purpose.

## How to Apply

### 1. Identify what's actually architectural

Sort every design choice by cost-to-reverse:
- **Architectural** (weeks+ to undo): data model and ownership, service boundaries, sync-vs-async communication, consistency model, primary datastore, public API shapes, authN/Z model
- **Not architectural** (days to undo): frameworks behind an interface, internal file layout, most library picks

Spend design effort proportionally. Bikeshedding folder structure while the data model slides by unreviewed is the classic inversion.

### 2. Record decisions as ADRs

Each architectural decision gets a short record in `.claude/plans/adr/{NNN}-{title}.md` (a compressed tech-doc):

```markdown
## ADR-{NNN}: {decision, stated as a decision}
**Status:** accepted | superseded-by-{NNN}
**Context:** {the forces: requirements, constraints, scale numbers — with figures}
**Decision:** {what we're doing}
**Alternatives rejected:** {each with the one reason that killed it}
**Consequences:** {what gets harder, what we're betting on, when to revisit}
```

The "Alternatives rejected" section is the payload — six months later, "why don't we just use X?" is answered in one lookup instead of one re-litigation.

### 3. Draw boundaries by change-rate and ownership, not by noun

Modules/services split along lines where: change happens for different reasons, different people own them, or scaling needs differ. Not along "there's a User, so there's a UserService." Test for a good boundary: can you describe its contract in three sentences, and could a team own it without meetings?

- Dependencies point one way; cycles between modules are architecture bugs, fix them the week they appear
- Data ownership is singular: one module writes a given table/entity; everyone else asks it

### 4. Default to boring, escalate with evidence

- Monolith with clean internal boundaries until *measured* pain says otherwise; the split is easy precisely when the boundaries were kept clean
- Proven stack over interesting stack; novelty budget: spend it on the one thing that differentiates the product
- No speculative flexibility ("we might need multi-tenant sharding") without a named, dated driver — YAGNI applies doubly at architecture scale because the carrying cost is higher

## Anti-Patterns

- Resume-driven architecture (Kafka for 100 events/day)
- Distributed monolith: microservice deployment cost with monolith coupling — the worst quadrant
- "We'll clean up the boundaries later" (later the imports are load-bearing)
- ADRs written to justify a decision already made and unreviewable
- Abstraction layers over things that never vary (the interface with one implementation, forever)
- Deciding architecture in the pull request that implements it — the review altitude is wrong by definition

## Verification

Reality drifts, so the gate is the drift check — quarterly, or at every build-loop phase exit:
- Evidence = the list of ADRs diffed against the code, each marked **holds** or **superseded**
- "Superseded" requires a new ADR with `superseded-by-{NNN}` set; either the code moves back or the record does — an architecture document that lies is worse than none
- Verdict is PASS/FAIL; a phase exit with no diff list attached is a FAIL
