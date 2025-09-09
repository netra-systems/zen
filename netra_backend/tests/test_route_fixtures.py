# Shim module for test fixtures
from test_framework.fixtures import *
from test_framework.fixtures.routes import CommonResponseValidators, MockServiceFactory
import pytest
from shared.isolated_environment import IsolatedEnvironment

# Import additional fixtures from routes test fixtures  
from netra_backend.tests.test_route_fixtures import TEST_DOCUMENT_DATA, TEST_MCP_REQUEST, authenticated_test_client

# Override TEST_USER_DATA to match admin routes test expectations
TEST_USER_DATA = {
    "admin": {
        "user_id": "admin_user_123",
        "email": "admin@example.com",
        "username": "adminuser",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "permissions": ["admin:read", "admin:write", "admin:delete", "user:read", "user:write"],
},
    "regular": {
        "user_id": "regular_user_456",
        "email": "user@example.com", 
        "username": "regularuser",
        "first_name": "Regular",
        "last_name": "User",
        "role": "user",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "permissions": ["user:read", "user:update"],
},
}

# Create basic_test_client as a proper pytest fixture
@pytest.fixture
def basic_test_client():
    """Create a basic test client for route testing."""
    from test_framework.fixtures.routes import create_mock_api_client
    return create_mock_api_client("http://localhost:8000")
