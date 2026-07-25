"""
Manual accuracy-check script for the Extraction Service.

Run the service first:
    uvicorn app.main:app --reload

Then, for each real sample invoice you want to check:
    python scripts/test_manual.py path/to/invoice.pdf
    python scripts/test_manual.py path/to/invoice.jpg --url http://localhost:8000/extract

Eyeball the printed JSON against the source document -- check vendor name,
invoice number, dates, line items, and totals. A non-null
"validation_warning" means the extracted line items/tax didn't reconcile
with the extracted total; that's worth checking by hand too.
"""

import argparse
import json
import mimetypes
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(
        description="Send an invoice file to the Extraction Service and print the result."
    )
    parser.add_argument("file", help="Path to an invoice image or PDF")
    parser.add_argument(
        "--url", default="http://localhost:8000/extract", help="Extraction service URL"
    )
    args = parser.parse_args()

    mime_type, _ = mimetypes.guess_type(args.file)
    if mime_type is None:
        print(f"Could not guess MIME type for {args.file}", file=sys.stderr)
        sys.exit(1)

    with open(args.file, "rb") as f:
        files = {"file": (args.file, f, mime_type)}
        response = httpx.post(args.url, files=files, timeout=60)

    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)


if __name__ == "__main__":
    main()
