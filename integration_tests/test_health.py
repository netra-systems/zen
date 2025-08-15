import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock
from app.db.postgres import get_async_db

# Set testing flags to simplify startup
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SKIP_STARTUP_CHECKS"] = "true"
os.environ["SKIP_CLICKHOUSE_INIT"] = "true"

@pytest.fixture(scope="function")
def client():
    """Test client fixture."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """Fixture to clean up dependency overrides after each test."""
    original_overrides = app.dependency_overrides.copy()
    yield
    app.dependency_overrides = original_overrides

def test_live_endpoint(client: TestClient):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready_endpoint_success(client: TestClient):
    # Mock successful database connection
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 1
    
    mock_session = MagicMock()
    mock_session.execute.return_value = mock_result
    
    async def mock_get_db_success():
        yield mock_session
    
    app.dependency_overrides[get_async_db] = mock_get_db_success
    
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready_endpoint_db_failure(client: TestClient):
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("DB connection failed")

    async def mock_get_db_failure():
        return mock_session

    app.dependency_overrides[get_async_db] = mock_get_db_failure

    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Service Unavailable"}

def test_ready_endpoint_clickhouse_failure(client: TestClient):
    from contextlib import asynccontextmanager
    
    mock_client = MagicMock()
    mock_client.ping.side_effect = Exception("ClickHouse connection failed")
    
    @asynccontextmanager
    async def mock_get_clickhouse_client():
        yield mock_client
    
    with patch("app.db.clickhouse.get_clickhouse_client", mock_get_clickhouse_client):
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Service Unavailable"}