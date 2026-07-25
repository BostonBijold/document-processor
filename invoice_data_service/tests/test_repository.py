from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from app import repository
from app.schema import ExtractionInput, StatusUpdate


@pytest.fixture
def collection():
    return mongomock.MongoClient()["test_db"]["invoices"]


def make_extraction(**overrides):
    defaults = dict(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        issue_date="2026-07-01",
        due_date="2026-12-01",
        line_items=[{"description": "Widget", "quantity": 2, "unit_price": 10.0, "amount": 20.0}],
        subtotal=20.0,
        tax=0.0,
        total=20.0,
        currency="USD",
        validation_warning=None,
    )
    defaults.update(overrides)
    return ExtractionInput(**defaults)


def test_insert_and_get(collection):
    created = repository.insert_invoice(collection, make_extraction(), b"filebytes", "application/pdf")
    assert created["status"] == "unpaid"
    assert created["document_content_type"] == "application/pdf"

    fetched = repository.get_invoice(collection, created["id"])
    assert fetched["vendor_name"] == "Acme Corp"


def test_get_invalid_id_raises(collection):
    with pytest.raises(repository.InvalidIdError):
        repository.get_invoice(collection, "not-an-object-id")


def test_get_missing_id_raises(collection):
    with pytest.raises(repository.InvoiceNotFoundError):
        repository.get_invoice(collection, "0" * 24)


def test_overdue_is_computed_not_stored(collection):
    past_due = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    created = repository.insert_invoice(
        collection, make_extraction(due_date=past_due), b"x", "application/pdf"
    )
    assert created["status"] == "overdue"

    raw = collection.find_one({"_id": collection.find_one({})["_id"]})
    assert raw["status"] == "unpaid"  # stored value never becomes "overdue"


def test_paid_invoice_never_shows_overdue(collection):
    past_due = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    created = repository.insert_invoice(
        collection, make_extraction(due_date=past_due), b"x", "application/pdf"
    )
    updated = repository.update_status(collection, created["id"], StatusUpdate(status="paid"))
    assert updated["status"] == "paid"
    assert updated["paid_date"] is not None


def test_update_status_back_to_unpaid_clears_paid_date(collection):
    created = repository.insert_invoice(collection, make_extraction(), b"x", "application/pdf")
    repository.update_status(collection, created["id"], StatusUpdate(status="paid"))
    reverted = repository.update_status(collection, created["id"], StatusUpdate(status="unpaid"))
    assert reverted["status"] == "unpaid"
    assert reverted["paid_date"] is None


def test_delete_then_get_raises_not_found(collection):
    created = repository.insert_invoice(collection, make_extraction(), b"x", "application/pdf")
    repository.delete_invoice(collection, created["id"])
    with pytest.raises(repository.InvoiceNotFoundError):
        repository.get_invoice(collection, created["id"])


def test_delete_missing_raises_not_found(collection):
    with pytest.raises(repository.InvoiceNotFoundError):
        repository.delete_invoice(collection, "0" * 24)


def test_list_filters_by_status_overdue(collection):
    past_due = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    future_due = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    repository.insert_invoice(collection, make_extraction(due_date=past_due), b"x", "application/pdf")
    repository.insert_invoice(collection, make_extraction(due_date=future_due), b"x", "application/pdf")

    items, total = repository.list_invoices(collection, status="overdue")
    assert total == 1
    assert items[0]["status"] == "overdue"


def test_list_filters_by_vendor_name_case_insensitive(collection):
    repository.insert_invoice(collection, make_extraction(vendor_name="Zylker Electronics"), b"x", "application/pdf")
    repository.insert_invoice(collection, make_extraction(vendor_name="Northwind Traders"), b"x", "application/pdf")

    items, total = repository.list_invoices(collection, vendor_name="zylker")
    assert total == 1
    assert items[0]["vendor_name"] == "Zylker Electronics"


def test_list_pagination(collection):
    for i in range(5):
        repository.insert_invoice(
            collection, make_extraction(invoice_number=f"INV-{i}"), b"x", "application/pdf"
        )
    items, total = repository.list_invoices(collection, skip=0, limit=2)
    assert total == 5
    assert len(items) == 2
