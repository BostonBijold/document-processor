# Frontend

Plain HTML/CSS/vanilla JS, no build step, no framework. A single page, thin
client over the existing Intake and Data service APIs -- no business logic
lives here (no total-reconciliation, no status derivation; it just renders
what the backend already computed).

Layout: an "+ Upload invoice" button at the top, an accordion list of
invoices on the left (click a row to expand it inline into the full
extracted fields -- line items, subtotal/tax, validation warning, mark as
paid, edit), and a document preview panel on the right that loads the
original uploaded file (image or PDF) for whichever invoice is expanded --
so extracted fields can be checked against the source document, and
corrected in place if extraction got something wrong.

- `index.html` -- the page shell (header, filters, accordion container,
  preview panel container).
- `app.js` -- all page logic: upload flow, list loading + filters +
  pagination, accordion expand/collapse, document preview loading, mark as
  paid.
- `api.js` -- thin fetch wrappers for the Intake and Data services (incl.
  `getDocumentBlob` for the preview panel), plus small formatting/escaping
  helpers.
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

**Backend requirements:**
- Intake and Data need CORS enabled, since the browser calls them directly
  from this page's origin. Already wired up
  (`app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)`) in both
  `intake_service/app/main.py` and `invoice_data_service/app/main.py`. The
  Extraction service doesn't need this -- the frontend never calls it
  directly, only Intake does (server-to-server).
- The document preview panel calls `GET /invoices/{id}/document` on the
  Data service, which streams back the originally-uploaded file
  (`document_binary`) with its stored content type. Added specifically to
  support this panel -- previously the Data service never returned the raw
  file, only extracted fields.
- The Edit form saves via `PATCH /invoices/{id}` on the Data service, also
  added specifically for this -- previously the Data service could only
  update `status` (via `PATCH /invoices/{id}/status`), not the extracted
  fields themselves.

## How it works

- **Upload** (top button): picks a file, POSTs it to Intake. Shows a
  loading banner while extraction/storage runs, then a success/warning/error
  banner. On success, the list reloads and the new invoice's accordion row
  auto-expands -- so you immediately see the extracted fields next to the
  document preview for a quick sanity check.
- **Accordion list**: `GET /invoices` already returns every field per
  invoice (line items, totals, status, etc.), so expanding a row needs no
  extra API call -- only the document preview panel needs its own fetch.
  Filters (vendor substring, status) and pagination (skip/limit) work the
  same as before, just against the accordion instead of a table.
- **Preview panel**: on expand, fetches the document as a blob and renders
  an `<img>` for images or an `<iframe>` for PDFs (object URLs are revoked
  on selection change to avoid leaking memory). Falls back to a plain
  "open file" link for anything else.
- **Mark as paid**: updates just that one item in local state and
  re-renders, no full list reload.
- **Edit**: swaps the expanded detail section for a form with every field
  editable (vendor, invoice #, dates, currency, subtotal/tax/total, and the
  line items table with add/remove rows) right next to the still-visible
  document preview, so you can compare and correct in place. Save PATCHes
  the whole field set to the Data service, which recomputes
  `validation_warning` from the new totals (so fixing a bad total clears a
  stale warning). Cancel just re-renders from the last-loaded data,
  discarding whatever was typed. Uses one delegated click listener on the
  accordion container (not per-element listeners re-attached on every
  render) so dynamically added/removed line-item rows work without special
  handling, and Save reads current input values directly from the DOM at
  click time rather than tracking edits in JS state.

## Known gaps (v1, by design)

- **No auth.** Single-user local use only, as scoped for this sprint.
- **No pagination page-size control** -- fixed at 20 per page (Data
  service default), just Prev/Next.
- No delete from the UI (Data service supports `DELETE /invoices/{id}` for
  correcting bad test data, but that wasn't asked for here).
- Only one invoice can be expanded (and previewed/edited) at a time.
- No client-side validation on edit beyond "vendor/invoice#/issue
  date/total can't be empty" -- e.g. nothing stops a nonsensical date.

## Testing

No automated tests for a single static page with no build step and no
business logic to unit-test -- correctness here is "does it render what the
API returns," which is best checked by hand.

Manual walkthrough (needs Extraction, Data, and Intake all running, plus
this page served per above):

1. Click "+ Upload invoice", pick a real invoice file.
2. Confirm the loading banner shows, then a success (or warning/error)
   banner -- and that the new invoice's row appears at the top of the list,
   already expanded, with its extracted fields and document preview both
   visible.
3. Collapse it, then click it again; confirm it re-expands and the preview
   reloads correctly.
4. Filter by that vendor and by status; confirm it still shows up
   correctly filtered, and that changing filters clears the preview panel.
5. Click "Mark as paid" inside the expanded row; confirm the status chip
   updates to "paid" and the button is replaced by a paid-date note,
   without a page reload.
6. Click into a different invoice's row; confirm the previous one collapses
   and the preview panel swaps to the new document.
7. Click "Edit" on an invoice; confirm every field (including line items)
   becomes editable. Change a field, click "Save"; confirm it persists
   (re-expand the row, or reload the page, to check) and the accordion row
   and detail view reflect the new value immediately.
8. Edit a total to something that no longer reconciles with the line items
   and save; confirm the validation warning banner appears. Fix it back and
   save again; confirm the warning clears.
9. Enter Edit mode, change a field, click "Cancel"; confirm the change is
   discarded and the original value is shown.
