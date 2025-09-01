from unittest.mock import patch
import os

import httpx
import pytest
from shared.isolated_environment import get_env

# NOTE: Assuming the following constants. These may need to be updated.
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"
TEST_USER_EMAIL = "test@example.com"


env = get_env()
@pytest.fixture(scope="module")
def auth_token():
    """Fixture to get an auth token for a test user."""
    # Skip if real services aren't available
    if not env.get("USE_REAL_SERVICES", "").lower() == "true":
        pytest.skip("Test requires real services - set USE_REAL_SERVICES=true")
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{AUTH_SERVICE_URL}/auth/dev/login", json={"email": TEST_USER_EMAIL}
            )
            response.raise_for_status()
            return response.json()["access_token"]
    except httpx.ConnectError:
        pytest.skip("Auth service not running - required for service communication tests")


class TestServiceCommunicationFailure:

    def test_auth_service_down(self, auth_token):
        """
        Tests that the backend handles the auth service being down gracefully.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        protected_endpoint = f"{BACKEND_URL}/api/user/profile"

        # Patch httpx.post to simulate the auth service being down
        # NOTE: This assumes the backend uses httpx.post to validate the token.
        # The actual path to patch may be different.
        # Mock: Component isolation for testing without external dependencies
        with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
            with httpx.Client() as client:
                response = client.get(protected_endpoint, headers=headers)

        # Assert that the backend returns a 503 Service Unavailable error
        assert response.status_code == 503
