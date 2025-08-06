
import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app

@pytest.mark.asyncio
async def test_live_endpoint(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready_endpoint_success(client: AsyncClient):
    response = await client.get("/health/ready")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready_endpoint_failure(client: AsyncClient, monkeypatch):
    # Mock the database connection to raise an exception
    async def mock_execute(*args, **kwargs):
        raise Exception("Database connection failed")

    monkeypatch.setattr("sqlalchemy.ext.asyncio.AsyncSession.execute", mock_execute)

    response = await client.get("/health/ready")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
