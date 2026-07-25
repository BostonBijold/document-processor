import json

from google import genai
from google.genai import types

from .config import GEMINI_MODEL, get_gemini_api_key

EXTRACTION_PROMPT = """You are an invoice data extraction engine. Read the attached \
invoice document (image or PDF) and extract the following fields.

Respond with ONLY a single JSON object. No markdown code fences, no preamble, \
no explanation, no trailing commentary -- your entire response must be valid JSON.

Rules:
- If a field cannot be found, use null (or an empty list for line_items).
- All monetary values must be plain numbers (no currency symbols, no thousands separators).
- Dates must be in ISO 8601 format (YYYY-MM-DD).
- "line_items" should reflect the individual line items printed on the invoice.

JSON schema to follow exactly:
{
  "vendor_name": string,
  "invoice_number": string,
  "issue_date": string (ISO 8601),
  "due_date": string (ISO 8601) | null,
  "line_items": [
    { "description": string, "quantity": number | null, "unit_price": number | null, "amount": number }
  ],
  "subtotal": number | null,
  "tax": number | null,
  "total": number,
  "currency": string | null
}
"""


class GeminiExtractionError(RuntimeError):
    """Raised when the Gemini call fails or returns unusable output."""


_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_gemini_api_key())
    return _client


def extract_raw_json(file_bytes: bytes, mime_type: str) -> dict:
    """Send the invoice file to Gemini and return the parsed JSON dict.

    Raises GeminiExtractionError on any API failure or unparsable response.
    """
    client = _get_client()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                EXTRACTION_PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    except Exception as exc:
        raise GeminiExtractionError(f"Gemini API call failed: {exc}") from exc

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise GeminiExtractionError("Gemini returned an empty response.")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiExtractionError(
            f"Gemini response was not valid JSON: {exc}. Raw response: {text[:500]}"
        ) from exc
