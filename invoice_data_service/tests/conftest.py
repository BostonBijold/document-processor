import mongomock
import pytest
from fastapi.testclient import TestClient

from app.db import get_invoices_collection
from app.main import app


@pytest.fixture
def collection():
    client = mongomock.MongoClient()
    return client["test_db"]["invoices"]


@pytest.fixture
def api_client(collection):
    app.dependency_overrides[get_invoices_collection] = lambda: collection
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
