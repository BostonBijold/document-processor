import io
import json

VALID_EXTRACTION = {
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


def post_invoice(api_client, payload=None):
    return api_client.post(
        "/invoices",
        data={"data": json.dumps(payload if payload is not None else VALID_EXTRACTION)},
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )


def test_health(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200


def test_create_invoice_defaults_to_unpaid(api_client):
    resp = post_invoice(api_client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "unpaid"
    assert body["vendor_name"] == "Acme Corp"
    assert "document_binary" not in body


def test_create_invoice_missing_required_field_returns_400(api_client):
    bad_payload = {**VALID_EXTRACTION}
    del bad_payload["total"]
    resp = post_invoice(api_client, bad_payload)
    assert resp.status_code == 400


def test_create_invoice_bad_json_returns_400(api_client):
    resp = api_client.post(
        "/invoices",
        data={"data": "{not valid json"},
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert resp.status_code == 400


def test_get_invoice_by_id(api_client):
    created = post_invoice(api_client).json()
    resp = api_client.get(f"/invoices/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["invoice_number"] == "INV-001"


def test_get_invoice_not_found_returns_404(api_client):
    resp = api_client.get(f"/invoices/{'0' * 24}")
    assert resp.status_code == 404


def test_get_invoice_bad_id_format_returns_400(api_client):
    resp = api_client.get("/invoices/not-an-id")
    assert resp.status_code == 400


def test_list_invoices(api_client):
    post_invoice(api_client)
    post_invoice(api_client, {**VALID_EXTRACTION, "vendor_name": "Other Vendor"})
    resp = api_client.get("/invoices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_invoices_filters_by_vendor(api_client):
    post_invoice(api_client)
    post_invoice(api_client, {**VALID_EXTRACTION, "vendor_name": "Other Vendor"})
    resp = api_client.get("/invoices", params={"vendor_name": "acme"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["vendor_name"] == "Acme Corp"


def test_list_invoices_pagination(api_client):
    for i in range(3):
        post_invoice(api_client, {**VALID_EXTRACTION, "invoice_number": f"INV-{i}"})
    resp = api_client.get("/invoices", params={"skip": 1, "limit": 1})
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1


def test_update_status_to_paid_sets_paid_date(api_client):
    created = post_invoice(api_client).json()
    resp = api_client.patch(f"/invoices/{created['id']}/status", json={"status": "paid"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "paid"
    assert body["paid_date"] is not None


def test_update_status_not_found_returns_404(api_client):
    resp = api_client.patch(f"/invoices/{'0' * 24}/status", json={"status": "paid"})
    assert resp.status_code == 404


def test_delete_invoice(api_client):
    created = post_invoice(api_client).json()
    resp = api_client.delete(f"/invoices/{created['id']}")
    assert resp.status_code == 204
    resp = api_client.get(f"/invoices/{created['id']}")
    assert resp.status_code == 404


def test_delete_not_found_returns_404(api_client):
    resp = api_client.delete(f"/invoices/{'0' * 24}")
    assert resp.status_code == 404


def test_overdue_invoice_computed_on_read(api_client):
    overdue_payload = {**VALID_EXTRACTION, "due_date": "2020-01-01"}
    created = post_invoice(api_client, overdue_payload).json()
    assert created["status"] == "overdue"

    resp = api_client.get("/invoices", params={"status": "overdue"})
    assert resp.json()["total"] == 1
