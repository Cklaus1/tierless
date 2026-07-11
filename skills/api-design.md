---
name: api-design
description: API-design skill — contract-first design for endpoints, interfaces, and libraries; the contract outlives the implementation
metadata:
  type: user
---

# API Design — Contract-First Skill

## Why

Smaller models design APIs by writing the implementation and letting the interface "fall out" — leaking internals, naming things after database columns, and breaking callers with every refactor. An API is a promise you can't take back: implementations are cheap to change, contracts are not. This skill forces the contract to be designed, reviewed, and stress-tested before any implementation exists.

## The Rule

**Write the contract first — every endpoint/function signature, every data shape, every error — and walk real call sequences through it on paper before implementing anything.**

## How to Apply

### 1. Start from the consumer

Write the code you *wish* callers could write — 3 real usage examples for the top use cases — before defining the API. If the example code is awkward, the API is wrong, and it's never been cheaper to fix.

### 2. Define the contract

Write `.claude/plans/{api}-contract.md`:

```markdown
## API: {name}
**Consumers:** {who calls this, from where}

### Operations
{for each: name, inputs (types, required/optional, defaults), output shape,
 errors it can return, idempotency, auth required}

### Data shapes
{each entity once, with field types and nullability — the shape callers see,
 NOT the storage shape — storage shape is database-design's job}

### Errors
{every error: code, when it fires, what the caller should do about it.
 Errors are part of the contract, not an afterthought.}

### Guarantees
- Idempotency: {which operations, via what mechanism}
- Ordering / consistency: {what callers may assume}
- Rate/size limits: {numbers}

### Versioning & evolution
{how this changes without breaking callers: additive-only fields,
 version scheme, deprecation policy}
```

### 3. Stress the contract on paper

Walk these through the contract before implementing:
- The 3 consumer examples from step 1 — do they still read well?
- A retry after a timeout — is anything double-applied?
- A partial failure mid-sequence — can the caller tell what state they're in?
- Next year's most likely feature — additive change, or does it break the shape?

### 4. Design rules

- **Consistency beats cleverness**: same verbs, same casing, same pagination, same error envelope everywhere. One surprising endpoint poisons trust in all of them.
- **Name by domain, not by storage** — `customer.name`, not `cust_nm`; the API is documentation
- **Make invalid states unrepresentable**: required fields required, enums over stringly-typed values, no "set A only if B is null" rules a type system could enforce
- **Errors are UX for developers**: machine-readable code + human-readable message + what-to-do
- **Pagination, filtering, and timestamps from day one** on anything returning lists — retrofitting is a breaking change

## Evidence Gate (before declaring done)

- The 3 consumer examples from step 1 exist as actual tests against the implementation
- Contract file matches implemented behavior

## Anti-Patterns

- Exposing the database schema as the API ("it's faster") — now the schema can never change
- Wrote the contract after the implementation and back-dated it
- Stress-tested only the happy-path example
- Contract file exists but the implementation drifted and nobody re-checked
- Breaking changes hidden as "fixes" because the old behavior was unintended (callers depend on it anyway — see code-archaeology)
- Designing for hypothetical consumers with hypothetical needs — design for the 3 real examples, evolve additively
