"""Sample invoices shaped like the Extraction service's output.

The third one has a due_date in the past on purpose, so the smoke test
can confirm the overdue-on-read logic actually fires.
"""

SAMPLE_INVOICES = [
    {
        "vendor_name": "Zylker Electronics Hub",
        "invoice_number": "INV-000001",
        "issue_date": "2024-08-05",
        "due_date": "2024-08-05",
        "line_items": [
            {"description": "Camera - DSLR camera", "quantity": 1, "unit_price": 899.0, "amount": 899.0},
            {"description": "Fitness Tracker", "quantity": 1, "unit_price": 129.0, "amount": 129.0},
            {"description": "Laptop", "quantity": 1, "unit_price": 1199.0, "amount": 1199.0},
        ],
        "subtotal": 2227.0,
        "tax": 111.35,
        "total": 2338.35,
        "currency": "USD",
        "validation_warning": None,
    },
    {
        "vendor_name": "Northwind Traders",
        "invoice_number": "NW-4521",
        "issue_date": "2026-06-15",
        "due_date": "2026-08-14",
        "line_items": [
            {"description": "Consulting services", "quantity": 10, "unit_price": 150.0, "amount": 1500.0},
        ],
        "subtotal": 1500.0,
        "tax": 0.0,
        "total": 1500.0,
        "currency": "USD",
        "validation_warning": None,
    },
    {
        "vendor_name": "Acme Supply Co",
        "invoice_number": "ACME-0099",
        "issue_date": "2025-11-01",
        "due_date": "2025-12-01",
        "line_items": [
            {"description": "Office chairs", "quantity": 4, "unit_price": 220.0, "amount": 880.0},
            {"description": "Desks", "quantity": 2, "unit_price": 450.0, "amount": 900.0},
        ],
        "subtotal": 1780.0,
        "tax": 89.0,
        "total": 1869.0,
        "currency": "USD",
        "validation_warning": None,
    },
]
