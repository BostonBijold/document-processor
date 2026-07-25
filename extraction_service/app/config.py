import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env.local")
load_dotenv(_ROOT / ".env")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def get_gemini_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ConfigError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a key from Google AI Studio (https://aistudio.google.com/apikey) "
            "and set it before starting the service."
        )
    return api_key


GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
