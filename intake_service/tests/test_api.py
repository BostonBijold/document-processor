import io
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app import clients
from app.main import app

client = TestClient(app)

EXTRACTED = {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-001",
    "issue_date": "2026-07-01",
    "due_date": "2026-12-01",
    "line_items": [{"description": "Widget", "quantity": 2, "unit_price": 10.0, "amount": 20.0}],
    "subtotal": 20.0,
    "tax": 0.0,
    "total": 20.0,
    "currency": "USD",
    "validation_warning": None,
}

STORED = {
    "id": "0" * 24,
    **EXTRACTED,
    "status": "unpaid",
    "paid_date": None,
    "document_content_type": "application/pdf",
    "created_at": "2026-07-25T00:00:00",
    "updated_at": "2026-07-25T00:00:00",
}


def upload_pdf():
    return client.post(
        "/upload",
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_upload_rejects_unsupported_content_type():
    resp = client.post(
        "/upload",
        files={"file": ("invoice.txt", io.BytesIO(b"not an invoice"), "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_rejects_empty_file():
    resp = client.post(
        "/upload",
        files={"file": ("invoice.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert resp.status_code == 400


@patch("app.clients.create_invoice", new_callable=AsyncMock)
@patch("app.clients.extract_invoice", new_callable=AsyncMock)
def test_upload_success_no_warning(mock_extract, mock_create):
    mock_extract.return_value = EXTRACTED
    mock_create.return_value = STORED

    resp = upload_pdf()
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "stored"
    assert body["invoice"]["id"] == "0" * 24
    assert body["warning"] is None


@patch("app.clients.create_invoice", new_callable=AsyncMock)
@patch("app.clients.extract_invoice", new_callable=AsyncMock)
def test_upload_surfaces_validation_warning(mock_extract, mock_create):
    warned = {**EXTRACTED, "validation_warning": "totals don't reconcile"}
    mock_extract.return_value = warned
    mock_create.return_value = {**STORED, "validation_warning": "totals don't reconcile"}

    resp = upload_pdf()
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "stored"
    assert body["warning"] == "totals don't reconcile"


@patch("app.clients.extract_invoice", new_callable=AsyncMock)
def test_upload_extraction_service_unreachable(mock_extract):
    mock_extract.side_effect = clients.ExtractionServiceError("Could not reach the Extraction service")

    resp = upload_pdf()
    assert resp.status_code == 502
    body = resp.json()
    assert body["status"] == "extraction_failed"


@patch("app.clients.create_invoice", new_callable=AsyncMock)
@patch("app.clients.extract_invoice", new_callable=AsyncMock)
def test_upload_storage_validation_error_keeps_extracted_data(mock_extract, mock_create):
    mock_extract.return_value = EXTRACTED
    mock_create.side_effect = clients.DataServiceValidationError("missing required field 'total'")

    resp = upload_pdf()
    assert resp.status_code == 400
    body = resp.json()
    assert body["status"] == "storage_failed"
    assert body["extracted_data"] == EXTRACTED


@patch("app.clients.create_invoice", new_callable=AsyncMock)
@patch("app.clients.extract_invoice", new_callable=AsyncMock)
def test_upload_storage_unreachable_returns_502(mock_extract, mock_create):
    mock_extract.return_value = EXTRACTED
    mock_create.side_effect = clients.DataServiceError("Could not reach the Data service")

    resp = upload_pdf()
    assert resp.status_code == 502
    body = resp.json()
    assert body["status"] == "storage_failed"
    assert body["extracted_data"] == EXTRACTED
