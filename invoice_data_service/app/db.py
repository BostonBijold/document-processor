from pymongo import MongoClient
from pymongo.collection import Collection

from .config import MONGODB_DB_NAME, MONGODB_URI

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client


def get_invoices_collection() -> Collection:
    """FastAPI dependency -- overridden with a mongomock collection in tests."""
    return get_client()[MONGODB_DB_NAME]["invoices"]
