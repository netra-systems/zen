"""
Auth service specific test configuration.
Depends on root /tests/conftest.py for common fixtures and environment setup.
"""
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio

# Set auth-specific environment variables (common ones handled by root conftest)
os.environ["ENVIRONMENT"] = "test"  # Use test environment for proper test setup
os.environ["AUTH_FAST_TEST_MODE"] = "false"  # Disable fast test mode for integration tests
os.environ["JWT_SECRET"] = "test_jwt_secret_key_that_is_long_enough_for_testing_purposes"
os.environ["GOOGLE_CLIENT_ID"] = "test_google_client_id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test_google_client_secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_auth.db"
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

@pytest.fixture(scope="function")
def initialized_test_db():
    """Synchronous fixture that ensures database is initialized for integration tests"""
    import asyncio
    from auth_service.auth_core.database.connection import auth_db
    
    # Get or create event loop
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

@pytest_asyncio.fixture(scope="function")
async def test_db_session():
    """Create async database session for tests with fresh tables"""
    from auth_service.auth_core.database.connection import auth_db
    from auth_service.auth_core.database.models import Base
    
    # Force a fresh database connection for each test
    if auth_db._initialized:
        await auth_db.close()
        auth_db._initialized = False
    
    # Initialize database
    await auth_db.initialize()
    
    # Explicitly create all tables
    async with auth_db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session directly without auto-commit context manager
    session = auth_db.async_session_maker()
    try:
        yield session
    finally:
        # Clean rollback to prevent any pending transactions
        try:
            await session.rollback()
        except:
            pass
        await session.close()

@pytest.fixture
def clean_environment():
    """Clean test environment"""
    original_env = dict(os.environ)
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)