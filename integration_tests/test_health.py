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
    
    # Test enhanced enterprise health response
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "netra-ai-platform"
    
    # Validate enterprise monitoring fields
    assert "version" in data
    assert "timestamp" in data
    assert "environment" in data
    
    # Type validation for business value
    assert isinstance(data["version"], str)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["environment"], str)

def test_ready_endpoint_success(client: TestClient):
    import asyncio
    from unittest.mock import AsyncMock, patch
    
    # Mock successful database connection
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 1
    
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    
    async def mock_get_db_success():
        return mock_session
    
    app.dependency_overrides[get_db_dependency] = mock_get_db_success
    
    # Mock all health checkers to return healthy status
    with patch("app.core.health.interface.HealthInterface.get_health_status") as mock_health:
        mock_health.return_value = {
            "status": "ready",
            "service": "netra-ai-platform", 
            "version": "1.0.0",
            "timestamp": "2025-01-01T00:00:00Z",
            "checks": {
                "database_postgres": True,
                "database_clickhouse": True,
                "database_redis": True,
                "dependency_websocket": True,
                "dependency_llm": True
            },
            "details": {}
        }
        
        response = client.get("/health/ready")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "ready"
        assert response_data["service"] == "netra-ai-platform"
        assert "details" in response_data  # Accept the details field

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
    from app.core.health_types import HealthStatus
    
    mock_client = MagicMock()
    mock_client.execute.side_effect = Exception("ClickHouse connection failed")
    
    @asynccontextmanager
    async def mock_get_clickhouse_client():
        yield mock_client
    
    # Mock the health interface to return an unhealthy status directly
    with patch("app.db.clickhouse.get_clickhouse_client", mock_get_clickhouse_client), \
         patch("app.core.health.interface.HealthInterface.get_health_status") as mock_health_status:
        
        # Mock the health status to return unhealthy for this test
        mock_health_status.return_value = {
            "status": HealthStatus.UNHEALTHY.value,
            "service": "netra-ai-platform",
            "version": "1.0.0",
            "uptime_seconds": 100,
            "checks": {"database_clickhouse": False},
            "timestamp": "2025-01-01T00:00:00Z"
        }
        
        response = client.get("/health/ready")
        assert response.status_code == 503
        
        # Check that the response contains error information
        response_data = response.json()
        assert response_data["error"] == True
        assert response_data["error_code"] == "SERVICE_UNAVAILABLE"
        assert response_data["message"] == "Service Unavailable"