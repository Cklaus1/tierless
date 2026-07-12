# Money-Movement API Design

## Design Decisions (Top-Level)

- **RESTful resource model**: Transfers are first-class resources. `GET /transfers` lists them, `GET /transfers/{id}` inspects one, `POST /transfers` creates one.
- **Idempotency keys on `POST`**: Every create request accepts an `Idempotency-Key` header. The server deduplicates on this key for 24 hours. This is the single most important correctness guarantee for retry-safe client code.
- **Optimistic locking on account balances**: The server checks the source account balance at commit time. If the balance changed since the transfer was validated, the request fails with `409 CONFLICT` and a retry hint.
- **Async settlement**: `POST /transfers` returns `201 CREATED` with status `PENDING`. A background worker moves it to `COMPLETED` or `FAILED`. Clients poll `GET /transfers/{id}` or subscribe to webhooks (see section 7).
- **Versioned URLs**: All routes live under `/api/v1/`. Future incompatible changes go under `/api/v2/`.
- **Error envelope**: Every error response uses a single JSON shape (section 5) so clients can handle errors uniformly.

---

## 1. Create a Transfer

**`POST /api/v1/transfers`**

Creates a new money transfer from the authenticated user's account to a destination account.

### Request Headers

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID v4. Prevents duplicate charges on network retries. |
| `Content-Type` | Yes | `application/json` |

### Request Body

```json
{
  "amount": {
    "value": "150.00",
    "currency": "USD"
  },
  "destination_account": "acct_9fK2mPqR7sL",
  "reference": "Invoice #4210"
}
```

- `amount.value` — string, decimal notation (not float). Minimum `0.01`. Maximum per-transfer limit is enforced server-side (currently $25,000).
- `amount.currency` — ISO 4217 three-letter code. Source and destination must share the same currency for now (multi-currency is future work).
- `destination_account` — string, the destination account ID. Must belong to a valid account in the system.
- `reference` — string, optional, max 200 characters. Client-supplied memo for the transfer.

### Response

**`201 CREATED`**

```json
{
  "id": "xfr_3bN8vQwY2jH",
  "amount": {
    "value": "150.00",
    "currency": "USD"
  },
  "source_account": "acct_1aB2cD3eF4g",
  "destination_account": "acct_9fK2mPqR7sL",
  "reference": "Invoice #4210",
  "status": "PENDING",
  "created_at": "2026-07-12T03:14:22Z",
  "updated_at": "2026-07-12T03:14:22Z"
}
```

**`400 BAD REQUEST`** — validation failure (e.g. amount too small, invalid account ID).

```json
{
  "error": {
    "code": "INVALID_AMOUNT",
    "message": "Amount must be at least 0.01",
    "field": "amount.value"
  }
}
```

**`409 CONFLICT`** — idempotency key already used, or source account balance insufficient.

```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Source account balance is insufficient for this transfer",
    "retry_after": 5
  }
}
```

**`409 CONFLICT`** — duplicate idempotency key.

```json
{
  "error": {
    "code": "IDEMPOTENCY_KEY_EXISTS",
    "message": "A transfer with this idempotency key already exists",
    "idempotent_response": {
      "id": "xfr_3bN8vQwY2jH",
      "status": "COMPLETED"
    }
  }
}
```

**`422 UNPROCESSABLE ENTITY`** — destination account does not exist or is disabled.

```json
{
  "error": {
    "code": "DESTINATION_ACCOUNT_INVALID",
    "message": "The destination account is not found or has been disabled"
  }
}
```

**`429 TOO MANY REQUESTS`** — rate-limited.

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many transfer requests. Retry after 30 seconds."
  }
}
```

---

## 2. List Transfers

**`GET /api/v1/transfers`**

Returns the authenticated user's transfers, newest first. Paginated.

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 20 | Max items per page (1-100). |
| `cursor` | string | — | Opaque cursor from `next_cursor` of a prior response. |
| `status` | string | — | Filter by status: `PENDING`, `COMPLETED`, `FAILED`, `CANCELLED`. |
| `since` | string (ISO 8601) | — | Only transfers updated after this time. |

### Response

**`200 OK`**

```json
{
  "data": [
    {
      "id": "xfr_3bN8vQwY2jH",
      "amount": {
        "value": "150.00",
        "currency": "USD"
      },
      "source_account": "acct_1aB2cD3eF4g",
      "destination_account": "acct_9fK2mPqR7sL",
      "reference": "Invoice #4210",
      "status": "COMPLETED",
      "created_at": "2026-07-12T03:14:22Z",
      "updated_at": "2026-07-12T03:14:25Z"
    },
    {
      "id": "xfr_7cD4eFgH5iJ",
      "amount": {
        "value": "50.00",
        "currency": "USD"
      },
      "source_account": "acct_1aB2cD3eF4g",
      "destination_account": "acct_2kL3mN4oP5q",
      "reference": null,
      "status": "PENDING",
      "created_at": "2026-07-11T18:00:00Z",
      "updated_at": "2026-07-11T18:00:01Z"
    }
  ],
  "next_cursor": "eyJpZCI6Inhmcl83Y0Q0ZUZoSjVpSiJ9",
  "has_more": true
}
```

- `next_cursor` — opaque, URL-safe base64 string. Clients pass it back as `cursor` on the next request.
- `has_more` — boolean. If `true`, more pages are available.
- `data` — array of transfer objects (same shape as the GET-by-ID response, but without `updated_at` if the server optimizes that field out of list items).

**`400 BAD REQUEST`** — invalid cursor or `limit` out of range.

```json
{
  "error": {
    "code": "INVALID_CURSOR",
    "message": "The provided cursor is malformed or expired"
  }
}
```

---

## 3. Get Transfer Status

**`GET /api/v1/transfers/{transfer_id}`**

Returns the current state of a single transfer.

### Path Parameters

| Parameter | Description |
|---|---|
| `transfer_id` | The transfer ID, e.g. `xfr_3bN8vQwY2jH` |

### Response

**`200 OK`**

```json
{
  "id": "xfr_3bN8vQwY2jH",
  "amount": {
    "value": "150.00",
    "currency": "USD"
  },
  "source_account": "acct_1aB2cD3eF4g",
  "destination_account": "acct_9fK2mPqR7sL",
  "reference": "Invoice #4210",
  "status": "COMPLETED",
  "created_at": "2026-07-12T03:14:22Z",
  "updated_at": "2026-07-12T03:14:25Z",
  "completed_at": "2026-07-12T03:14:25Z"
}
```

- `completed_at` — present only when `status` is `COMPLETED` or `FAILED`. ISO 8601 timestamp.

**`404 NOT FOUND`**

```json
{
  "error": {
    "code": "TRANSFER_NOT_FOUND",
    "message": "No transfer found with id xfr_ZzZzZzZzZzZ"
  }
}
```

**`403 FORBIDDEN`** — the transfer exists but the authenticated user does not own it.

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have access to this transfer"
  }
}
```

---

## 4. Cancel a Transfer

**`POST /api/v1/transfers/{transfer_id}/cancel`**

Cancels a transfer that is still `PENDING`. Irreversible once the transfer has moved to `COMPLETED` or `FAILED`.

### Response

**`200 OK`**

```json
{
  "id": "xfr_3bN8vQwY2jH",
  "status": "CANCELLED",
  "updated_at": "2026-07-12T03:20:00Z"
}
```

**`409 CONFLICT`** — transfer is no longer cancellable.

```json
{
  "error": {
    "code": "TRANSFER_NOT_CANCELLABLE",
    "message": "Transfer is already COMPLETED and cannot be cancelled"
  }
}
```

**`404 NOT FOUND`**

```json
{
  "error": {
    "code": "TRANSFER_NOT_FOUND",
    "message": "No transfer found with id xfr_..."
  }
}
```

---

## 5. Error Envelope (Summary)

Every error response is `application/json` with this shape:

```json
{
  "error": {
    "code": "ENUM_CODE",
    "message": "Human-readable description",
    "field": "optional.field.path",
    "retry_after": 30
  }
}
```

| Field | When present |
|---|---|
| `code` | Always. Machine-readable error identifier. |
| `message` | Always. Human-readable explanation. |
| `field` | Only on `400` validation errors. Points to the offending JSON field. |
| `retry_after` | Only on `429` or `409` retry-hint errors. Seconds to wait. |

HTTP status codes and their meanings:

| Code | Meaning |
|---|---|
| `200` | Success (GET, POST cancel) |
| `201` | Created (POST transfer) |
| `400` | Bad request — client sent invalid data |
| `403` | Forbidden — authenticated but not authorized |
| `404` | Not found — resource does not exist |
| `409` | Conflict — idempotency collision, insufficient funds, or wrong state |
| `422` | Unprocessable — resource exists but is in an invalid state for this operation |
| `429` | Rate limited |
| `500` | Internal server error |
| `502` | Bad gateway (downstream payment network unreachable) |
| `503` | Service unavailable (maintenance window) |

---

## 6. Key Correctness Decisions

### 6.1 Idempotency

`POST /transfers` is inherently non-idempotent (sending the same request twice could double-charge). The `Idempotency-Key` header solves this: the server stores a hash of the key + request body and returns the original response for 24 hours if a duplicate arrives. If the body differs from the original, the server returns `409 CONFLICT` with `IDEMPOTENCY_KEY_MISMATCH`.

### 6.2 Amount Representation

`amount.value` is a **string**, not a JSON number. This avoids floating-point precision issues (e.g. `0.1 + 0.2 != 0.3` in IEEE 754). Clients and the server parse it as a decimal type. This is the same approach used by Stripe, Plaid, and other payments APIs.

### 6.3 Cursor Pagination

Cursor-based pagination (not offset/limit) is used because:
- It is O(1) regardless of dataset size.
- New transfers inserted between pages do not cause duplicates or gaps.
- The cursor is opaque — the server can change its encoding without breaking clients.

### 6.4 Status Lifecycle

```
PENDING -> COMPLETED
PENDING -> FAILED
PENDING -> CANCELLED   (only via explicit cancel)
```

Once a transfer leaves `PENDING`, it cannot return. This simplifies client state machines: a transfer is either in flight or done.

### 6.5 Backward Compatibility Guarantees

- **No field removals**: Existing fields in request/response bodies will never be removed. Fields can be added (clients that ignore unknown fields is the standard JSON behavior).
- **New required fields are additive**: If a new field becomes required on `POST /transfers`, it will be introduced as optional first, documented in a deprecation window (60 days), then required.
- **New error codes are additive**: Clients that do not recognize an error code should fall back to the `message` string.
- **URL versioning**: Breaking changes go under `/api/v2/`. `/api/v1/` is maintained for the lifetime of existing integrations.

---

## 7. Webhooks (Future-Proofing)

The API supports webhook notifications so clients do not need to poll. This is documented but not yet implemented in v1.

```
POST /api/v1/webhooks
  Body: { "url": "https://client.example.com/webhooks", "events": ["transfer.completed", "transfer.failed"] }

GET /api/v1/webhooks/{id}
POST /api/v1/webhooks/{id}   (update URL or events)
DELETE /api/v1/webhooks/{id}
```

Webhook payload on `transfer.completed`:

```json
{
  "id": "wh_abc123",
  "type": "transfer.completed",
  "created_at": "2026-07-12T03:14:25Z",
  "data": {
    "id": "xfr_3bN8vQwY2jH",
    "status": "COMPLETED",
    "amount": { "value": "150.00", "currency": "USD" },
    "completed_at": "2026-07-12T03:14:25Z"
  }
}
```

Webhooks include a `X-Webhook-Signature` header (HMAC-SHA256 of the payload) so clients can verify authenticity.

---

## 8. Security

- All endpoints require `Authorization: Bearer <token>`.
- Tokens are scoped: a token issued for a specific account can only access that account's transfers.
- Third-party API keys are scoped to read-only or read-write via a `scope` parameter at key creation time.
- TLS 1.2+ is required for all requests.
- Rate limits: 100 requests/minute per API key on `GET`, 20 requests/minute on `POST`.