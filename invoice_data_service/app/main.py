import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from . import repository
from .db import get_invoices_collection
from .schema import ExtractionInput, InvoiceListOut, InvoiceOut, StatusUpdate

logger = logging.getLogger("invoice_data_service")

app = FastAPI(title="Invoice Data Service", version="0.1.0")

# No auth yet (single-user local use, tracked as a known gap) -- wildcard
# CORS lets the local frontend call this service directly from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PyMongoError)
async def handle_mongo_error(request, exc: PyMongoError):
    logger.error("MongoDB error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": f"Database unavailable: {exc}"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(
    data: str = Form(
        ..., description="JSON string matching the Extraction service's output schema"
    ),
    file: UploadFile = File(...),
    collection: Collection = Depends(get_invoices_collection),
):
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"'data' is not valid JSON: {exc}") from exc

    try:
        extraction = ExtractionInput(**parsed)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid invoice data: {exc}") from exc

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded document is empty.")

    return repository.insert_invoice(
        collection, extraction, file_bytes, file.content_type or "application/octet-stream"
    )


@app.get("/invoices", response_model=InvoiceListOut)
def list_invoices(
    vendor_name: Optional[str] = None,
    status: Optional[str] = Query(None, pattern="^(unpaid|paid|overdue)$"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    collection: Collection = Depends(get_invoices_collection),
):
    items, total = repository.list_invoices(
        collection,
        vendor_name=vendor_name,
        status=status,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@app.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, collection: Collection = Depends(get_invoices_collection)):
    try:
        return repository.get_invoice(collection, invoice_id)
    except repository.InvalidIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except repository.InvoiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' not found.") from exc


@app.patch("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: str,
    update: StatusUpdate,
    collection: Collection = Depends(get_invoices_collection),
):
    try:
        return repository.update_status(collection, invoice_id, update)
    except repository.InvalidIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except repository.InvoiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' not found.") from exc


@app.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: str, collection: Collection = Depends(get_invoices_collection)):
    try:
        repository.delete_invoice(collection, invoice_id)
    except repository.InvalidIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except repository.InvoiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' not found.") from exc
    return Response(status_code=204)
