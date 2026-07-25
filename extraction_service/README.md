# Extraction Service

Standalone microservice that takes a binary invoice file (image or PDF) and
returns structured JSON via Gemini 2.5 Flash (Google AI Studio API). Not
wired to MongoDB, a frontend, or any other service -- test it directly.

## Setup

```
cd extraction_service
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then edit .env and add your GEMINI_API_KEY
```

Get an API key from Google AI Studio: https://aistudio.google.com/apikey

## Run

```
uvicorn app.main:app --reload
```

Service comes up at http://localhost:8000. Interactive docs at
http://localhost:8000/docs.

## Endpoint

`POST /extract` -- multipart form upload, field name `file`. Accepts
`application/pdf`, `image/png`, `image/jpeg`, `image/webp`, `image/heic`,
`image/heif`.

Response body matches:

```json
{
  "vendor_name": "string",
  "invoice_number": "string",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD | null",
  "line_items": [
    { "description": "string", "quantity": 0, "unit_price": 0, "amount": 0 }
  ],
  "subtotal": 0,
  "tax": 0,
  "total": 0,
  "currency": "string | null",
  "validation_warning": "string | null"
}
```

`validation_warning` is populated when the extracted line-item amounts
(plus tax) don't reasonably reconcile with the extracted total, or when the
extracted subtotal doesn't match the line-item sum -- a guardrail against
Gemini hallucinating the total field. `null` means it reconciled (or there
weren't enough line items to check).

Errors return a normal FastAPI JSON error body (`{"detail": "..."}`):
- `400` -- unsupported file type or empty upload
- `502` -- Gemini call failed, or its output didn't parse as JSON / didn't
  match the schema
- `500` -- `GEMINI_API_KEY` isn't configured

## Testing

### Automated (no API key needed)

Unit tests for the validation logic, plus API tests that mock the Gemini
call to check request handling, error paths, and schema wiring:

```
pytest
```

### Manual accuracy check against real invoices (needs API key)

This is the check that actually matters before sprint 2 -- run 2-3 real
invoices (PDF or photo/scan) through the service and eyeball the output.

1. Start the server: `uvicorn app.main:app --reload`
2. For each sample invoice:
   ```
   python scripts/test_manual.py path\to\invoice.pdf
   ```
3. Compare the printed JSON against the source document: vendor name,
   invoice number, dates, line items, subtotal/tax/total, and whether
   `validation_warning` fired correctly (should be `null` on a normal
   invoice, and non-null if you test with a deliberately mismatched or
   low-quality scan).

You can also use `curl` or the Swagger UI at `/docs` instead of the script.

## Project layout

```
extraction_service/
  app/
    main.py            FastAPI app, /extract and /health endpoints
    gemini_client.py    Gemini call + prompt, wrapped in error handling
    schema.py           Pydantic response schema
    validation.py       Total/line-item reconciliation check
    config.py            Env var config (GEMINI_API_KEY, GEMINI_MODEL)
  scripts/
    test_manual.py      CLI to POST a real invoice file and print the result
  tests/
    test_validation.py  Unit tests for the reconciliation logic
    test_api.py          API tests with the Gemini call mocked
```
