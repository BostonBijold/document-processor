from typing import List, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: float


class InvoiceExtraction(BaseModel):
    vendor_name: str
    invoice_number: str
    issue_date: str
    due_date: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    currency: Optional[str] = None
    validation_warning: Optional[str] = None
