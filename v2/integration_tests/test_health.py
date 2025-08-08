
import pytest
from httpx import AsyncClient
from app.main import app
from unittest.mock import patch, MagicMock

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
    with patch("app.routes.health.get_db", new_callable=MagicMock) as mock_get_db:
        mock_get_db.side_effect = Exception("DB connection failed")
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health/ready")
            assert response.status_code == 503
            assert response.json() == {"detail": "Service Unavailable"}
