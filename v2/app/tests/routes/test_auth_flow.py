import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

@pytest.mark.asyncio
async def test_login_redirect_in_production():
    settings.environment = "production"
    with TestClient(app) as client:
        response = client.get("/api/v3/auth/login", follow_redirects=False)
        assert response.status_code == 302
    settings.environment = "development"
