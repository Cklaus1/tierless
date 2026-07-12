# Money-Movement API — Endpoint Design

## 1. Overview

Three endpoints for moving money between accounts within the existing payments product:

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/v1/transfers` | Create a new transfer |
| GET | `/v1/transfers` | List the authenticated user's transfers |
| GET | `/v1/transfers/{id}` | Retrieve status/details of one transfer |

All endpoints require Bearer-token authentication. All request/response bodies are JSON with `application/json` content type.

---

## 2. Create Transfer — `POST /v1/transfers`

### 2.1 Request

```
POST /v1/transfers
Authorization: Bearer <token>
Content-Type: application/json
Idempotency-Key: <uuid>   // optional but strongly recommended
```

**Request body:**

```json
{
  "amount": { "value": "1500.00", "currency": "USD" },
  "from_account": "acct_9f3k20d",
  "to_account": "acct_7h1m44p",
  "reference": "Invoice 42 payment",
  "metadata": {
    "order_id": "ord_8832",
    "customer_segment": "premium"
  }
}
```

**Field constraints:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `amount.value` | string (decimal, 2-decimal precision) | Yes | Must be > 0. Maximum per-transfer limit enforced server-side (e.g., $25,000). |
| `amount.currency` | string (ISO 4217) | Yes | Must be a supported currency. |
| `from_account` | string | Yes | Must belong to the authenticated user. Format: `acct_<base62>` |
| `to_account` | string | Yes | Must be a valid account in the system. |
| `reference` | string | No | Max 256 chars. Displayed on statements. |
| `metadata` | object | No | Arbitrary key-value pairs, max 20 keys, each key ≤ 64 chars, each value ≤ 512 chars. |

**Idempotency-Key header:**

A client-supplied UUID. If a request with the same key arrives within 24 hours, the server returns the original response without creating a second transfer. This is the primary defense against double-sends caused by network retries.

### 2.2 Response — 201 Created

```json
{
  "id": "xfr_3k9d20ma",
  "amount": { "value": "1500.00", "currency": "USD" },
  "from_account": "acct_9f3k20d",
  "to_account": "acct_7h1m44p",
  "status": "pending",
  "reference": "Invoice 42 payment",
  "metadata": {
    "order_id": "ord_8832",
    "customer_segment": "premium"
  },
  "created_at": "2026-07-11T14:32:01Z",
  "updated_at": "2026-07-11T14:32:01Z",
  "_links": {
    "self": { "href": "/v1/transfers/xfr_3k9d20ma" },
    "from_account": { "href": "/v1/accounts/acct_9f3k20d" },
    "to_account": { "href": "/v1/accounts/acct_7h1m44p" }
  }
}
```

### 2.3 Response — 409 Conflict (Idempotency Replay)

```json
{
  "error": {
    "code": "idempotency_replay",
    "message": "This request was previously submitted and created transfer xfr_3k9d20ma.",
    "idempotent": true
  },
  "_links": {
    "original_transfer": { "href": "/v1/transfers/xfr_3k9d20ma" }
  }
}
```

### 2.4 Error Responses

| Status | Error Code | When |
|--------|-----------|------|
| 400 | `invalid_request` | Malformed JSON, missing required fields, `amount.value` not a valid decimal, currency not supported. |
| 400 | `amount_exceeds_limit` | Transfer amount exceeds per-transfer or daily cumulative limit. |
| 400 | `amount_below_minimum` | Transfer amount is below the minimum (e.g., $0.50). |
| 401 | `authentication_failed` | Missing or invalid Bearer token. |
| 403 | `insufficient_funds` | `from_account` balance is insufficient. |
| 403 | `account_suspended` | Either account is frozen, closed, or restricted. |
| 404 | `account_not_found` | `to_account` does not exist or is not reachable. |
| 409 | `idempotency_replay` | Duplicate idempotency key (see 2.3). |
| 422 | `self_transfer` | `from_account` equals `to_account`. |
| 422 | `currency_mismatch` | `from_account` and `to_account` do not support the requested currency. |
| 429 | `rate_limit` | Too many transfer requests in the sliding window. |
| 500 | `internal_error` | Unexpected server error. |
| 503 | `service_unavailable` | Downstream ledger or account service is down. |

**Error body shape (all errors):**

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "Account acct_9f3k20d has a balance of $42.10, which is less than the requested $1,500.00.",
    "details": {
      "account_id": "acct_9f3k20d",
      "available_balance": { "value": "42.10", "currency": "USD" },
      "requested_amount": { "value": "1500.00", "currency": "USD" }
    },
    "idempotent": false
  }
}
```

The `idempotent` field tells the client whether retrying with the same idempotency key is safe (`true`) or whether the request may have had a side effect and should be retried with a new key (`false`).

---

## 3. List Transfers — `GET /v1/transfers`

### 3.1 Request

```
GET /v1/transfers?limit=25&cursor=eyJpZCI6Inhmcl8zazlkMjBtYSJ9&status=pending&sort=desc
```

**Query parameters:**

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `limit` | integer | 25 | 1–100. Number of transfers to return. |
| `cursor` | string | — | Opaque cursor from `next_cursor` of a prior response. Pagination is forward-only. |
| `status` | string | — | Filter by one of: `pending`, `completed`, `failed`, `cancelled`. Repeatable for multiple statuses. |
| `sort` | string | `desc` | `asc` or `desc` (by `created_at`). |
| `from_date` | string (ISO 8601) | — | Inclusive start of date range. |
| `to_date` | string (ISO 8601) | — | Inclusive end of date range. |

### 3.2 Response — 200 OK

```json
{
  "data": [
    {
      "id": "xfr_3k9d20ma",
      "amount": { "value": "1500.00", "currency": "USD" },
      "from_account": "acct_9f3k20d",
      "to_account": "acct_7h1m44p",
      "status": "pending",
      "reference": "Invoice 42 payment",
      "created_at": "2026-07-11T14:32:01Z",
      "updated_at": "2026-07-11T14:32:01Z"
    },
    {
      "id": "xfr_1a2b3c4d",
      "amount": { "value": "250.00", "currency": "USD" },
      "from_account": "acct_9f3k20d",
      "to_account": "acct_5e6f7g8h",
      "status": "completed",
      "reference": "Rent payment",
      "created_at": "2026-07-10T09:15:00Z",
      "updated_at": "2026-07-10T09:15:32Z"
    }
  ],
  "pagination": {
    "has_more": true,
    "next_cursor": "eyJpZCI6Inhmcl8xYTJiM2M0ZCJ9",
    "prev_cursor": null,
    "total_count": 147
  }
}
```

### 3.3 Error Responses

| Status | Error Code | When |
|--------|-----------|------|
| 400 | `invalid_cursor` | Malformed or expired cursor. |
| 400 | `invalid_date_range` | `from_date` is after `to_date`, or dates are in the future. |
| 401 | `authentication_failed` | Missing or invalid Bearer token. |
| 429 | `rate_limit` | Too many list requests. |

---

## 4. Get Transfer — `GET /v1/transfers/{id}`

### 4.1 Request

```
GET /v1/transfers/xfr_3k9d20ma
```

### 4.2 Response — 200 OK

```json
{
  "id": "xfr_3k9d20ma",
  "amount": { "value": "1500.00", "currency": "USD" },
  "from_account": "acct_9f3k20d",
  "to_account": "acct_7h1m44p",
  "status": "completed",
  "reference": "Invoice 42 payment",
  "metadata": {
    "order_id": "ord_8832",
    "customer_segment": "premium"
  },
  "created_at": "2026-07-11T14:32:01Z",
  "updated_at": "2026-07-11T14:32:33Z",
  "completed_at": "2026-07-11T14:32:33Z",
  "failure_reason": null,
  "ledger_entries": [
    {
      "account": "acct_9f3k20d",
      "amount": { "value": "-1500.00", "currency": "USD" },
      "type": "debit",
      "timestamp": "2026-07-11T14:32:01Z"
    },
    {
      "account": "acct_7h1m44p",
      "amount": { "value": "+1500.00", "currency": "USD" },
      "type": "credit",
      "timestamp": "2026-07-11T14:32:33Z"
    }
  ],
  "_links": {
    "self": { "href": "/v1/transfers/xfr_3k9d20ma" }
  }
}
```

When `status` is `failed`, `failure_reason` is populated:

```json
"failure_reason": {
  "code": "destination_rejected",
  "message": "The receiving account has rejected incoming transfers.",
  "retryable": false
}
```

### 4.3 Error Responses

| Status | Error Code | When |
|--------|-----------|------|
| 400 | `invalid_id` | `id` does not match expected format. |
| 401 | `authentication_failed` | Missing or invalid Bearer token. |
| 404 | `transfer_not_found` | No transfer with the given ID, or the authenticated user has no permission to view it. |
| 429 | `rate_limit` | Too many requests. |

---

## 5. Transfer Status Lifecycle

```
pending ──→ completed
    │           (final)
    │
    ├─→ failed ──→ (final)
    │
    └─→ cancelled ──→ (final)
```

- **pending**: Transfer has been accepted and is being processed. May remain pending for up to a configurable timeout (e.g., 30 minutes).
- **completed**: Funds have been debited from the source and credited to the destination.
- **failed**: Processing failed. The transfer is rolled back (funds restored to source). `failure_reason` is set.
- **cancelled**: Cancelled by the user (if cancellation is allowed before completion) or by the system (e.g., timeout).

A transfer can be cancelled only while in `pending` status. Cancellation is a separate operation not included in this initial API surface.

---

## 6. Key Design Decisions and Rationale

### 6.1 Amount as a string, not a number

`amount.value` is a string (`"1500.00"`) rather than a JSON number. This avoids floating-point precision issues that are unacceptable in financial systems. Clients and servers parse the string as a decimal type (e.g., `BigDecimal` in Java, `decimal` in C#, `Decimal` in Python).

### 6.2 Idempotency-Key header

Money movement is inherently unsafe to retry blindly. The `Idempotency-Key` header (a client-generated UUID) is the standard mechanism for safe retries. The server stores the key + response for 24 hours. If a duplicate key arrives, the stored response is returned.

**Decision:** The header is optional on the wire but the API documentation strongly recommends it. This balances third-party developer friction (they may not know about it) with safety (clients that do use it are protected).

### 6.3 Cursor-based pagination

Offset-based pagination (`?offset=50&limit=25`) is unreliable for financial data because inserts and deletes shift offsets. Cursor-based pagination (using the last item's ID as a bookmark) is stable and efficient.

**Decision:** Forward-only pagination (no `prev_cursor` in list, or limited backward pagination) to avoid expensive reverse scans on large datasets.

### 6.4 HATEOAS-style `_links`

Each response includes a `_links` object with `self` and related-resource links. This allows clients to navigate the API without constructing URLs from IDs, reducing coupling between client and server URL conventions.

**Decision:** `_links` are provided for discoverability but clients are expected to also construct URLs directly from IDs for performance-critical paths (e.g., polling).

### 6.5 Versioning via URL path (`/v1/`)

The API version is embedded in the URL path (`/v1/transfers`). This is the simplest and most widely understood versioning strategy.

**Decision:** When a breaking change is needed, release a new version (`/v2/transfers`) and maintain the old version for a deprecation period (minimum 12 months). Do not break existing fields or change semantics in-place.

### 6.6 Error body consistency

All errors follow the same envelope shape:

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "Human-readable explanation.",
    "details": { ... },
    "idempotent": false
  }
}
```

- `code` is machine-parseable.
- `message` is human-readable and may include contextual data (e.g., actual balance).
- `details` is an optional object with structured error context.
- `idempotent` tells the client whether retrying with the same key is safe.

### 6.7 Timestamps in UTC ISO 8601

All timestamps use UTC with `Z` suffix: `"2026-07-11T14:32:01Z"`. This avoids timezone ambiguity. Clients are responsible for converting to local time.

### 6.8 No transfer amount in cents (integer)

The amount uses a decimal string with explicit currency, not an integer in cents. This supports currencies with no fractional units (e.g., JPY) and avoids the common "always use cents" anti-pattern that breaks for zero-decimal currencies.

---

## 7. Security Considerations

### 7.1 Authentication

All endpoints require a Bearer token obtained from the product's existing auth system. The token must include scopes:

- `transfers:write` — required for `POST /v1/transfers`.
- `transfers:read` — required for `GET /v1/transfers` and `GET /v1/transfers/{id}`.

Third-party developers must be issued tokens via OAuth 2.0 client credentials or authorization code flow, depending on whether the app acts on behalf of a user.

### 7.2 Authorization scoping

- A user can only create transfers from accounts they own.
- A user can only list and view transfers involving their own accounts.
- Third-party tokens are scoped to the specific user's accounts (no cross-account access).

### 7.3 Rate limiting

- `POST /v1/transfers`: 10 requests per minute per account (to prevent rapid double-sends or abuse).
- `GET /v1/transfers`: 60 requests per minute.
- `GET /v1/transfers/{id}`: 60 requests per minute.

Rate limit headers are included in every response:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1689084781
```

### 7.4 TLS

All endpoints require TLS 1.2 or higher. HTTP is not supported.

### 7.5 Input validation

- `from_account` and `to_account` are validated against the account service at request time.
- `amount.value` is validated as a positive decimal with at most 2 decimal places.
- `reference` is sanitized to prevent injection (max 256 chars, no control characters).
- `metadata` keys and values are validated for length and character set (alphanumeric, hyphens, underscores).

---

## 8. Evolution and Backward Compatibility

### 8.1 Adding new fields

New optional fields can be added to request and response bodies without breaking existing clients. Clients that do not recognize a field simply ignore it.

**Example:** Adding a `network_fee` field to the response:

```json
"network_fee": { "value": "2.50", "currency": "USD" }
```

Existing clients that do not parse `network_fee` are unaffected.

### 8.2 Adding new enum values

New status values (e.g., `processing`) can be added. Clients should treat unknown statuses as "unknown state, keep polling" rather than assuming a final state.

### 8.3 Deprecating fields

Deprecated fields are marked in documentation but remain in responses for a minimum of 12 months. A `Deprecation` response header is sent:

```
Deprecation: true
Sunset: Sat, 11 Jul 2027 00:00:00 GMT
```

### 8.4 Adding new endpoints

New endpoints (e.g., `POST /v1/transfers/{id}/cancel`) do not affect existing clients. They are additive and do not change the shape of existing responses.

### 8.5 Changing response field types

Changing a field type (e.g., `status` from string to object) is a breaking change and requires a new API version.

---

## 9. Gaps and Risks Not Addressed in This Design

### 9.1 Transfer cancellation

The status lifecycle includes `cancelled`, but there is no endpoint to cancel a transfer. This should be added as `POST /v1/transfers/{id}/cancel` before the next API iteration.

### 9.2 Transfer scheduling

There is no way to schedule a transfer for a future time. This is a common requirement (e.g., recurring rent payments). A `scheduled_at` field on the create request would address this.

### 9.3 Bulk transfers

No endpoint exists for sending multiple transfers in a single atomic operation. If needed, a `POST /v1/transfers/batch` endpoint could be added.

### 9.4 Webhooks for status changes

Clients polling `GET /v1/transfers/{id}` for status updates is inefficient. A webhook subscription system (`POST /v1/webhooks`, `POST /v1/transfers/{id}/subscribe`) should be added so the server pushes status updates to clients.

### 9.5 Cross-currency transfers

The current design does not support converting between currencies. A `source_currency` and `target_currency` with an exchange rate would be needed for international transfers.

### 9.6 Transfer limits and compliance

Per-user daily/monthly transfer limits, AML/KYC checks, and large-transaction flags are not modeled in the API. These should be surfaced as error codes or as a separate compliance check endpoint.

### 9.7 Audit trail

The response includes `ledger_entries` for completed transfers, but there is no dedicated audit log endpoint. An `GET /v1/transfers/{id}/audit` endpoint would provide a full history of state changes.

### 9.8 Partial failures

If a transfer partially completes (e.g., debit succeeds but credit fails), the API must ensure atomicity — either both succeed or both fail. This is an implementation concern, but the API should document the guarantee (all-or-nothing semantics).

### 9.9 Timeouts and long-running transfers

Some transfers (e.g., cross-bank ACH) may take hours or days. The `pending` status could remain for an extended period. The API should document expected processing times per transfer type and support a `processing` status for long-running transfers.

### 9.10 Idempotency key storage cost

Storing idempotency keys for 24 hours at high throughput could require significant storage. Consider using a TTL-based store (e.g., Redis with EXPIRE) and monitoring storage growth.

### 9.11 Third-party API key management

Third-party developers need a way to rotate API keys without interrupting existing integrations. A key rotation endpoint (`POST /v1/api-keys/rotate`) should be provided.

### 9.12 Request size limits

No explicit request body size limit is documented. Large `metadata` objects or many concurrent requests could exhaust server resources. A `Content-Length` limit (e.g., 16 KB) should be enforced.

### 9.13 CORS for browser-based clients

Third-party developers using browser-based clients need CORS headers. The API should document which origins are allowed and whether credentials (cookies, auth headers) are supported.

### 9.14 OpenAPI specification

The API should be accompanied by an OpenAPI 3.1 specification document to enable code generation, client SDKs, and automated testing. This is a deliverable, not a design gap, but should be produced alongside the API.