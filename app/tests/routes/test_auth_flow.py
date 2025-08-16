import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
async def test_login_redirect_in_production():
    """Test that login redirects properly in production mode."""
    # Set test environment variables
    os.environ["SKIP_STARTUP_CHECKS"] = "true"
    os.environ["SECRET_KEY"] = "test_secret_key_for_auth_flow_tests_32_chars_minimum"
    
    # Store original environment value
    original_env = settings.environment
    
    try:
        settings.environment = "production"
        with TestClient(app) as client:
            response = client.get("/api/auth/login", follow_redirects=False)
            assert response.status_code == 302
    finally:
        # Restore original environment
        settings.environment = original_env
        # Clean up test environment variables
        os.environ.pop("SKIP_STARTUP_CHECKS", None)
        os.environ.pop("SECRET_KEY", None)
