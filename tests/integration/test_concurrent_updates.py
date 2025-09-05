import asyncio
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest

# NOTE: Assuming the following constants. These may need to be updated.
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword"


@pytest.fixture(scope="module")
def auth_token():
    """Fixture to get an auth token for a test user."""
    # NOTE: This assumes a dev login endpoint exists on the auth service
    # that can provide a token for a test user.
    with httpx.Client() as client:
        response = client.post(
            f"{AUTH_SERVICE_URL}/auth/dev/login", json={"email": TEST_USER_EMAIL}
        )
        response.raise_for_status()
        return response.json()["access_token"]


class TestConcurrentUpdates:

    @pytest.mark.asyncio
    async def test_concurrent_profile_updates(self, auth_token):
        """
        Tests that concurrent updates to a user profile are handled correctly.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        user_id = "test_user_id"  # NOTE: Assuming a static user ID for the test user

        # Two different update payloads
        payload1 = {"display_name": "Concurrent User Name 1"}
        payload2 = {"company": "Concurrent Company Name 2"}

        async with httpx.AsyncClient() as client:
            tasks = [
                # Mock: Component isolation for testing without external dependencies
                client.patch(
                    f"{BACKEND_URL}/api/users/{user_id}",
                    json=payload1,
                    headers=headers,
                ),
                # Mock: Component isolation for testing without external dependencies
                client.patch(
                    f"{BACKEND_URL}/api/users/{user_id}",
                    json=payload2,
                    headers=headers,
                ),
            ]
            responses = await asyncio.gather(*tasks)

        # Check that both requests were successful
        for response in responses:
            response.raise_for_status()

        # Fetch the user profile to verify the updates
        with httpx.Client() as client:
            response = client.get(
                f"{BACKEND_URL}/api/users/{user_id}", headers=headers
            )
            response.raise_for_status()
            user_profile = response.json()

        # Assert that both updates were applied
        assert user_profile["display_name"] == payload1["display_name"]
        assert user_profile["company"] == payload2["company"]
