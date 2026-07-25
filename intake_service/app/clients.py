import json

import httpx

from .config import DATA_SERVICE_URL, EXTRACTION_SERVICE_URL

TIMEOUT = 60.0


class ExtractionServiceError(RuntimeError):
    """The Extraction service was unreachable or returned an error."""


class DataServiceError(RuntimeError):
    """The Data service was unreachable or returned an error."""


class DataServiceValidationError(DataServiceError):
    """The Data service rejected the payload as invalid (its 400 response)."""


def _response_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        return body.get("detail", resp.text)
    except ValueError:
        return resp.text


async def extract_invoice(file_bytes: bytes, content_type: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{EXTRACTION_SERVICE_URL}/extract",
                files={"file": ("upload", file_bytes, content_type)},
            )
    except httpx.HTTPError as exc:
        raise ExtractionServiceError(f"Could not reach the Extraction service: {exc}") from exc

    if resp.status_code != 200:
        raise ExtractionServiceError(
            f"Extraction service returned {resp.status_code}: {_response_detail(resp)}"
        )

    return resp.json()


async def create_invoice(extracted: dict, file_bytes: bytes, content_type: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{DATA_SERVICE_URL}/invoices",
                data={"data": json.dumps(extracted)},
                files={"file": ("upload", file_bytes, content_type)},
            )
    except httpx.HTTPError as exc:
        raise DataServiceError(f"Could not reach the Data service: {exc}") from exc

    if resp.status_code == 400:
        raise DataServiceValidationError(
            f"Data service rejected the extracted invoice: {_response_detail(resp)}"
        )
    if resp.status_code >= 400:
        raise DataServiceError(f"Data service returned {resp.status_code}: {_response_detail(resp)}")

    return resp.json()
