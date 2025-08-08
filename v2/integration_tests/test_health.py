
import pytest
from httpx import AsyncClient
from app.main import app
from unittest.mock import patch, MagicMock
from app.db.postgres import get_async_db

@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """Fixture to clean up dependency overrides after each test."""
    original_overrides = app.dependency_overrides.copy()
    yield
    app.dependency_overrides = original_overrides

@pytest.mark.asyncio
async def test_live_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready_endpoint_success():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready_endpoint_db_failure():
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("DB connection failed")

    async def mock_get_db_failure():
        return mock_session

    app.dependency_overrides[get_async_db] = mock_get_db_failure

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Service Unavailable"}

@pytest.mark.asyncio
async def test_ready_endpoint_clickhouse_failure():
    with patch("app.routes.health.central_logger.clickhouse_db.ping", return_value=False):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health/ready")
            assert response.status_code == 503
            assert response.json() == {"detail": "Service Unavailable"}
