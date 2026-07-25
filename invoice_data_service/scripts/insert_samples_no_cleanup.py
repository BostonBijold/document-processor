"""One-off: insert the sample invoices and leave them in the database
(unlike smoke_test.py, which deletes what it creates). Use this to actually
see records land in MongoDB via Atlas's Collections view or a Mongo client.

Usage:
    python insert_samples_no_cleanup.py [--url http://localhost:8000]
"""

import argparse
import io
import json

import httpx

from sample_invoices import SAMPLE_INVOICES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    with httpx.Client(timeout=30) as client:
        for invoice in SAMPLE_INVOICES:
            files = {"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake invoice binary"), "application/pdf")}
            data = {"data": json.dumps(invoice)}
            resp = client.post(f"{args.url}/invoices", data=data, files=files)
            resp.raise_for_status()
            created = resp.json()
            print(f"created {created['id']}  {created['vendor_name']!r}  status={created['status']}")

    print("\nLeft in the database -- check Atlas's Collections view (accounts_payable.invoices),")
    print("or delete them later with DELETE /invoices/{id} if you want to clean up.")


if __name__ == "__main__":
    main()
