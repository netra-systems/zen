import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.asyncio
async def test_live_endpoint():
    """
    Tests the /live endpoint.
    """
    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready_endpoint_success(mocker):
    """
    Tests the /ready endpoint when all services are healthy.
    """
    mocker.patch("app.db.clickhouse_base.ClickHouseDatabase.ping", return_value=True)
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready_endpoint_failure(mocker):
    """
    Tests the /ready endpoint when a service is unhealthy.
    """
    mocker.patch("app.db.clickhouse_base.ClickHouseDatabase.ping", return_value=False)
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Service Unavailable"}