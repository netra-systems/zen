import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.dependencies import get_db_session
from app.db.testing import override_get_db

app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create test client with proper environment setup."""
    # Set test environment variables
    os.environ["SKIP_STARTUP_CHECKS"] = "true"
    os.environ["SECRET_KEY"] = "test_secret_key_for_user_auth_tests_32_chars_minimum"
    
    try:
        with TestClient(app=app, base_url="http://test") as client:
            yield client
    finally:
        # Clean up test environment variables
        os.environ.pop("SKIP_STARTUP_CHECKS", None)
        os.environ.pop("SECRET_KEY", None)

def test_get_auth_config_dev_mode(client: TestClient):
    settings.environment = "development"
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert data["development_mode"] == True
    assert data["endpoints"]["dev_login"] != None

def test_get_auth_config_prod_mode(client: TestClient):
    settings.environment = "production"
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert data["development_mode"] == False

def test_dev_login_get_not_allowed(client: TestClient):
    settings.environment = "development"
    response = client.get("/api/auth/dev_login", follow_redirects=False)
    assert response.status_code == 405  # Method Not Allowed

def test_dev_login_success(client: TestClient):
    settings.environment = "development"
    response = client.post("/api/auth/dev_login", json={"email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Dev login successful"
    assert data["user"] == "test@example.com"

def test_dev_login_prod_mode(client: TestClient):
    settings.environment = "production"
    response = client.post("/api/auth/dev_login", json={"email": "test@example.com"})
    assert response.status_code == 403

def test_google_login_redirect(client: TestClient):
    response = client.get("/api/auth/login/google", follow_redirects=False)
    assert response.status_code == 302  # Found
    assert "accounts.google.com" in response.headers["location"]

def test_logout_redirect(client: TestClient):
    response = client.get("/api/auth/logout", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect
    assert response.headers["location"] == "/login"