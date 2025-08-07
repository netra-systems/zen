from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.db.models_postgres import User
from app.services.security_service import security_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
@patch("app.services.security_service.verify_password", new_callable=AsyncMock)
@patch("app.services.security_service.get_user", new_callable=AsyncMock)
async def test_login_for_access_token(mock_get_user, mock_verify_password, client):
    mock_get_user.return_value = User(email="test@example.com", hashed_password="hashed_password")
    mock_verify_password.return_value = True

    response = client.post("/api/v3/auth/token", data={"username": "test@example.com", "password": "testpassword"})

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"