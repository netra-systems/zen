"""
Backend-specific test configuration.
Uses consolidated test framework infrastructure with backend-specific customizations.
"""

# Import all common fixtures from the consolidated base
from test_framework.conftest_base import *

# Import backend-specific utilities
from test_framework.fixtures.database_fixtures import *
from test_framework.mocks.service_mocks import MockClickHouseService, MockLLMService

# Setup Python path for imports
import sys
from pathlib import Path

# Add project root to Python path for netra_backend imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os

# Import constants at module level only if not in collection mode  
if not os.environ.get("TEST_COLLECTION_MODE"):
    from netra_backend.app.core.network_constants import (
        DatabaseConstants,
        HostConstants,
        ServicePorts,
    )

# Set test environment variables BEFORE importing any app modules
# Use isolated values if TEST_ISOLATION is enabled

# CRITICAL: Set test collection mode to skip heavy initialization during pytest collection
# Only set if we're actually running tests to prevent affecting dev launcher
import sys
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    os.environ["TEST_COLLECTION_MODE"] = "1"

# Only set environment variables if we're actually running tests
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    if os.environ.get("TEST_ISOLATION") == "1":
        # When using test isolation, environment is already configured
        # Just ensure critical test flags are set

        os.environ.setdefault("TESTING", "1")

        os.environ.setdefault("ENVIRONMENT", "testing")

        os.environ.setdefault("LOG_LEVEL", "ERROR")

        os.environ.setdefault("DEV_MODE_DISABLE_CLICKHOUSE", "true")

        os.environ.setdefault("CLICKHOUSE_ENABLED", "false")
        
        # Ensure SERVICE_SECRET is set for test isolation mode
        os.environ.setdefault("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-32-chars-minimum-length")

    else:
        # Standard test environment setup

        os.environ["TESTING"] = "1"
        # Import network constants lazily only if not in collection mode
        if not os.environ.get("TEST_COLLECTION_MODE"):
            from netra_backend.app.core.network_constants import (
                DatabaseConstants,
                HostConstants, 
                ServicePorts,
            )
        
        # Use PostgreSQL URL format even for tests to satisfy validator
        if not os.environ.get("TEST_COLLECTION_MODE"):
            os.environ["DATABASE_URL"] = DatabaseConstants.build_postgres_url(
                user="test", password="test", 
                port=ServicePorts.POSTGRES_DEFAULT,
                database="netra_test"
            )

            os.environ["REDIS_URL"] = DatabaseConstants.build_redis_url(
                database=DatabaseConstants.REDIS_TEST_DB
            )

            os.environ["REDIS_HOST"] = HostConstants.LOCALHOST

            os.environ["REDIS_PORT"] = str(ServicePorts.REDIS_DEFAULT)
        else:
            # Use simple defaults during collection mode
            os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/netra_test"
            os.environ["REDIS_URL"] = "redis://localhost:6379/1"
            os.environ["REDIS_HOST"] = "localhost"
            os.environ["REDIS_PORT"] = "6379"

        os.environ["REDIS_USERNAME"] = ""

        os.environ["REDIS_PASSWORD"] = ""

        os.environ["TEST_DISABLE_REDIS"] = "true"

        os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-must-be-32-chars"

        os.environ["SERVICE_SECRET"] = "test-service-secret-for-cross-service-auth-32-chars-minimum-length"

        os.environ["FERNET_KEY"] = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="

        os.environ["ENVIRONMENT"] = "testing"

        os.environ["LOG_LEVEL"] = "ERROR"
        # Disable ClickHouse for tests

        os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"

        os.environ["CLICKHOUSE_ENABLED"] = "false"
        
        # Handle real LLM testing configuration

        if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
            # When real LLM testing is enabled, use actual API keys
            # These should be passed from the test runner
            # Ensure GOOGLE_API_KEY mirrors GEMINI_API_KEY for compatibility

            if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):

                os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
            
            # Validate that at least Gemini key is available for real LLM testing
            gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not gemini_key or gemini_key.startswith("test-"):
                import warnings
                warnings.warn(
                    "ENABLE_REAL_LLM_TESTING=true but no valid Gemini API key found. "
                    "Real LLM tests will fail. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.",
                    stacklevel=2
                )

        else:
            # Use mock keys for regular testing

            os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

            os.environ.setdefault("GOOGLE_API_KEY", "test-gemini-api-key")  # Same as GEMINI

            os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")

            os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-api-key")

import pytest
import asyncio
from typing import Optional

# Always import logger - this is lightweight
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

# Only import heavy modules if not in collection mode
if not os.environ.get("TEST_COLLECTION_MODE"):
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
if not os.environ.get("TEST_COLLECTION_MODE"):
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