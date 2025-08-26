"""
Auth service specific test configuration.
Uses consolidated test framework infrastructure with auth-specific customizations.
"""

# Import all common fixtures from the consolidated base
from test_framework.conftest_base import *

# Import auth-specific utilities
from test_framework.fixtures.auth_fixtures import *
from test_framework.fixtures.database_fixtures import test_db_session
# SSOT compliance: Use auth_db directly instead of custom database mocks

import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio

# Use auth service isolated environment
from auth_service.auth_core.isolated_environment import get_env

# Set auth-specific environment variables (common ones handled by root conftest)
# CRITICAL: Only set test environment if we're actually running tests
# This prevents the dev launcher from being affected when modules are imported
# Check pytest context using get_env for consistency
if "pytest" in sys.modules or get_env().get("PYTEST_CURRENT_TEST"):
    env = get_env()
    env.enable_isolation()  # Enable isolation for tests
    env.set("ENVIRONMENT", "test", "auth_conftest")  # Use test environment for proper test setup
    env.set("AUTH_FAST_TEST_MODE", "false", "auth_conftest")  # Disable fast test mode for integration tests
    env.set("JWT_SECRET", "test_jwt_secret_key_that_is_long_enough_for_testing_purposes", "auth_conftest")
    env.set("GOOGLE_CLIENT_ID", "123456789-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com", "auth_conftest")
    env.set("GOOGLE_CLIENT_SECRET", "GOCSPX-1234567890123456789012345678901", "auth_conftest")
    env.set("DATABASE_URL", "sqlite+aiosqlite:///test_auth.db", "auth_conftest")
    env.set("AUTH_USE_FILE_DB", "true", "auth_conftest")  # Force file-based DB for tests
    env.set("REDIS_URL", "redis://localhost:6379/1", "auth_conftest")

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
        # No running loop, create a new one (avoid deprecated get_event_loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run the setup
    if not loop.is_running():
        loop.run_until_complete(setup_db())
    else:
        # If we're in an async context, create a task
        task = asyncio.create_task(setup_db())
    
    yield auth_db
    
    # Cleanup with proper async resource handling
    async def cleanup():
        try:
            await auth_db.close()
        except Exception:
            pass  # Ignore cleanup errors
    
    try:
        if not loop.is_running():
            loop.run_until_complete(cleanup())
        else:
            # Schedule cleanup task if in async context
            asyncio.create_task(cleanup())
    except Exception:
        pass  # Ignore cleanup errors

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
        # No running loop, create a new one (avoid deprecated get_event_loop)
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
    
    # Cleanup with proper async resource handling
    async def cleanup():
        try:
            await auth_db.close()
        except Exception:
            pass  # Ignore cleanup errors
    
    try:
        if not loop.is_running():
            loop.run_until_complete(cleanup())
        else:
            # Schedule cleanup task if in async context
            asyncio.create_task(cleanup())
    except Exception:
        pass  # Ignore cleanup errors

@pytest.fixture
def mock_auth_redis():
    """Auth-specific Redis mock for session management"""
    # Mock: Redis caching isolation to prevent test interference and external dependencies
    with patch('auth_service.auth_core.redis_manager.auth_redis_manager') as mock:
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
    """Clean test environment using IsolatedEnvironment"""
    env = get_env()
    # Enable isolation and backup state
    env.enable_isolation(backup_original=True)
    yield
    # Restore original environment state
    env.disable_isolation()

# REMOVED: Duplicate mock_auth_redis fixture - use the one above at line 130