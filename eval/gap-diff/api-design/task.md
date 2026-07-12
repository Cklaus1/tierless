# API design task

Design the HTTP API for a **money-movement** feature in an existing payments product: a user can
send a transfer from their account to another account, list their past transfers, and check the
status of one. Consumers are (a) our own web/mobile clients and (b) third-party developers via a
public API.

Give the endpoint design: routes, methods, request/response shapes (show the JSON), status codes,
and error handling. Call out the decisions that matter for correctness and for evolving the API
without breaking existing integrations. Be concrete — show the actual request and response bodies.
