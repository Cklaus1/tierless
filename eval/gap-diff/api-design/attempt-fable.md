# Money-Movement API Design

HTTP API for sending transfers between accounts, listing past transfers, and checking the status
of a transfer. Consumers are first-party web/mobile clients and third-party developers, so the
design treats the public contract as the primary artifact: everything here is safe to expose
externally, and first-party clients use the same API (no privileged shadow endpoints — that is how
contracts drift).

---

## 1. Design summary (the decisions that matter)

| Decision | Choice | Why it matters |
|---|---|---|
| Resource model | `Transfer` is a first-class, immutable-request resource with a server-owned lifecycle (`status`) | Money movement is asynchronous in the real world (rails, reviews, reversals). Modeling it as "POST returns final result" is a lie that breaks the moment you add a slow rail. |
| Creation semantics | `POST /v1/transfers` returns **`201` or `202`-style acceptance encoded as `201` + `status: "pending"`** — creation succeeds, settlement is async | Clients poll `GET /v1/transfers/{id}` or consume webhooks; the API never blocks on settlement. |
| Idempotency | **`Idempotency-Key` header required on `POST /v1/transfers`** | The single most important correctness feature in a money API. Retried requests (mobile networks, client timeouts) must not double-send money. |
| Money representation | **Integer minor units + ISO 4217 currency string** (`"amount": 12345, "currency": "USD"` = $123.45) | Floats and decimal strings both cause bugs; integer minor units are unambiguous across JSON parsers in every language. |
| IDs | Opaque, prefixed strings: `tr_9f8a2b...`, `acct_...` | Prefixes make logs/debugging self-describing; opacity means we can change the backing storage. No sequential integers (enumeration + information leak). |
| Statuses | Small closed-for-now enum with a documented **"clients must tolerate unknown values"** rule + `status_details` for granularity | Lets us add lifecycle nuance without a breaking change. |
| Errors | One error envelope everywhere: machine-readable `type`/`code`, human `message`, field-level details | Third parties program against `code`, not message strings. |
| Pagination | **Cursor-based** (`limit` + `starting_after`), never offset | Offset pagination skips/duplicates rows while new transfers are being written — unacceptable for financial lists. |
| Versioning | URL major version (`/v1/`) + additive-only changes within v1 | Explicit rules below for what counts as non-breaking. |
| Cancellation | `POST /v1/transfers/{id}/cancel` (verb sub-resource), not `DELETE` | Transfers are never deleted; cancel is a state transition that can fail. |
| Auth | `Authorization: Bearer <token>` — OAuth2 user tokens (first-party), API keys/OAuth client credentials (third-party). Third-party access scoped: `transfers:read`, `transfers:write` | Same endpoints, different credential types; scopes gate write access. |

---

## 2. Resource: `Transfer`

The canonical representation, returned by every endpoint that touches a transfer:

```json
{
  "id": "tr_9f8a2b41c6d34e7f",
  "object": "transfer",
  "status": "pending",
  "status_details": null,
  "amount": 12345,
  "currency": "USD",
  "source_account_id": "acct_7d1e3f92",
  "destination_account_id": "acct_4b9c0a17",
  "description": "Rent, July",
  "reference": "invoice-2026-0711",
  "failure": null,
  "created_at": "2026-07-12T14:03:21Z",
  "completed_at": null,
  "metadata": {
    "order_id": "ord_555"
  }
}
```

Field notes:

- **`id`** — opaque, prefixed, globally unique. The only key clients should store.
- **`object`** — type discriminator (`"transfer"`). Cheap now, invaluable later for webhook payloads
  and polymorphic lists.
- **`amount`** — integer, **minor units** of `currency` (cents for USD). Always positive; direction
  is expressed by source/destination, not sign.
- **`currency`** — ISO 4217 uppercase code.
- **`status`** — lifecycle state, see §3.
- **`status_details`** — optional free-form-ish object for sub-state (e.g.
  `{"reason": "compliance_review"}` while `status` stays `"pending"`). Lets us add nuance without
  growing the enum.
- **`reference`** — client-supplied, shown to counterparties / on statements. Distinct from
  `description` (private note) and `metadata` (structured key-value bag for the integrator's own
  reconciliation; never shown to end users, max 50 keys, string values).
- **`failure`** — `null` unless `status` is `"failed"` or `"returned"`; then:
  ```json
  { "code": "insufficient_funds", "message": "The source account has an insufficient balance." }
  ```
- **Timestamps** — RFC 3339 UTC, `Z` suffix, second precision. `completed_at` is `null` until the
  transfer reaches a terminal state.

**Nulls vs. omission:** fields that exist but have no value are serialized as `null`, not omitted.
Stable shape is kinder to typed clients, and it makes "field added in a newer version" (absent)
distinguishable from "no value" (`null`).

---

## 3. Status lifecycle

```
              +-----------+
   create --> |  pending  | ---(cancel window / review)---> canceled   [terminal]
              +-----------+
                    |
                    v
              +------------+
              | processing | --> failed     [terminal]
              +------------+
                    |
                    v
               completed  ---(rail bounce, days later)---> returned   [terminal]
```

- `pending` — accepted, not yet submitted to the payment rail. Cancelable.
- `processing` — submitted; no longer cancelable.
- `completed` — funds moved. **Not necessarily final forever:** some rails (ACH) can bounce a
  completed transfer days later, which transitions it to `returned`. Documenting this up front
  saves every integrator a painful surprise.
- `failed` — did not move money. `failure` is populated.
- `canceled` — stopped before submission. No money moved.
- `returned` — moved and then reversed by the rail. `failure` is populated with the return reason.

**Forward-compatibility rule (documented, load-bearing):** clients MUST treat an unrecognized
`status` value as "in progress, not terminal" and keep polling / rely on webhooks. This is what
lets us add e.g. `requires_approval` later without a v2.

---

## 4. Endpoints

All endpoints:

- Base path `https://api.example.com/v1`
- `Authorization: Bearer <token>` required; requests without it get `401`, requests with a valid
  token but missing scope get `403`.
- Request/response bodies are `application/json; charset=utf-8`.
- Every response carries `Request-Id: req_...` (echo it in support tickets) and rate-limit headers
  (`RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`).

### 4.1 Create a transfer — `POST /v1/transfers`

**Headers**

```
Authorization: Bearer sk_live_...
Idempotency-Key: 0f4b9d2c-6a8e-4f1d-9c3b-7e5a1d8f2b6c
Content-Type: application/json
```

`Idempotency-Key` is **required** (we reject its absence with `400` rather than silently accepting
unsafe retries — third-party integrators will not read the docs, so the API enforces the safety
property). Client-generated, unique per logical transfer attempt, e.g. a UUIDv4. Keys are retained
for 24 hours.

**Request**

```json
{
  "amount": 12345,
  "currency": "USD",
  "source_account_id": "acct_7d1e3f92",
  "destination_account_id": "acct_4b9c0a17",
  "description": "Rent, July",
  "reference": "invoice-2026-0711",
  "metadata": { "order_id": "ord_555" }
}
```

Required: `amount` (integer > 0), `currency`, `source_account_id`, `destination_account_id`.
Optional: `description`, `reference`, `metadata`.

Unknown request fields are **rejected** with `400` (`code: "unknown_parameter"`). This is the
opposite of the tolerant-reader rule for responses, deliberately: silently ignoring a misspelled
`destination_acount_id` in a money API means silently doing the wrong thing. Strict on input,
additive on output.

**Response — `201 Created`**

```
HTTP/1.1 201 Created
Location: /v1/transfers/tr_9f8a2b41c6d34e7f
Request-Id: req_a1b2c3
```

```json
{
  "id": "tr_9f8a2b41c6d34e7f",
  "object": "transfer",
  "status": "pending",
  "status_details": null,
  "amount": 12345,
  "currency": "USD",
  "source_account_id": "acct_7d1e3f92",
  "destination_account_id": "acct_4b9c0a17",
  "description": "Rent, July",
  "reference": "invoice-2026-0711",
  "failure": null,
  "created_at": "2026-07-12T14:03:21Z",
  "completed_at": null,
  "metadata": { "order_id": "ord_555" }
}
```

`201` means "the transfer resource exists and is being worked on," **not** "money has moved."
Settlement is observed via `GET` polling or webhooks (§6). Synchronously-failable checks
(validation, balance check, limits, sanctioned counterparty) fail the POST itself; anything that
depends on the rail happens async and surfaces as a status transition.

**Idempotency semantics (exact behavior):**

| Situation | Result |
|---|---|
| First request with key K | Processed normally; response stored against K. |
| Retry with key K, **same** request body | `200 OK` replaying the original stored response, plus header `Idempotency-Replayed: true`. (Note `200`, not `201` — nothing new was created; either code is defensible but we document one and stick to it.) |
| Retry with key K, **different** body | `409 Conflict`, `code: "idempotency_key_reuse"`. The client has a bug; do not guess. |
| Retry with key K while the first request is **still executing** | `409 Conflict`, `code: "idempotency_key_in_flight"`, `Retry-After: 1`. Prevents the race where two concurrent retries both pass the "does K exist?" check. |

The idempotency record is written **atomically with** (same transaction as) the transfer row, so a
crash between "create transfer" and "record key" cannot produce a double-send.

**Create-time failures**

- `400 invalid_request` — malformed JSON, missing/invalid fields, unknown fields, unsupported
  currency, `amount <= 0`, source == destination.
- `401` / `403` — bad token / missing `transfers:write` scope, or the token's principal doesn't own
  `source_account_id` (we return `403`, not `404`, for "you can't send from that account you can
  see"; `404` for accounts outside the principal's visibility entirely — don't leak existence).
- `402 Payment Required`, `code: "insufficient_funds"` — the one place this status code is
  actually on-label. (If `402` feels too cute for your org, `422` with the same `code` is fine;
  what matters is that the machine-readable `code` is the contract, and it's documented.)
- `404 not_found` — a referenced account doesn't exist *or is not visible to the caller*.
- `409` — idempotency conflicts, as above.
- `422 unprocessable`, `code: "account_frozen"`, `"limit_exceeded"`, etc. — request was
  well-formed, business rules said no.
- `429 rate_limited` — with `Retry-After`.
- `500` / `503` — **safe to retry with the same `Idempotency-Key`**; this is the whole point.

### 4.2 Get a transfer — `GET /v1/transfers/{id}`

```
GET /v1/transfers/tr_9f8a2b41c6d34e7f
Authorization: Bearer sk_live_...
```

**Response — `200 OK`** with the canonical Transfer object (§2). This *is* the status-check
endpoint; status is a field on the resource, not a separate `/status` endpoint — one shape, one
cache, one doc page.

- `404 not_found` — no such transfer, **or** the transfer belongs to a principal the caller can't
  see (existence must not leak across tenants).
- `GET` is stable and cacheable per-user (`Cache-Control: private, no-store` by default though —
  it's financial data and it changes).

### 4.3 List transfers — `GET /v1/transfers`

```
GET /v1/transfers?limit=25&status=completed&created_after=2026-07-01T00:00:00Z&starting_after=tr_9f8a2b41c6d34e7f
```

Query parameters:

- `limit` — 1–100, default 25.
- `starting_after` — cursor: the `id` of the last transfer on the previous page.
- `status` — filter; repeatable (`status=failed&status=returned`).
- `source_account_id`, `destination_account_id` — filters.
- `created_after`, `created_before` — RFC 3339 bounds.

Order: `created_at` **descending** (newest first), tie-broken by `id`, and stable — cursor
pagination over this order never skips or duplicates a transfer even while new ones are created,
which is exactly the failure mode of `offset=` pagination and why we don't offer it.

**Response — `200 OK`**

```json
{
  "object": "list",
  "data": [
    {
      "id": "tr_9f8a2b41c6d34e7f",
      "object": "transfer",
      "status": "completed",
      "status_details": null,
      "amount": 12345,
      "currency": "USD",
      "source_account_id": "acct_7d1e3f92",
      "destination_account_id": "acct_4b9c0a17",
      "description": "Rent, July",
      "reference": "invoice-2026-0711",
      "failure": null,
      "created_at": "2026-07-12T14:03:21Z",
      "completed_at": "2026-07-12T14:03:44Z",
      "metadata": { "order_id": "ord_555" }
    }
  ],
  "has_more": true,
  "next_cursor": "tr_9f8a2b41c6d34e7f"
}
```

The list is wrapped in an **envelope object, never a bare JSON array** — a bare array can never
grow pagination or aggregate fields without a breaking change (and is a legacy XSS hazard).
`next_cursor` is passed as the next request's `starting_after`; treat it as opaque. Unknown filter
parameters are rejected with `400` (same strict-input rule: a typo'd filter that gets ignored
returns *more* money-movement rows than the caller asked for, which is a correctness bug, not a
convenience).

An empty result is `200` with `"data": []` — never `404`.

### 4.4 Cancel a transfer — `POST /v1/transfers/{id}/cancel`

```
POST /v1/transfers/tr_9f8a2b41c6d34e7f/cancel
Authorization: Bearer sk_live_...
```

No body required. A verb-as-subresource `POST`, not `DELETE /v1/transfers/{id}`: nothing is
deleted (the record is permanent), the operation can fail for state reasons, and it returns the
updated resource.

**Response — `200 OK`** with the Transfer, now `"status": "canceled"`.

- `409 Conflict`, `code: "not_cancelable"` — transfer already `processing`/terminal. The response
  `error` includes the current status so clients don't need a second round trip:
  ```json
  {
    "error": {
      "type": "conflict",
      "code": "not_cancelable",
      "message": "Transfer tr_9f8a2b41c6d34e7f is already processing and can no longer be canceled.",
      "transfer_status": "processing"
    }
  }
  ```
- Canceling an already-`canceled` transfer returns `200` with the unchanged resource (idempotent
  no-op), so retries of a cancel are safe without an idempotency key.

---

## 5. Error handling

Every non-2xx response, from every endpoint, uses one envelope:

```json
{
  "error": {
    "type": "invalid_request",
    "code": "amount_invalid",
    "message": "amount must be a positive integer in minor units (e.g. cents).",
    "param": "amount",
    "request_id": "req_a1b2c3"
  }
}
```

- **`type`** — coarse class, small closed set: `invalid_request`, `authentication`, `permission`,
  `not_found`, `conflict`, `unprocessable`, `rate_limited`, `api_error`. Maps ~1:1 to status code
  families; useful for generic client middleware.
- **`code`** — fine-grained, machine-readable, **the stable contract**. New codes may be added
  (clients must fall back on `type`/status when they see an unknown code); existing codes are never
  renamed or repurposed.
- **`message`** — human/developer-readable, English, explicitly documented as **not stable and not
  for programmatic matching or end-user display**. First-party clients localize from `code`.
- **`param`** — present for field-level validation errors. Multiple field errors: `400` with
  `code: "validation_failed"` and an `errors` array of `{param, code, message}` so the client can
  render every problem in one round trip.
- **`request_id`** — correlates with logs; also in the `Request-Id` header.

Status-code discipline: `4xx` means "your request — don't retry unchanged" (except `408/429`),
`5xx` means "us — retry with backoff, and on `POST /transfers` retry with the *same*
idempotency key." `429` and `503` carry `Retry-After`.

---

## 6. Webhooks (companion to polling)

Because settlement is async, polling `GET /v1/transfers/{id}` works but scales badly for third
parties. We emit webhook events on every status transition:

```json
{
  "id": "evt_2c7d1a90",
  "object": "event",
  "type": "transfer.completed",
  "created_at": "2026-07-12T14:03:44Z",
  "data": { /* full Transfer object as of this transition */ }
}
```

Event types: `transfer.created`, `transfer.processing`, `transfer.completed`,
`transfer.failed`, `transfer.canceled`, `transfer.returned` — and the docs state new
`transfer.*` types may appear; consumers must ignore unknown types.

Delivery rules that matter for correctness:

- Signed (`Webhook-Signature` HMAC header) — receivers must verify.
- **At-least-once, possibly out of order.** Receivers must be idempotent on `evt_` id and should
  treat the event as a hint: on receipt, `GET` the transfer for authoritative current state rather
  than trusting event ordering.
- Retried with exponential backoff for non-2xx responses for up to 3 days.

(First-party mobile/web clients typically just poll or use our push channel; webhooks are the
third-party contract.)

---

## 7. Versioning & evolution policy

**URL major version** (`/v1/`), bumped only for genuinely breaking changes, which we expect to be
rare because of the additive rules below. Old major versions get a published deprecation window
(≥12 months) with `Deprecation` and `Sunset` headers on responses.

**Non-breaking (allowed within v1, no notice required):**
- Adding response fields. Clients must ignore unknown response fields (tolerant reader — stated in
  the docs and in our client-library design).
- Adding *optional* request fields and query filters.
- Adding new endpoints, new event types, new error `code`s.
- Adding enum values to fields documented as open (`status`, `failure.code`, event `type`) — each
  such field's docs carry an explicit "unknown value" fallback behavior (§3).
- Lengthening or changing the internal format of opaque IDs and cursors (clients were told they're
  opaque; we mean it — documented max length 255 so they can size columns).

**Breaking (requires v2):**
- Removing/renaming fields or endpoints; changing a field's type or units; changing status-code
  semantics; making an optional request field required; changing sort order or pagination
  semantics.

Two habits that make this policy real rather than aspirational: (1) responses always serialize the
full stable shape (nulls included) so "absent vs null" stays meaningful, and (2) request parsing is
strict, so we can *add* a parameter later without wondering whether some integrator has been
sending it (misspelled) for years and silently depending on it being ignored.

---

## 8. Correctness checklist (why each piece is here)

1. **No double-sends:** required `Idempotency-Key`, atomic key+transfer persistence, replay
   semantics, in-flight conflict handling, and "5xx ⇒ retry same key" guidance.
2. **No amount corruption:** integer minor units; no floats anywhere in the contract.
3. **No lying about settlement:** `201` = accepted, `status` = truth, `completed` can still become
   `returned` on reversible rails — all documented.
4. **No lost/duplicated rows in lists:** cursor pagination over a stable total order.
5. **No cross-tenant leaks:** opaque IDs, `404` for invisible resources, `403` only when the
   resource is legitimately visible but the action is forbidden.
6. **No silent misinterpretation:** strict request parsing (unknown fields/params rejected),
   tolerant response reading (unknown fields/enum values handled) — asymmetry is intentional.
7. **No un-debuggable failures:** `Request-Id` on everything, `code`-first error contract,
   `param`-level validation detail.
8. **No breaking third parties by accident:** written additive-change policy, open-enum rules,
   envelope-wrapped lists, opaque cursors/IDs, versioned URL with a sunset process.
