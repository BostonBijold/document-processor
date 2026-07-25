"""
End-to-end manual test for the Intake Service -- confirms the full chain:
file in -> Extraction -> Data storage -> retrievable back out.

Requires all three services running:
  - Extraction service (GEMINI_API_KEY configured)
  - Invoice Data service (MONGODB_URI configured)
  - Intake service itself (EXTRACTION_SERVICE_URL / DATA_SERVICE_URL pointed
    at wherever the two above are actually running)

Usage:
    python scripts/test_manual.py "C:\\path\\to\\invoice1.pdf" "C:\\path\\to\\invoice2.png"
    python scripts/test_manual.py invoice1.pdf --intake-url http://localhost:8002 --data-url http://localhost:8001
"""

import argparse
import mimetypes
import sys

import httpx


def upload_one(client, intake_url, path):
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type is None:
        print(f"  could not guess MIME type for {path}", file=sys.stderr)
        return None

    with open(path, "rb") as f:
        files = {"file": (path, f, mime_type)}
        resp = client.post(f"{intake_url}/upload", files=files)

    print(f"  POST /upload -> {resp.status_code}")
    try:
        return resp.status_code, resp.json()
    except ValueError:
        print(f"  non-JSON response: {resp.text}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Upload real invoices through the Intake service and confirm the full chain works."
    )
    parser.add_argument("files", nargs="+", help="Paths to invoice files (PDF/JPG/PNG)")
    parser.add_argument("--intake-url", default="http://localhost:8002")
    parser.add_argument("--data-url", default="http://localhost:8001")
    args = parser.parse_args()

    passed = 0
    with httpx.Client(timeout=90) as client:
        for path in args.files:
            print(f"\n== {path} ==")
            result = upload_one(client, args.intake_url, path)
            if result is None:
                continue
            status_code, body = result

            if status_code != 201 or body.get("status") != "stored":
                print(f"  NOT STORED: {body}")
                continue

            invoice = body["invoice"]
            invoice_id = invoice["id"]
            warning = body.get("warning")
            print(f"  stored as {invoice_id}  vendor={invoice['vendor_name']}  total={invoice['total']}")
            if warning:
                print(f"  validation_warning: {warning}")

            verify = client.get(f"{args.data_url}/invoices/{invoice_id}")
            if verify.status_code == 200 and verify.json().get("id") == invoice_id:
                print(f"  confirmed retrievable via Data service GET /invoices/{invoice_id}")
                passed += 1
            else:
                print(f"  COULD NOT VERIFY via Data service: {verify.status_code} {verify.text}")

    print(f"\n{passed}/{len(args.files)} file(s) made it through the full chain successfully.")


if __name__ == "__main__":
    main()
