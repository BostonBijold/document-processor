from app.schema import InvoiceExtraction, LineItem
from app.validation import check_totals


def make_invoice(**overrides):
    defaults = dict(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        issue_date="2026-01-01",
        due_date=None,
        line_items=[
            LineItem(description="Widget", quantity=2, unit_price=10.0, amount=20.0),
            LineItem(description="Gadget", quantity=1, unit_price=5.0, amount=5.0),
        ],
        subtotal=25.0,
        tax=2.5,
        total=27.5,
        currency="USD",
    )
    defaults.update(overrides)
    return InvoiceExtraction(**defaults)


def test_matching_totals_no_warning():
    invoice = make_invoice()
    assert check_totals(invoice) is None


def test_mismatched_total_produces_warning():
    invoice = make_invoice(total=100.0)
    warning = check_totals(invoice)
    assert warning is not None
    assert "does not match" in warning


def test_no_line_items_skips_check():
    # Nothing to reconcile against -- shouldn't guess or false-flag.
    invoice = make_invoice(line_items=[], total=999.0)
    assert check_totals(invoice) is None


def test_subtotal_mismatch_produces_warning():
    invoice = make_invoice(subtotal=999.0, tax=2.5, total=27.5)
    warning = check_totals(invoice)
    assert warning is not None
    assert "subtotal" in warning.lower()


def test_small_rounding_difference_is_tolerated():
    invoice = make_invoice(total=27.51)
    assert check_totals(invoice) is None
