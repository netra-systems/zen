"""
Auth service specific test configuration.
Uses consolidated test framework infrastructure with auth-specific customizations.
"""

# Import all common fixtures from the consolidated base
from test_framework.conftest_base import *

# Import auth-specific utilities
from test_framework.fixtures.auth_fixtures import *
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.mocks.database_mocks import MockAsyncDatabaseFactory

import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio

# Set auth-specific environment variables (common ones handled by root conftest)
# CRITICAL: Only set test environment if we're actually running tests
# This prevents the dev launcher from being affected when modules are imported
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    os.environ["ENVIRONMENT"] = "test"  # Use test environment for proper test setup
    os.environ["AUTH_FAST_TEST_MODE"] = "false"  # Disable fast test mode for integration tests
    os.environ["JWT_SECRET"] = "test_jwt_secret_key_that_is_long_enough_for_testing_purposes"
    os.environ["GOOGLE_CLIENT_ID"] = "test_google_client_id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test_google_client_secret"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_auth.db"
    os.environ["AUTH_USE_FILE_DB"] = "true"  # Force file-based DB for tests
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure database is initialized before any tests run"""
    import asyncio
    from auth_service.auth_core.database.connection import auth_db
    from auth_service.auth_core.database.models import Base
    
    async def setup_db():
        # Force initialization regardless of test mode
        if auth_db._initialized:
            await auth_db.close()
            auth_db._initialized = False
        
        # Initialize the database
        await auth_db.initialize()
        
        # Create all tables
        async with auth_db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        return auth_db
    
    # Get or create event loop - avoid deprecation warning
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    
    # Run the setup
    if not loop.is_running():
        loop.run_until_complete(setup_db())
    else:
        # If we're in an async context, create a task
        task = asyncio.create_task(setup_db())
    
    yield auth_db
    
    # Cleanup
    try:
        if not loop.is_running():
            loop.run_until_complete(auth_db.close())
    except:
        pass

# REMOVED: Duplicate auth_db fixture - use initialized_test_db or test_db_session instead

@pytest.fixture(scope="function")
def initialized_test_db():
    """Synchronous fixture that ensures database is initialized for integration tests"""
    import asyncio
    from auth_service.auth_core.database.connection import auth_db
    
    # Get or create event loop - avoid deprecation warning
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    
    # Initialize database synchronously
    if not loop.is_running():
        loop.run_until_complete(auth_db.initialize())
    else:
        # If loop is already running, create task
        task = asyncio.create_task(auth_db.initialize())
        # This fixture will be called before the test, ensuring DB is ready
    
    yield auth_db
    
    # Cleanup
    try:
        if not loop.is_running():
            loop.run_until_complete(auth_db.close())
    except:
        pass

@pytest.fixture
def mock_auth_redis():
    """Auth-specific Redis mock for session management"""
    with patch('auth_service.auth_core.core.session_manager.redis') as mock:
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

# REMOVED: Duplicate test_db_session fixture
# Use test_framework.fixtures.database_fixtures.test_db_session instead
# or create auth-specific session if needed using auth_db.get_session()

@pytest.fixture
def clean_environment():
    """Clean test environment"""
    original_env = dict(os.environ)
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_auth_redis():
    """Mock Redis client for OAuth security testing"""
    from unittest.mock import Mock
    
    redis_mock = Mock()
    
    # Set up default mock behaviors
    redis_mock.exists.return_value = False  # By default, keys don't exist
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.ping.return_value = True
    
    return redis_mock