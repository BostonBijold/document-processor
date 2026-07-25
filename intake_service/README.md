# Intake Service

Orchestrator: accepts a file upload, calls the Extraction service, then the
Invoice/Data service, and returns the stored invoice. Talks to both over
real HTTP (base URLs from env vars) -- no direct imports of their code, so
each service stays independently deployable/scalable.

## Setup

```
cd intake_service
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env.local          # then edit URLs if your ports differ
```

## Running all three services together

Each service defaults to uvicorn's port 8000, so when running them
simultaneously give each an explicit `--port`. Suggested convention:

| Service              | Port |
|----------------------|------|
| Extraction service   | 8000 |
| Invoice Data service | 8001 |
| Intake service        | 8002 |

```
# in extraction_service/
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# in invoice_data_service/
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001

# in intake_service/
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8002 --reload
```

`intake_service`'s `.env.local` should point `EXTRACTION_SERVICE_URL` /
`DATA_SERVICE_URL` at whatever ports you actually used for the other two.

## Endpoint

`POST /upload` -- multipart form upload, field name `file`. Accepts
`application/pdf`, `image/jpeg`, `image/png`; rejects anything else or an
empty file with `400`.

Flow: receive file -> call Extraction's `POST /extract` -> call Data's
`POST /invoices` with the extracted JSON + original binary -> return the
stored invoice.

### Response shapes

**Success** (`201`) -- extraction and storage both succeeded, whether or
not extraction flagged a `validation_warning`:
```json
{
  "status": "stored",
  "invoice": { "...": "the stored invoice, including its id" },
  "warning": "string, or null if extraction didn't flag anything"
}
```
A non-null `warning` is not an error -- the invoice is still stored. It's
surfaced explicitly (not just buried in `invoice.validation_warning`) so a
future UI can flag it for review without having to know to look for it.

**Extraction failed** (`502`) -- Extraction service was unreachable or
returned an error. Nothing was stored.
```json
{ "status": "extraction_failed", "detail": "..." }
```

**Storage failed after a successful extraction** -- the extracted data is
never silently dropped: it's logged server-side (`logger.error`, payload
included) *and* handed back in the response, so the caller doesn't lose
the extraction work even though nothing landed in the database.
- `400` if the Data service rejected the payload as invalid (e.g. missing
  a required field):
  ```json
  { "status": "storage_failed", "detail": "...", "extracted_data": { "...": "..." } }
  ```
- `502` if the Data service was unreachable or errored:
  ```json
  { "status": "storage_failed", "detail": "...", "extracted_data": { "...": "..." } }
  ```

**Bad upload** (`400`, plain FastAPI `{"detail": "..."}`) -- unsupported
content type or empty file, rejected before either downstream service is
called.

## Testing

### Automated (no live services needed)

`app.clients.extract_invoice` / `app.clients.create_invoice` are mocked, so
these run without Extraction, Data, Mongo, or a Gemini key:

```
.venv\Scripts\python.exe -m pytest
```

Covers: content-type/empty-file rejection, success with and without a
warning, extraction failure, and both storage-failure modes (validation
vs. unreachable) -- including that `extracted_data` survives in the error
response.

### End-to-end (needs all three services actually running)

This is the real "file in, structured invoice out, retrievable via the
Data service" check:

1. Start Extraction, Invoice Data, and Intake per the port table above
   (Extraction needs `GEMINI_API_KEY`, Data needs `MONGODB_URI`).
2. ```
   cd intake_service\scripts
   ..\.venv\Scripts\python.exe test_manual.py "C:\path\to\invoice1.pdf" "C:\path\to\invoice2.jpg"
   ```

For each file it prints the Intake response, then independently confirms
the returned invoice id is retrievable via the Data service's
`GET /invoices/{id}`, and reports how many of the files made it through
the full chain.

## Project layout

```
intake_service/
  app/
    main.py       FastAPI app, POST /upload orchestration
    clients.py     HTTP clients for Extraction and Data services (httpx)
    config.py       Env var config (EXTRACTION_SERVICE_URL, DATA_SERVICE_URL)
  scripts/
    test_manual.py  Real end-to-end check: upload -> extract -> store -> retrieve
  tests/
    test_api.py      API tests with both downstream services mocked
```
