# GRADER checklist — api-design task (deterministic keyword scoring)

A money-movement API has well-known correctness/evolution disciplines. A naive design does the
happy-path CRUD (POST /transfers, GET /transfers, GET /transfers/:id) and misses the things that
make a payments API safe and evolvable. Each is scored by keyword presence.

## The findings (the disciplines a rigorous payments-API design includes)
1. **Idempotency keys on the write** — the #1 payments-API discipline: a create-transfer must be
   idempotent (retry-safe) so a network retry doesn't double-send money.
   sig: `idempotenc|idempotency-key|idempotency key|retry-safe|retry safe|exactly.once|double.(charge|send|submit|spend)|dedup`
2. **Money as integer minor units + currency** — never floats; amount in cents/minor units with an
   explicit currency code.
   sig: `minor unit|cents|integer.*(amount|money)|amount.*(cents|minor|integer)|no float|not.*float|currency (code)?|ISO 4217`
3. **Explicit machine-readable error taxonomy** — coded errors (e.g. `insufficient_funds`,
   `account_not_found`), not just prose/HTTP status.
   sig: `error (code|taxonomy|type)|machine.readable|coded error|insufficient_funds|error.*enum|problem.?detail|application/problem`
4. **Pagination on the list endpoint** — cursor/limit; never an unbounded list.
   sig: `paginat|cursor|limit.*offset|page.?token|next.?page|has_more`
5. **Async status / state machine** — a transfer isn't instant; it has states (pending →
   settled/failed) and status is polled, not assumed synchronous.
   sig: `pending|settled|status.*(pending|processing|poll)|state machine|asynchronous|async.*(settle|process)|webhook`
6. **Versioning / non-breaking evolution** — explicit API version and additive-evolution policy.
   sig: `version|/v1|/v2|breaking change|additive|backward.?compat|deprecat`
7. **AuthZ / ownership on read** — a user can only list/read THEIR transfers; third-party scope.
   sig: `authoriz|ownership|only.*(their|own)|scope|IDOR|cross.(account|user|tenant)|can'?t (see|read|access) other`
8. **Amount validation / limits** — positive amount, upper bound / limit checks.
   sig: `positive amount|amount.*> 0|amount <= 0|limit|maximum|max.*amount|reject.*negative|validation`

## Scoring
Each finding present = 1. Report haiku vs fable /8. Discriminating (most-often-missed by a naive
design): #1 idempotency, #3 error taxonomy, #5 async state, #6 versioning. If bare haiku already
hits most of these, the skill is near-ceiling; if fable hits several haiku misses, real gap.
Note: keyword scoring is generous (a mention counts even if shallow) — applied equally to both,
so the COMPARISON is fair even if absolute numbers run high.
