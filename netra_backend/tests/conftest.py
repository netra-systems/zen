"""
Backend-specific test configuration.
Uses consolidated test framework infrastructure with backend-specific customizations.
"""

# Import all common fixtures from the consolidated base FIRST
from test_framework.conftest_base import *

# Use the SAME get_env from the test framework to avoid multiple instances
try:
    from dev_launcher.isolated_environment import get_env
except ImportError:
    # Fallback if dev_launcher is not available
    from netra_backend.app.core.isolated_environment import get_env

# Import backend-specific utilities
from test_framework.fixtures.database_fixtures import *
from test_framework.fixtures.service_fixtures import *
from test_framework.mocks.service_mocks import MockClickHouseService, MockLLMService

# Setup Python path for imports
import sys
from pathlib import Path

# Add project root to Python path for netra_backend imports

# Import constants at module level only if not in collection mode  
if not get_env().get("TEST_COLLECTION_MODE"):
    from netra_backend.app.core.network_constants import (
        DatabaseConstants,
        HostConstants,
        ServicePorts,
    )

# Set test environment variables BEFORE importing any app modules
# Use isolated values if TEST_ISOLATION is enabled

# CRITICAL: Set test collection mode to skip heavy initialization during pytest collection
# Only set if we're in the collection phase (pytest is imported but no test is executing)
import sys
import os
import atexit

# Apply stderr patch to prevent I/O errors during test teardown
try:
    from netra_backend.tests import test_logging_patch  # Import to apply the patch
except ImportError:
    pass

# Enhanced collection mode detection and cleanup registration
if "pytest" in sys.modules and not get_env().get("PYTEST_CURRENT_TEST"):
    # Only set collection mode if pytest is imported but we're not currently executing a test
    # PYTEST_CURRENT_TEST is set during test execution but not during collection
    get_env().set("TEST_COLLECTION_MODE", "1", source="netra_backend_conftest")

# Register cleanup for async resources at module level
def _cleanup_async_resources():
    """Cleanup async resources on exit"""
    import asyncio
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            # Close any remaining event loops
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                loop.close()
        except Exception:
            pass
        
        # Safely cleanup loguru handlers to prevent I/O errors during test shutdown
        try:
            from loguru import logger
            import time
            # Remove all handlers to prevent closed file I/O errors
            time.sleep(0.05)  # Small delay to allow any queued messages to be processed
            logger.remove()
        except Exception:
            pass

atexit.register(_cleanup_async_resources)

# Only set environment variables if we're actually running tests
if "pytest" in sys.modules or get_env().get("PYTEST_CURRENT_TEST"):
    # Use IsolatedEnvironment for all test configuration
    env = get_env()
    
    if env.get("TEST_ISOLATION") == "1":
        # When using test isolation, environment is already configured
        # Just ensure critical test flags are set
        env.set("TESTING", "1", source="netra_backend_conftest")
        env.set("ENVIRONMENT", "testing", source="netra_backend_conftest")
        env.set("LOG_LEVEL", "ERROR", source="netra_backend_conftest")
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", source="netra_backend_conftest")
        env.set("CLICKHOUSE_ENABLED", "false", source="netra_backend_conftest")
        # Ensure SERVICE_SECRET is set for test isolation mode
        env.set("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-32-chars-minimum-length", source="netra_backend_conftest")

    else:
        # Standard test environment setup using IsolatedEnvironment
        env.set("TESTING", "1", source="netra_backend_conftest")
        
        # Import network constants lazily only if not in collection mode
        if not env.get("TEST_COLLECTION_MODE"):
            from netra_backend.app.core.network_constants import (
                DatabaseConstants,
                HostConstants, 
                ServicePorts,
            )
        
        # Use PostgreSQL URL format even for tests to satisfy validator
        if not env.get("TEST_COLLECTION_MODE"):
            database_url = DatabaseConstants.build_postgres_url(
                user="postgres", password="postgres", 
                port=ServicePorts.POSTGRES_DEFAULT,
                database="netra_test"
            )
            redis_url = DatabaseConstants.build_redis_url(
                database=DatabaseConstants.REDIS_TEST_DB
            )
            env.set("DATABASE_URL", database_url, source="netra_backend_conftest")
            env.set("REDIS_URL", redis_url, source="netra_backend_conftest")
            env.set("REDIS_HOST", HostConstants.LOCALHOST, source="netra_backend_conftest")
            env.set("REDIS_PORT", str(ServicePorts.REDIS_DEFAULT), source="netra_backend_conftest")
        else:
            # Use simple defaults during collection mode
            env.set("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test", source="netra_backend_conftest")
            env.set("REDIS_URL", "redis://localhost:6379/0", source="netra_backend_conftest")
            env.set("REDIS_HOST", "localhost", source="netra_backend_conftest")
            env.set("REDIS_PORT", "6379", source="netra_backend_conftest")

        env.set("REDIS_USERNAME", "", source="netra_backend_conftest")
        env.set("REDIS_PASSWORD", "", source="netra_backend_conftest")
        env.set("TEST_DISABLE_REDIS", "true", source="netra_backend_conftest")
        env.set("SECRET_KEY", "test-secret-key-for-testing-only", source="netra_backend_conftest")
        env.set("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-must-be-32-chars", source="netra_backend_conftest")
        env.set("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-32-chars-minimum-length", source="netra_backend_conftest")
        env.set("FERNET_KEY", "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=", source="netra_backend_conftest")
        
        # Set test values for all required secrets from SecretManager
        env.set("GOOGLE_CLIENT_ID", "test-google-client-id-for-integration-testing", source="netra_backend_conftest")
        env.set("GOOGLE_CLIENT_SECRET", "test-google-client-secret-for-integration-testing", source="netra_backend_conftest")
        env.set("CLICKHOUSE_PASSWORD", "test-clickhouse-password-for-integration-testing", source="netra_backend_conftest")
        env.set("ENVIRONMENT", "testing", source="netra_backend_conftest")
        env.set("LOG_LEVEL", "ERROR", source="netra_backend_conftest")
        
        # Disable ClickHouse for tests
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", source="netra_backend_conftest")
        env.set("CLICKHOUSE_ENABLED", "false", source="netra_backend_conftest")
        
        # Handle real LLM testing configuration
        if env.get("ENABLE_REAL_LLM_TESTING") == "true":
            # When real LLM testing is enabled, use actual API keys
            # These should be passed from the test runner
            # Ensure GOOGLE_API_KEY mirrors GEMINI_API_KEY for compatibility
            if env.get("GEMINI_API_KEY") and not env.get("GOOGLE_API_KEY"):
                env.set("GOOGLE_API_KEY", env.get("GEMINI_API_KEY"), source="netra_backend_conftest")
            
            # Validate that at least Gemini key is available for real LLM testing
            gemini_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
            if not gemini_key or gemini_key.startswith("test-"):
                import warnings
                warnings.warn(
                    "ENABLE_REAL_LLM_TESTING=true but no valid Gemini API key found. "
                    "Real LLM tests will fail. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.",
                    stacklevel=2
                )
        else:
            # Use mock keys for regular testing
            if not env.get("GEMINI_API_KEY"):
                env.set("GEMINI_API_KEY", "test-gemini-api-key", source="netra_backend_conftest")
            if not env.get("GOOGLE_API_KEY"):
                env.set("GOOGLE_API_KEY", "test-gemini-api-key", source="netra_backend_conftest")  # Same as GEMINI
            if not env.get("GOOGLE_API_KEY"):
                env.set("GOOGLE_API_KEY", "test-openai-api-key", source="netra_backend_conftest")
            if not env.get("ANTHROPIC_API_KEY"):
                env.set("ANTHROPIC_API_KEY", "test-anthropic-api-key", source="netra_backend_conftest")

import pytest
import asyncio
from typing import Optional

# Always import logger - this is lightweight
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

# Only import heavy modules if not in collection mode
if not get_env().get("TEST_COLLECTION_MODE"):
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import StaticPool
    
    # Import schemas if available
    try:
        from netra_backend.app.schemas.auth_schemas import UserAuthentication
        from netra_backend.app.services.user_service_factory import get_user_service_sync
    except ImportError:
        UserAuthentication = None
        get_user_service_sync = None
    
    # Import config if available
    try:
        from netra_backend.app.core.configuration import get_unified_config
    except ImportError:
        get_unified_config = None
else:
    # Stub imports for collection mode
    TestClient = None
    AsyncSession = None
    create_async_engine = None
    StaticPool = None
    UserAuthentication = None
    get_user_service_sync = None
    get_unified_config = None

# Mock services
class MockClickHouseService:
    """Mock ClickHouse service for testing."""
    async def execute(self, query):
        return []
    
    async def insert(self, table, data):
        return True

class MockRedisService:
    """Mock Redis service for testing."""
    async def get(self, key):
        return None
    
    async def set(self, key, value, ex=None):
        return True
    
    async def delete(self, key):
        return True
    
    async def exists(self, key):
        return False

# Skip importing backend modules during collection to avoid side effects
if not get_env().get("TEST_COLLECTION_MODE"):
    # Event loop configuration
    @pytest.fixture(scope="function")
    def event_loop():
        """Create a new event loop for each test function to prevent async issues."""
        # Always create a new event loop for each test to prevent contamination
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        asyncio.set_event_loop(loop)
        yield loop
        # Proper cleanup: cancel all tasks and close the loop
        try:
            # Cancel any remaining tasks
            pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending_tasks:
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
        except Exception:
            pass
        finally:
            if not loop.is_closed():
                loop.close()

    # Database fixture delegates to single source of truth from test_framework
    # REMOVED: Duplicate db_session implementation 
    # Use test_framework.fixtures.database_fixtures.test_db_session instead

    # Test client fixture only if FastAPI is available
    if TestClient:
        @pytest.fixture(scope="function")
        def test_client():
            """Create test client for FastAPI app."""
            from netra_backend.app.main import app
            with TestClient(app) as client:
                yield client

    # Mock user fixture only if UserAuthentication is available
    if UserAuthentication:
        @pytest.fixture
        def mock_user():
            """Create a mock authenticated user."""
            return UserAuthentication(
                user_id="test-user-123",
                email="test@example.com",
                is_authenticated=True,
                roles=["user"]
            )

    # Mock services fixtures
    @pytest.fixture
    def mock_clickhouse():
        """Mock ClickHouse service."""
        return MockClickHouseService()

    @pytest.fixture
    def mock_redis():
        """Mock Redis service."""
        return MockRedisService()

    # Config fixture only if config is available
    if get_unified_config:
        @pytest.fixture
        def test_config():
            """Get test configuration."""
            return get_unified_config()

else:
    # Provide empty fixtures during collection mode to prevent import errors
    
    @pytest.fixture
    def event_loop():
        """Placeholder event loop fixture for collection mode."""
        pass
    
    @pytest.fixture
    def db_session():
        """Placeholder database session fixture for collection mode."""
        pass
    
    @pytest.fixture
    def test_client():
        """Placeholder test client fixture for collection mode."""
        pass
    
    @pytest.fixture
    def mock_user():
        """Placeholder mock user fixture for collection mode."""
        pass
    
    @pytest.fixture
    def mock_clickhouse():
        """Placeholder mock ClickHouse fixture for collection mode."""
        pass
    
    @pytest.fixture
    def mock_redis():
        """Placeholder mock Redis fixture for collection mode."""
        pass
    
    @pytest.fixture
    def test_config():
        """Placeholder config fixture for collection mode."""
        pass

# Auto-cleanup fixture to prevent I/O errors during test teardown
@pytest.fixture(autouse=True)
def cleanup_loguru_handlers():
    """Automatically cleanup loguru handlers after each test to prevent I/O errors."""
    yield  # Run the test
    # Cleanup after test completes
    try:
        from loguru import logger
        import warnings
        import time
        import sys
        import os
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Check if we're in pytest teardown phase
            is_pytest_teardown = (
                hasattr(sys, '_getframe') and
                any('pytest' in str(frame.filename) for frame in 
                    [sys._getframe(i) for i in range(10)] if frame)
            )
            
            # Small delay to allow queued messages to be processed, but only if not in teardown
            if not is_pytest_teardown:
                time.sleep(0.01)
            
            # Force close any open file handlers before removing
            try:
                # Access internal loguru state carefully
                if hasattr(logger, '_core') and hasattr(logger._core, 'handlers'):
                    for handler_id, handler in list(logger._core.handlers.items()):
                        if hasattr(handler, '_sink') and hasattr(handler._sink, '_file'):
                            try:
                                if hasattr(handler._sink._file, 'close'):
                                    handler._sink._file.close()
                            except (AttributeError, ValueError, OSError):
                                pass
            except (AttributeError, ValueError, OSError):
                pass
            
            # Remove all handlers
            logger.remove()
            
    except (ImportError, ValueError, OSError, AttributeError):
        # Ignore any errors during cleanup - this is common during test teardown
        pass

# Common test utilities
def assert_success_response(response, expected_status=200):
    """Assert that response is successful with expected status."""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    return response.json() if response.text else None

def assert_error_response(response, expected_status=400, expected_error=None):
    """Assert that response is an error with expected status."""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    if expected_error:
        data = response.json()
        assert expected_error in str(data), f"Expected error '{expected_error}' not found in {data}"
    return response.json() if response.text else None