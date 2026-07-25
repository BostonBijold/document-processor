# Frontend

Plain HTML/CSS/vanilla JS, no build step, no framework. Three pages, each a
thin client over the existing Intake and Data service APIs -- no business
logic lives here (no total-reconciliation, no status derivation; the pages
just render what the backend already computed).

- `index.html` / `upload.js` -- **Upload**: pick a file, POST to Intake,
  show extracted fields on success.
- `invoices.html` / `list.js` -- **Invoice list**: calls Data's
  `GET /invoices`, filter by vendor/status, paginate, click through to detail.
- `invoice.html` / `detail.js` -- **Invoice detail**: calls Data's
  `GET /invoices/{id}`, shows all fields + line items, "Mark as paid" button
  (`PATCH /invoices/{id}/status`), prominent banner if `validation_warning`
  is set.
- `api.js` -- thin fetch wrappers for both services, plus small
  formatting/escaping helpers shared by all three pages.
- `config.js` -- **the only place service URLs are configured.**

## Setup

Edit `config.js`:
```js
window.APP_CONFIG = {
  INTAKE_URL: "http://localhost:8002",
  DATA_URL: "http://localhost:8001",
};
```
Point these at wherever your Intake and Data services are actually running.

## Run

No build step -- just serve the static files (opening `index.html` directly
via `file://` will NOT work; browsers block `fetch` calls made from a
`file://` page). From this directory:

```
python -m http.server 5500
```

Then open http://localhost:5500.

**Backend requirement:** since this page calls Intake and Data directly
from the browser, both of those services need CORS enabled to accept
requests from this origin. That's already wired up
(`app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)` in both
`intake_service/app/main.py` and `invoice_data_service/app/main.py`) -- wide
open, since there's no auth yet. The Extraction service doesn't need this;
the frontend never calls it directly, only Intake does (server-to-server).

## Known gaps (v1, by design)

- **No auth.** Single-user local use only, as scoped for this sprint.
- **No pagination page-size control** -- fixed at 20 per page (Data
  service default), just Prev/Next.
- No delete/edit from the UI (Data service supports `DELETE /invoices/{id}`
  for correcting bad test data, but that wasn't asked for here).

## Testing

No automated tests for a 3-page static site with no build step and no
business logic to unit-test -- correctness here is "does it render what
the API returns," which is best checked by hand.

Manual walkthrough (needs Extraction, Data, and Intake all running, plus
this page served per above):

1. Open the Upload page, pick a real invoice file, submit it.
2. Confirm the loading state shows, then the extracted fields (vendor,
   total, line items) appear on success -- or a clear error/warning if not.
3. Click through to the detail view (or navigate to Invoices).
4. Confirm the new invoice appears in the list with the right vendor,
   invoice number, date, total, and status.
5. Filter the list by that vendor and by status; confirm it still shows up
   correctly filtered.
6. Click into the detail view; confirm every field matches what was shown
   at upload time, including line items.
7. Click "Mark as paid"; confirm the status updates in place (chip changes
   to "paid", button is replaced with a paid-date note) without a page
   reload, and that revisiting the Invoices list reflects the new status too.
