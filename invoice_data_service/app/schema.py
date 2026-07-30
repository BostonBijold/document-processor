from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: float


class ExtractionInput(BaseModel):
    """Matches the Extraction service's output schema (the POST /invoices body)."""

    vendor_name: str
    invoice_number: str
    issue_date: datetime
    due_date: Optional[datetime] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    currency: Optional[str] = None
    validation_warning: Optional[str] = None


class InvoiceOut(BaseModel):
    id: str
    vendor_name: str
    invoice_number: str
    issue_date: datetime
    due_date: Optional[datetime] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    currency: Optional[str] = None
    validation_warning: Optional[str] = None
    status: Literal["unpaid", "paid", "overdue"]
    paid_date: Optional[datetime] = None
    document_content_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InvoiceListOut(BaseModel):
    items: List[InvoiceOut]
    total: int
    skip: int
    limit: int


class StatusUpdate(BaseModel):
    status: Literal["unpaid", "paid"]
    paid_date: Optional[datetime] = None


class InvoiceFieldsUpdate(BaseModel):
    """Body for PATCH /invoices/{id} -- editing the extracted fields.

    Not partial: the frontend's edit form always submits every field
    together, so this mirrors ExtractionInput rather than making everything
    optional. status/paid_date go through PATCH /invoices/{id}/status instead.
    """

    vendor_name: str
    invoice_number: str
    issue_date: datetime
    due_date: Optional[datetime] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    currency: Optional[str] = None
