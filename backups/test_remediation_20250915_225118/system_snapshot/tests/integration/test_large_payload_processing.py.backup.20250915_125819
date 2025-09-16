import json
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest

# NOTE: Assuming the following constants. These may need to be updated.
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"
TEST_USER_EMAIL = "test@example.com"


@pytest.fixture(scope="module")
def auth_token():
    """Fixture to get an auth token for a test user."""
    with httpx.Client() as client:
        response = client.post(
            f"{AUTH_SERVICE_URL}/auth/dev/login", json={"email": TEST_USER_EMAIL}
        )
        response.raise_for_status()
        return response.json()["access_token"]


@pytest.mark.integration
class TestLargePayloadProcessing:

    def test_large_json_payload(self, auth_token):
        """
        Tests that the backend can handle large JSON payloads without crashing.
        """
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        # NOTE: Assuming an endpoint like this exists for processing large
        # reports.
        endpoint = f"{BACKEND_URL}/api/reports/process"

        # Generate a large JSON payload (approx. 10MB)
        large_data = {
            "data": [{"key": f"key_{i}", "value": "a" * 1024} for i in range(10 * 1024)]
        }
        payload = json.dumps(large_data).encode("utf-8")

        with httpx.Client(timeout=30) as client:
            response = client.post(endpoint, content=payload, headers=headers)

        # Assert that the request was accepted
        assert response.status_code == 202  # Accepted for processing

        # Assert that the response indicates success
        assert response.json()["status"] == "processing"
