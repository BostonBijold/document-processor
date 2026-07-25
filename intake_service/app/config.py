import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env.local")
load_dotenv(_ROOT / ".env")

EXTRACTION_SERVICE_URL = os.environ.get("EXTRACTION_SERVICE_URL", "http://localhost:8000").rstrip("/")
DATA_SERVICE_URL = os.environ.get("DATA_SERVICE_URL", "http://localhost:8001").rstrip("/")
