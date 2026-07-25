import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import ConfigError
from .gemini_client import GeminiExtractionError, extract_raw_json
from .schema import InvoiceExtraction
from .validation import check_totals

logger = logging.getLogger("extraction_service")

app = FastAPI(title="Extraction Service", version="0.1.0")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            ),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        raw_json = extract_raw_json(file_bytes, file.content_type)
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except GeminiExtractionError as exc:
        logger.warning("Extraction failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}") from exc

    try:
        result = InvoiceExtraction(**raw_json)
    except ValidationError as exc:
        logger.warning("Gemini output did not match schema: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Extracted data did not match the expected schema: {exc}",
        ) from exc

    result.validation_warning = check_totals(result)

    return JSONResponse(content=result.model_dump())
