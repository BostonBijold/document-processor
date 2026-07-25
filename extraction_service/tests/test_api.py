import io
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.gemini_client import GeminiExtractionError
from app.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-001",
    "issue_date": "2026-01-01",
    "due_date": None,
    "line_items": [
        {"description": "Widget", "quantity": 2, "unit_price": 10.0, "amount": 20.0}
    ],
    "subtotal": 20.0,
    "tax": 0.0,
    "total": 20.0,
    "currency": "USD",
}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_extract_rejects_unsupported_mime_type():
    resp = client.post(
        "/extract",
        files={"file": ("invoice.txt", io.BytesIO(b"not an invoice"), "text/plain")},
    )
    assert resp.status_code == 400


def test_extract_rejects_empty_file():
    resp = client.post(
        "/extract",
        files={"file": ("invoice.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert resp.status_code == 400


@patch("app.main.extract_raw_json")
def test_extract_success(mock_extract):
    mock_extract.return_value = VALID_PAYLOAD
    resp = client.post(
        "/extract",
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["vendor_name"] == "Acme Corp"
    assert body["validation_warning"] is None


@patch("app.main.extract_raw_json")
def test_extract_flags_mismatched_total(mock_extract):
    mock_extract.return_value = {**VALID_PAYLOAD, "total": 500.0}
    resp = client.post(
        "/extract",
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert resp.status_code == 200
    assert resp.json()["validation_warning"] is not None


@patch("app.main.extract_raw_json", side_effect=GeminiExtractionError("upstream failure"))
def test_extract_handles_gemini_failure(mock_extract):
    resp = client.post(
        "/extract",
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert resp.status_code == 502


@patch("app.main.extract_raw_json")
def test_extract_handles_bad_schema(mock_extract):
    mock_extract.return_value = {"not": "a valid invoice payload"}
    resp = client.post(
        "/extract",
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert resp.status_code == 502
