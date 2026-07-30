import re
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.binary import Binary
from bson.errors import InvalidId
from pymongo.collection import Collection

from .schema import ExtractionInput, InvoiceFieldsUpdate, LineItem, StatusUpdate

# Same tolerance the Extraction service uses for its own totals sanity
# check -- duplicated here (not imported cross-service) so this service
# can recompute validation_warning after a manual edit without depending
# on Extraction's internals.
_TOLERANCE_ABS = 0.01
_TOLERANCE_REL = 0.01


def _within_tolerance(a: float, b: float) -> bool:
    diff = abs(a - b)
    threshold = max(_TOLERANCE_ABS, _TOLERANCE_REL * max(abs(a), abs(b)))
    return diff <= threshold


def _compute_validation_warning(
    line_items: list[LineItem], tax: Optional[float], subtotal: Optional[float], total: float
) -> Optional[str]:
    if not line_items:
        return None

    line_item_sum = sum(item.amount for item in line_items)
    tax_val = tax or 0.0
    expected_total = line_item_sum + tax_val

    if not _within_tolerance(expected_total, total):
        return (
            f"Sum of line items ({line_item_sum:.2f}) plus tax ({tax_val:.2f}) = "
            f"{expected_total:.2f}, which does not match the total ({total:.2f})."
        )

    if subtotal is not None and not _within_tolerance(subtotal, line_item_sum):
        return (
            f"Subtotal ({subtotal:.2f}) does not match the sum of line item "
            f"amounts ({line_item_sum:.2f})."
        )

    return None


class InvalidIdError(ValueError):
    pass


class InvoiceNotFoundError(LookupError):
    pass


def _parse_object_id(invoice_id: str) -> ObjectId:
    try:
        return ObjectId(invoice_id)
    except (InvalidId, TypeError) as exc:
        raise InvalidIdError(f"'{invoice_id}' is not a valid invoice id.") from exc


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Store everything as naive UTC so stored/computed datetimes compare cleanly."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_effective_status(stored_status: str, due_date: Optional[datetime]) -> str:
    """Overdue is computed at read time, never persisted.

    The stored 'status' field only ever holds 'unpaid' or 'paid'. A doc
    reads as 'overdue' when stored status is 'unpaid' and due_date has
    passed -- this function is the single source of truth for that.
    """
    if stored_status == "unpaid" and due_date is not None and due_date < _now():
        return "overdue"
    return stored_status


def _to_out_dict(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "vendor_name": doc["vendor_name"],
        "invoice_number": doc["invoice_number"],
        "issue_date": doc["issue_date"],
        "due_date": doc.get("due_date"),
        "line_items": doc.get("line_items", []),
        "subtotal": doc.get("subtotal"),
        "tax": doc.get("tax"),
        "total": doc["total"],
        "currency": doc.get("currency"),
        "validation_warning": doc.get("validation_warning"),
        "status": compute_effective_status(doc["status"], doc.get("due_date")),
        "paid_date": doc.get("paid_date"),
        "document_content_type": doc.get("document_content_type"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def insert_invoice(
    collection: Collection, data: ExtractionInput, file_bytes: bytes, content_type: str
) -> dict:
    now = _now()
    doc = {
        "vendor_name": data.vendor_name,
        "invoice_number": data.invoice_number,
        "issue_date": _to_naive_utc(data.issue_date),
        "due_date": _to_naive_utc(data.due_date),
        "line_items": [item.model_dump() for item in data.line_items],
        "subtotal": data.subtotal,
        "tax": data.tax,
        "total": data.total,
        "currency": data.currency,
        "validation_warning": data.validation_warning,
        "status": "unpaid",
        "paid_date": None,
        "document_binary": Binary(file_bytes),
        "document_content_type": content_type,
        "created_at": now,
        "updated_at": now,
    }
    result = collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out_dict(doc)


def get_invoice(collection: Collection, invoice_id: str) -> dict:
    oid = _parse_object_id(invoice_id)
    doc = collection.find_one({"_id": oid})
    if doc is None:
        raise InvoiceNotFoundError(invoice_id)
    return _to_out_dict(doc)


def update_fields(collection: Collection, invoice_id: str, data: InvoiceFieldsUpdate) -> dict:
    oid = _parse_object_id(invoice_id)
    if collection.find_one({"_id": oid}, {"_id": 1}) is None:
        raise InvoiceNotFoundError(invoice_id)

    warning = _compute_validation_warning(data.line_items, data.tax, data.subtotal, data.total)

    collection.update_one(
        {"_id": oid},
        {
            "$set": {
                "vendor_name": data.vendor_name,
                "invoice_number": data.invoice_number,
                "issue_date": _to_naive_utc(data.issue_date),
                "due_date": _to_naive_utc(data.due_date),
                "line_items": [item.model_dump() for item in data.line_items],
                "subtotal": data.subtotal,
                "tax": data.tax,
                "total": data.total,
                "currency": data.currency,
                "validation_warning": warning,
                "updated_at": _now(),
            }
        },
    )
    updated = collection.find_one({"_id": oid})
    return _to_out_dict(updated)


def get_document(collection: Collection, invoice_id: str) -> tuple[bytes, str]:
    oid = _parse_object_id(invoice_id)
    doc = collection.find_one({"_id": oid}, {"document_binary": 1, "document_content_type": 1})
    if doc is None:
        raise InvoiceNotFoundError(invoice_id)
    content_type = doc.get("document_content_type") or "application/octet-stream"
    return bytes(doc["document_binary"]), content_type


def list_invoices(
    collection: Collection,
    vendor_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[dict], int]:
    query: dict = {}

    if vendor_name:
        query["vendor_name"] = {"$regex": re.escape(vendor_name), "$options": "i"}

    if date_from or date_to:
        issue_date_query = {}
        if date_from:
            issue_date_query["$gte"] = _to_naive_utc(date_from)
        if date_to:
            issue_date_query["$lte"] = _to_naive_utc(date_to)
        query["issue_date"] = issue_date_query

    if status == "overdue":
        # Overdue isn't a stored value -- translate it into the underlying
        # condition (unpaid + due_date in the past) for filtering.
        query["status"] = "unpaid"
        query["due_date"] = {"$lt": _now()}
    elif status == "unpaid":
        # Explicitly exclude overdue ones so this filter matches the
        # effective status shown in responses, not just the raw stored value.
        query["status"] = "unpaid"
        query["$or"] = [{"due_date": None}, {"due_date": {"$gte": _now()}}]
    elif status == "paid":
        query["status"] = "paid"

    total = collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = [_to_out_dict(doc) for doc in cursor]
    return items, total


def update_status(collection: Collection, invoice_id: str, update: StatusUpdate) -> dict:
    oid = _parse_object_id(invoice_id)
    doc = collection.find_one({"_id": oid})
    if doc is None:
        raise InvoiceNotFoundError(invoice_id)

    if update.status == "paid":
        paid_date = _to_naive_utc(update.paid_date) or _now()
    else:
        paid_date = None

    collection.update_one(
        {"_id": oid},
        {"$set": {"status": update.status, "paid_date": paid_date, "updated_at": _now()}},
    )
    updated = collection.find_one({"_id": oid})
    return _to_out_dict(updated)


def delete_invoice(collection: Collection, invoice_id: str) -> None:
    oid = _parse_object_id(invoice_id)
    result = collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise InvoiceNotFoundError(invoice_id)
