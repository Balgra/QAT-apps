# Refit API activity log

`GET /api/activity-log` returns a downloadable UTF-8 JSON snapshot with `Cache-Control: no-store`. Logging is automatic for HTTP paths under `/api/`, including validation failures, missing resources, CORS preflights, and health checks. The download endpoint itself, `/docs`, and `/openapi.json` are not logged. There is no frontend logging button and no additional dependency.

The recorder belongs to one FastAPI application instance. Normal startup creates a new recorder, matching the fresh-data lifecycle. A download does not clear events; repeated downloads include the same completed calls plus any calls completed since the earlier download. An in-progress request appears after it completes. Concurrent calls receive sequence numbers in completion order.

## Export fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Export format version, currently `1` |
| `application`, `session_id` | Application name and identifier of this backend run |
| `started_at`, `exported_at` | UTC timestamps with explicit timezone offsets |
| `events` | Completed API observations |
| Event `sequence`, `timestamp`, `duration_ms` | Completion sequence, request start time, and elapsed milliseconds |
| Event `method`, `path` | HTTP method and API path |
| `request.query` | Query names mapped to lists of values, preserving repeated parameters |
| `request.payload`, `response.payload` | Capture envelopes containing content type, observed byte size, completeness, and decoded JSON `value` |
| `response.status_code` | HTTP response status; `500` if an exception occurred before a response started |
| `error_type` | Unhandled exception class, or `null`; handled HTTP/validation errors remain in the response payload |

For example, a checkout observation includes these payload values (other event/envelope fields omitted here):

```json
{
  "method": "POST",
  "path": "/api/checkout",
  "request": {
    "payload": {
      "value": {
        "items": [{"product_id": 2, "quantity": 1}],
        "card_number": "[REDACTED]",
        "expiry": "[REDACTED]",
        "cvv": "[REDACTED]"
      }
    }
  },
  "response": {"status_code": 200}
}
```

## Capture and redaction

Capture observes the ASGI messages consumed/emitted by the application without replacing or replaying them. Streaming JSON response chunks are combined for the log while forwarded unchanged to the client. Payloads are decoded values, not a byte-for-byte transcript of JSON whitespace or formatting. An unused request body or interrupted response can be incomplete; `complete: false` and `omitted_reason` make that explicit. An unexpected exception can be rendered by outer framework middleware, so its response body may not be observable here; the exception type and failure status are still recorded.

Each request/response body has a **1 MiB** capture limit. Oversized, non-JSON, invalid JSON, and incomplete bodies have `value: null` and an `omitted_reason`; partial/raw body text is not retained. Empty bodies have `value: null` without an omission reason. The capture limit does not limit or truncate the actual API response or request.

Credential-shaped keys are redacted recursively, including card/CVV/expiry/PIN/password/token fields and all validation-error `input` values. Headers are not retained. Other customer details and free-text input remain demonstration data in the file. The endpoint exposes this local teaching backend's whole run and has no separate authentication, matching the application's existing local demo controls.

Implementation: `app/activity_log.py` owns immutable event snapshots and thread-safe export; `app/activity_middleware.py` handles per-request capture. Tests are in `backend/tests/test_activity_log.py`.
