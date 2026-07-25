import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import clients

logger = logging.getLogger("intake_service")

app = FastAPI(title="Intake Service", version="0.1.0")

# No auth yet (single-user local use, tracked as a known gap) -- wildcard
# CORS lets the local frontend call this service directly from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
            ),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extracted = await clients.extract_invoice(file_bytes, file.content_type)
    except clients.ExtractionServiceError as exc:
        logger.error("Extraction failed: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"status": "extraction_failed", "detail": str(exc)},
        )

    try:
        stored = await clients.create_invoice(extracted, file_bytes, file.content_type)
    except clients.DataServiceValidationError as exc:
        # Extraction succeeded but the Data service rejected the payload --
        # don't lose it: log it and hand it straight back to the caller too.
        logger.error("Storage rejected the extracted payload: %s | payload=%r", exc, extracted)
        return JSONResponse(
            status_code=400,
            content={"status": "storage_failed", "detail": str(exc), "extracted_data": extracted},
        )
    except clients.DataServiceError as exc:
        logger.error("Storage failed: %s | payload=%r", exc, extracted)
        return JSONResponse(
            status_code=502,
            content={"status": "storage_failed", "detail": str(exc), "extracted_data": extracted},
        )

    return JSONResponse(
        status_code=201,
        content={
            "status": "stored",
            "invoice": stored,
            "warning": extracted.get("validation_warning"),
        },
    )
