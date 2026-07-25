"""
End-to-end smoke test for the Invoice Data Service.

Requires:
  - The service running: uvicorn app.main:app --reload
  - MONGODB_URI pointing at a real (or local) MongoDB instance

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --url http://localhost:8000

Inserts the sample invoices from sample_invoices.py, exercises every
endpoint (create, list, filter, get, patch status, delete), and cleans up
everything it created. Raises AssertionError on the first thing that
doesn't behave as expected.
"""

import argparse
import io
import json

import httpx

from sample_invoices import SAMPLE_INVOICES


def post_invoice(client, base_url, invoice):
    files = {"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake invoice binary"), "application/pdf")}
    data = {"data": json.dumps(invoice)}
    resp = client.post(f"{base_url}/invoices", data=data, files=files)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    created_ids = []
    with httpx.Client(timeout=30) as client:
        print("== Inserting sample invoices ==")
        for invoice in SAMPLE_INVOICES:
            created = post_invoice(client, args.url, invoice)
            created_ids.append(created["id"])
            print(f"  created {created['id']}  {created['vendor_name']!r}  status={created['status']}")
        assert len(created_ids) == len(SAMPLE_INVOICES)

        print("\n== GET /invoices (list all) ==")
        resp = client.get(f"{args.url}/invoices")
        resp.raise_for_status()
        listing = resp.json()
        print(f"  total={listing['total']}, returned={len(listing['items'])}")
        assert listing["total"] >= len(created_ids)

        print("\n== GET /invoices?status=overdue ==")
        resp = client.get(f"{args.url}/invoices", params={"status": "overdue"})
        resp.raise_for_status()
        overdue = resp.json()
        print(f"  {overdue['total']} overdue invoice(s)")
        for item in overdue["items"]:
            print(f"    {item['id']}  due {item['due_date']}  status={item['status']}")
        assert overdue["total"] >= 1  # the Acme Supply Co sample is overdue by design

        first_id = created_ids[0]
        print(f"\n== GET /invoices/{first_id} ==")
        resp = client.get(f"{args.url}/invoices/{first_id}")
        resp.raise_for_status()
        detail = resp.json()
        print(f"  vendor={detail['vendor_name']}  total={detail['total']}")

        print(f"\n== PATCH /invoices/{first_id}/status -> paid ==")
        resp = client.patch(f"{args.url}/invoices/{first_id}/status", json={"status": "paid"})
        resp.raise_for_status()
        updated = resp.json()
        print(f"  status={updated['status']}  paid_date={updated['paid_date']}")
        assert updated["status"] == "paid"
        assert updated["paid_date"] is not None

        print("\n== GET /invoices?vendor_name=... (filter) ==")
        vendor_fragment = SAMPLE_INVOICES[1]["vendor_name"].split()[0]
        resp = client.get(f"{args.url}/invoices", params={"vendor_name": vendor_fragment})
        resp.raise_for_status()
        matches = resp.json()
        print(f"  {matches['total']} match(es) for vendor filter {vendor_fragment!r}")
        assert matches["total"] >= 1

        print("\n== Non-existent id checks ==")
        resp = client.get(f"{args.url}/invoices/{'0' * 24}")
        assert resp.status_code == 404
        resp = client.get(f"{args.url}/invoices/not-a-valid-id")
        assert resp.status_code == 400
        print("  404 for well-formed missing id, 400 for malformed id -- both correct")

        print("\n== DELETE cleanup ==")
        for invoice_id in created_ids:
            resp = client.delete(f"{args.url}/invoices/{invoice_id}")
            resp.raise_for_status()
        for invoice_id in created_ids:
            resp = client.get(f"{args.url}/invoices/{invoice_id}")
            assert resp.status_code == 404
        print(f"  deleted {len(created_ids)} invoice(s), confirmed all now return 404")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
