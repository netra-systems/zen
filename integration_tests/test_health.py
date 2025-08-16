import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock
from app.dependencies import get_db_dependency

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
    assert response.json() == {"status": "healthy", "service": "netra-ai-platform"}

def test_ready_endpoint_success(client: TestClient):
    import asyncio
    from unittest.mock import AsyncMock
    
    # Mock successful database connection
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 1
    
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    
    async def mock_get_db_success():
        return mock_session
    
    app.dependency_overrides[get_db_dependency] = mock_get_db_success
    
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "netra-ai-platform"}

def test_ready_endpoint_db_failure(client: TestClient):
    import os
    from unittest.mock import AsyncMock
    
    # Ensure DATABASE_URL doesn't contain "mock" which would skip the check
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
    
    try:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB connection failed")

        async def mock_get_db_failure():
            return mock_session

        app.dependency_overrides[get_db_dependency] = mock_get_db_failure
        
        response = client.get("/health/ready")
        assert response.status_code == 503
        
        # Check that the response contains expected error fields
        response_data = response.json()
        assert response_data["error"] == True
        assert response_data["error_code"] == "SERVICE_UNAVAILABLE"
        assert response_data["message"] == "Service Unavailable"
    finally:
        # Restore original value
        if original_db_url is not None:
            os.environ["DATABASE_URL"] = original_db_url
        else:
            os.environ.pop("DATABASE_URL", None)

def test_ready_endpoint_clickhouse_failure(client: TestClient):
    from contextlib import asynccontextmanager
    import os
    
    # Temporarily allow ClickHouse check for this test
    original_skip_clickhouse = os.environ.get("SKIP_CLICKHOUSE_INIT")
    os.environ["SKIP_CLICKHOUSE_INIT"] = "false"
    
    try:
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("ClickHouse connection failed")
        
        @asynccontextmanager
        async def mock_get_clickhouse_client():
            yield mock_client
        
        with patch("app.db.clickhouse.get_clickhouse_client", mock_get_clickhouse_client):
            response = client.get("/health/ready")
            assert response.status_code == 503
            
            # Check that the response contains error information
            response_data = response.json()
            assert response_data["error"] == True
            assert response_data["error_code"] == "SERVICE_UNAVAILABLE"
            assert response_data["message"] == "Service Unavailable"
    finally:
        # Restore original value
        if original_skip_clickhouse is not None:
            os.environ["SKIP_CLICKHOUSE_INIT"] = original_skip_clickhouse
        else:
            os.environ.pop("SKIP_CLICKHOUSE_INIT", None)