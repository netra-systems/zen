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
        return_value=RedirectResponse(url="https://accounts.google.com/o/oauth2/v2/auth", status_code=302)
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

    # 3. Use TestClient as a context manager to persist session
    with TestClient(app) as client:
        # 4. Initiate the Google login
        response = client.get("/login/google", follow_redirects=False)
        assert response.status_code == 302
        assert "state" in response.cookies

        # 5. Simulate the callback from Google
        response = client.get("/api/v3/auth/google", follow_redirects=False)
        assert response.status_code == 307
        redirect_url = response.headers["location"]
        assert redirect_url.startswith(f"{settings.frontend_url}/auth/callback?token=")

        # 6. Verify the token in the redirect URL
        token = redirect_url.split("=")[1]
        payload = app.state.security_service.decode_access_token(token)
        assert payload["sub"] == "test@example.com"