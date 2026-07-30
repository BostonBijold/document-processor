# Invoice Data Service

Standalone microservice that owns MongoDB storage for invoices -- the CRUD
layer other services (Intake, a future frontend) will call. Not wired to
Intake or a frontend yet; the Extraction service's JSON output is the
expected input shape, but this service doesn't call Extraction directly.

## Setup

```
cd invoice_data_service
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env.local          # then edit MONGODB_URI if needed
```

Needs a MongoDB instance reachable at `MONGODB_URI` (defaults to
`mongodb://localhost:27017`). A local MongoDB Community Server or a free
Atlas cluster both work fine for this.

## Run

```
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Service comes up at http://localhost:8000. Interactive docs at
http://localhost:8000/docs.

## Endpoints

- `POST /invoices` -- multipart form: `data` (JSON string matching the
  Extraction service's output schema) + `file` (the original document
  binary). Stores both, defaults `status` to `"unpaid"`. Returns `201` with
  the created invoice, or `400` if `data` is missing required fields
  (e.g. `total`) or isn't valid JSON.
- `GET /invoices` -- list with query params `vendor_name` (case-insensitive
  substring match), `status` (`unpaid` | `paid` | `overdue`), `date_from` /
  `date_to` (filter on `issue_date`), `skip` / `limit` (pagination, default
  `skip=0, limit=20`, max `limit=100`). Returns `{items, total, skip, limit}`.
- `GET /invoices/{id}` -- single invoice. `404` if not found, `400` if `id`
  isn't a valid ObjectId.
- `GET /invoices/{id}/document` -- streams back the original uploaded file
  (`document_binary`) with its stored `document_content_type` as the
  response's `Content-Type`. Added for the frontend's document preview
  panel. `404` / `400` as above.
- `PATCH /invoices/{id}` -- body is every extracted field (`vendor_name`,
  `invoice_number`, `issue_date`, `due_date`, `line_items`, `subtotal`,
  `tax`, `total`, `currency` -- same shape as the `POST` body minus
  `validation_warning`). Not partial: the frontend's edit form always
  submits all of them together. `status`/`paid_date` are untouched --
  those go through `PATCH /invoices/{id}/status` instead. Recomputes
  `validation_warning` from the submitted totals (see below), so fixing a
  bad total in the edit form also clears the warning. `404` if not found,
  `422` if a required field is missing (this endpoint takes a plain JSON
  body, so FastAPI's default validation error applies, unlike `POST`'s
  `400` -- see design decisions).
- `PATCH /invoices/{id}/status` -- body `{"status": "paid" | "unpaid", "paid_date": "...")?}`.
  Setting `"paid"` without `paid_date` stamps it with the current time;
  setting `"unpaid"` clears `paid_date`. `404` / `400` as above.
- `DELETE /invoices/{id}` -- hard delete, for cleaning up bad test data.
  `204` on success, `404` if not found.

## Design decisions (as requested, documented rather than assumed)

**Overdue is computed at read time, not stored.** The `status` field
persisted in MongoDB only ever holds `"unpaid"` or `"paid"`. When a document
is read (`GET /invoices`, `GET /invoices/{id}`, or right after `POST`), if
its stored status is `"unpaid"` and `due_date` has passed, the response
reports `"overdue"` instead -- see `compute_effective_status` in
`app/repository.py`. Filtering `GET /invoices?status=overdue` translates to
the underlying query (`status="unpaid" AND due_date < now`) rather than a
literal field match. This avoids a stale/unsynced stored value and needs no
scheduled job; the tradeoff is that a raw `db.invoices.find()` in a Mongo
shell will show `"unpaid"` even for invoices the API reports as overdue.
`PATCH .../status` only accepts `"unpaid"`/`"paid"` as inputs -- you can't
manually set `"overdue"`, since it isn't a real stored state.

**`POST /invoices` is multipart, not pure JSON.** The document model
requires storing the raw file binary (`document_binary`) alongside the
extracted fields, and JSON can't carry binary cleanly. `data` carries the
Extraction-shaped JSON as a form field; `file` carries the binary.

**`validation_warning` is trusted from Extraction at insert time, but
recomputed on every edit.** `POST /invoices` just stores whatever
`validation_warning` came in the payload -- this service doesn't re-derive
it from the line items at creation time. `PATCH /invoices/{id}` does
recompute it (`_compute_validation_warning` in `app/repository.py`, using
the same tolerance logic as `extraction_service/app/validation.py`,
duplicated rather than shared across services on purpose), so correcting a
bad total through the edit form also clears a stale warning instead of
leaving it stuck.

**`document_binary` is never returned from the JSON endpoints** -- only
`document_content_type` is. Raw bytes don't belong in a JSON payload.
`GET /invoices/{id}/document` returns it separately as a raw response with
the correct `Content-Type`, for the frontend's preview panel.

## Testing

### Automated (no live MongoDB needed)

Uses `mongomock` to fake MongoDB in-memory, so these run without any
external dependency:

```
.venv\Scripts\python.exe -m pytest
```

`tests/test_repository.py` covers the CRUD + overdue logic directly;
`tests/test_api.py` covers the HTTP layer (status codes, validation errors,
filtering, pagination) with a mocked collection injected via FastAPI's
dependency override.

### End-to-end smoke test (needs a real MongoDB + the running server)

This is the "extract → store → retrieve" loop check before moving to
Intake:

1. Start MongoDB (if not already running).
2. Start the server: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`
3. In another terminal:
   ```
   cd invoice_data_service\scripts
   ..\.venv\Scripts\python.exe smoke_test.py
   ```

It inserts the 3 sample invoices in `scripts/sample_invoices.py` (shaped
like real Extraction service output -- one is deliberately overdue), walks
every endpoint, asserts the expected behavior at each step, and deletes
everything it created. Prints `All checks passed.` at the end if nothing
broke.

To test against invoices you actually ran through the Extraction service,
edit `SAMPLE_INVOICES` in `scripts/sample_invoices.py` with real output from
`extraction_service/scripts/test_manual.py`.

## Project layout

```
invoice_data_service/
  app/
    main.py            FastAPI app, all 5 endpoints
    repository.py       CRUD + overdue-computation logic against a Mongo collection
    schema.py            Pydantic models: ExtractionInput, InvoiceOut, StatusUpdate
    db.py                 Mongo client/collection accessor (FastAPI dependency)
    config.py             Env var config (MONGODB_URI, MONGODB_DB_NAME)
  scripts/
    sample_invoices.py    3 sample Extraction-shaped invoices for testing
    smoke_test.py           End-to-end CLI check against a running server + real Mongo
  tests/
    test_repository.py    Unit tests against repository.py (mongomock)
    test_api.py            API tests against the FastAPI app (mongomock)
```
