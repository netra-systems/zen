"""
Auth service specific test configuration.
Depends on root /tests/conftest.py for common fixtures and environment setup.
"""
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import patch

import pytest

# Set auth-specific environment variables (common ones handled by root conftest)
os.environ["JWT_SECRET"] = "test_jwt_secret_key_that_is_long_enough_for_testing_purposes"
os.environ["GOOGLE_CLIENT_ID"] = "test_google_client_id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test_google_client_secret"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def auth_db():
    """Mock auth database for testing"""
    from auth_service.auth_core.database.connection import auth_db
    await auth_db.initialize()
    yield auth_db
    await auth_db.close()

@pytest.fixture
def mock_auth_redis():
    """Auth-specific Redis mock for session management"""
    with patch('auth_core.core.session_manager.redis') as mock:
        mock.ping.return_value = True
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = True
        yield mock

@pytest.fixture
def test_user_data():
    """Test user data for OAuth tests"""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "provider": "google"
    }

@pytest.fixture
def clean_environment():
    """Clean test environment"""
    original_env = dict(os.environ)
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)