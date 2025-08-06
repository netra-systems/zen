from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi.responses import RedirectResponse

from app.main import app
from app.services.security_service import SecurityService
from app.services.key_manager import KeyManager
from app.config import settings

client = TestClient(app)


@patch("app.routes.google_auth.oauth.google")
def test_google_auth(mock_google_oauth):
    # 1. Mock the Google OAuth flow
    mock_google_oauth.authorize_redirect = AsyncMock(
        return_value=RedirectResponse(url="https://accounts.google.com/o/oauth2/v2/auth", status_code=200)
    )
    mock_google_oauth.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/avatar.png",
            }
        }
    )

    # 2. Initialize the security service
    key_manager = KeyManager.load_from_settings(settings)
    app.state.security_service = SecurityService(key_manager)

    # 3. Initiate the Google login
    response = client.get("/login/google")
    assert response.status_code == 200

    # 4. Simulate the callback from Google
    response = client.get("/auth/google")
    assert response.status_code == 307
    redirect_url = response.headers["location"]
    assert redirect_url.startswith("http://localhost:3000/auth/callback?token=")