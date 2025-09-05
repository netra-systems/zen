"""Test patterns and base classes for integration tests."""

import pytest
from shared.isolated_environment import IsolatedEnvironment


class L3IntegrationTest:
    """Base class for L3 integration tests."""
    
    @property
    def backend_url(self):
        """Get backend URL for testing."""
        return "http://localhost:8000"
    
    @pytest.fixture(autouse=True)
    async def setup_base(self):
        """Base setup for all L3 tests."""
        # Setup code here
        yield
        # Teardown code here
    
    async def create_test_user(self, email: str):
        """Create a test user for integration tests."""
        return {
            "id": f"user_{email.split('@')[0]}",
            "email": email,
            "name": f"Test User {email.split('@')[0]}",
            "token": f"test_token_{email.split('@')[0]}"
        }
    
    async def get_auth_token(self, user_data):
        """Get authentication token for a test user."""
        return user_data.get('token', 'test_token')
    
    async def get_auth_headers(self, user_data):
        """Get authentication headers for a test user."""
        return {
            "Authorization": f"Bearer {user_data.get('token', 'test_token')}"
        }


class L4IntegrationTest:
    """Base class for L4 integration tests."""
    
    @pytest.fixture(autouse=True)
    async def setup_base(self):
        """Base setup for all L4 tests."""
        # Setup code here
        yield
        # Teardown code here