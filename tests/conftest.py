import asyncio
import os
import sys
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

import pytest

# Add project root for imports

# Import isolated environment for proper test isolation
from dev_launcher.isolated_environment import get_env
from test_framework.environment_isolation import (
    get_test_env_manager,
    isolated_test_session,
    isolated_test_env,
    ensure_test_isolation,
)

# =============================================================================
# COMMON ENVIRONMENT SETUP FOR ALL TESTS
# Uses IsolatedEnvironment to prevent global pollution
# =============================================================================

# Set up isolated test environment if we're running tests
if "pytest" in sys.modules or get_env().get("PYTEST_CURRENT_TEST"):
    # Ensure test isolation is enabled
    ensure_test_isolation()

# Re-export test environment fixtures for convenience
__all__ = ['isolated_test_session', 'isolated_test_env']

# Only import if available to avoid failures
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import StaticPool

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Mock User class if app imports fail
try:
    from netra_backend.app.schemas import User
except ImportError:

    class User:
        def __init__(self, id, email, is_active=True, is_superuser=False):
            self.id = id
            self.email = email
            self.is_active = is_active
            self.is_superuser = is_superuser


pytest_plugins = ["pytest_asyncio"]


# Remove custom event_loop fixture to let pytest-asyncio handle it properly
# The --asyncio-mode=auto setting in pytest.ini will provide the event loop


# =============================================================================
# E2E PERFORMANCE TESTING FIXTURES
# Consolidated from tests/e2e/performance/conftest.py
# =============================================================================

# Environment configuration for performance tests
# Use isolated environment for safe access
E2E_TEST_CONFIG = {
    "websocket_url": get_env().get("E2E_WEBSOCKET_URL", "ws://localhost:8765"),
    "backend_url": get_env().get("E2E_BACKEND_URL", "http://localhost:8000"),
    "auth_service_url": get_env().get("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "skip_real_services": get_env().get("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_mode": get_env().get("HIGH_VOLUME_TEST_MODE", "mock")
}


@pytest.fixture
async def high_volume_server():
    """High-volume WebSocket server fixture."""
    if E2E_TEST_CONFIG["test_mode"] != "mock":
        yield None
        return
        
    try:
        from tests.e2e.test_helpers.performance_base import HighVolumeWebSocketServer
        server = HighVolumeWebSocketServer()
        await server.start()
        
        # Allow server startup time
        await asyncio.sleep(1.0)
        
        yield server
        await server.stop()
    except ImportError:
        # Mock server if performance_base not available
        # Mock: Performance test server isolation when performance_base module unavailable
        yield MagicMock()


@pytest.fixture
async def throughput_client(test_user_token, high_volume_server):
    """High-volume throughput client fixture."""
    try:
        from tests.e2e.test_helpers.performance_base import HighVolumeThroughputClient
        websocket_uri = E2E_TEST_CONFIG["websocket_url"]
        client = HighVolumeThroughputClient(websocket_uri, test_user_token["token"], "primary-client")
        
        # Establish connection with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await client.connect()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    pytest.skip(f"WebSocket connection failed after {max_retries} attempts: {e}")
                await asyncio.sleep(1.0)
        
        yield client
        
        # Cleanup
        try:
            await client.disconnect()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Client cleanup error: {e}")
    except ImportError:
        # Mock client if performance_base not available
        # Mock: Performance test client isolation when performance_base module unavailable
        yield AsyncMock()


# =============================================================================
# COMMON MOCK FIXTURES
# Consolidated basic mocks used across multiple services
# =============================================================================

@pytest.fixture
def mock_redis_client():
    """Common Redis client mock for all tests"""
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    mock.ping = AsyncMock(return_value=True)
    mock.aclose = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_redis_manager():
    """Common Redis manager mock"""
    # Mock: Redis cache isolation to prevent test interference and external dependencies
    mock = MagicMock()
    mock.enabled = True
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def mock_clickhouse_client():
    """Common ClickHouse client mock"""
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value=None)
    mock.fetch = AsyncMock(return_value=[])
    mock.insert_data = AsyncMock(return_value=None)
    mock.command = AsyncMock(return_value=None)
    mock.ping = AsyncMock(return_value=True)
    return mock


# =============================================================================\n# COMMON TEST DATA FIXTURES\n# Shared test data used across multiple services\n# =============================================================================\n\n@pytest.fixture\ndef common_test_user():\n    \"\"\"Common test user data for all services\"\"\"\n    return {\n        \"id\": \"test-user-123\",\n        \"email\": \"test@example.com\",\n        \"name\": \"Test User\",\n        \"is_active\": True,\n        \"is_superuser\": False\n    }\n\n\n@pytest.fixture\ndef sample_data():\n    \"\"\"Basic sample data for tests\"\"\"\n    return {\"test\": \"data\", \"status\": \"active\"}\n\n\n# =============================================================================\n# COMMON SERVICE MOCKS\n# Basic service mocks that are reused across tests\n# ============================================================================="


@pytest.fixture
def mock_llm_manager():
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock = MagicMock()
    mock.get_llm = MagicMock(return_value=MagicMock())
    return mock


@pytest.fixture
def mock_websocket_manager():
    # Mock: WebSocket infrastructure isolation for unit tests without real connections
    mock = MagicMock()
    mock.active_connections = {}
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.send_message = AsyncMock(return_value=None)
    mock.broadcast = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_background_task_manager():
    # Mock: Background task isolation to prevent real tasks during testing
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_key_manager():
    # Mock: Cryptographic key isolation for security testing without real keys
    mock = MagicMock()
    mock.load_from_settings = MagicMock(return_value=mock)
    return mock


@pytest.fixture
def mock_security_service():
    # Mock: Security service isolation for auth testing without real token validation
    return MagicMock()


@pytest.fixture
def mock_tool_dispatcher():
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    return MagicMock()


@pytest.fixture
def mock_agent_supervisor():
    # Mock: Agent supervisor isolation for testing without spawning real agents
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_agent_service():
    # Mock: Agent service isolation for testing without LLM agent execution
    return MagicMock()


@pytest.fixture
def app(
    mock_redis_manager,
    mock_clickhouse_client,
    mock_llm_manager,
    mock_websocket_manager,
    mock_background_task_manager,
    mock_key_manager,
    mock_security_service,
    mock_tool_dispatcher,
    mock_agent_supervisor,
    mock_agent_service,
):
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.redis_manager = mock_redis_manager
        app.state.clickhouse_client = mock_clickhouse_client
        app.state.llm_manager = mock_llm_manager
        app.state.background_task_manager = mock_background_task_manager
        app.state.key_manager = mock_key_manager
        app.state.security_service = mock_security_service
        app.state.tool_dispatcher = mock_tool_dispatcher
        app.state.agent_supervisor = mock_agent_supervisor
        app.state.agent_service = mock_agent_service
        yield

    app = FastAPI(lifespan=lifespan)

    # Only include routes if they can be imported
    try:
        from netra_backend.app.routes.websocket_secure import router as websockets_router

        app.include_router(websockets_router)
    except ImportError:
        pass

    try:
        from netra_backend.app.routes.auth import router as auth_router

        app.include_router(auth_router, prefix="/api/auth")
    except ImportError:
        pass

    return app


@pytest.fixture
def client(app):
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")
    return TestClient(app)


@pytest.fixture
def test_user():
    return User(
        id="test-user-id", email="test@example.com", is_active=True, is_superuser=False
    )


@pytest.fixture
def auth_headers(test_user):
    try:
        from netra_backend.app.auth_integration.auth import create_access_token

        token = create_access_token(data={"sub": test_user.email})
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        # Return mock headers if auth module not available
        return {"Authorization": "Bearer mock-token"}


# NOTE: sample_data fixture moved to common fixtures section above


# Real Service Testing Fixtures
@pytest.fixture(scope="session")
async def dev_launcher():
    """Provides dev_launcher instance for real service testing."""
    try:
        from dev_launcher.config import LauncherConfig
        from dev_launcher.launcher import DevLauncher
    except ImportError:
        pytest.skip("Dev launcher not available")
        return

    # Check if we should use real services
    use_real_services = os.environ.get("USE_REAL_SERVICES", "false").lower() == "true"
    if not use_real_services:
        pytest.skip("Real services disabled (set USE_REAL_SERVICES=true)")
        return

    config = LauncherConfig(
        dynamic_ports=True,
        test_mode=True,
        startup_timeout=30,
        services=["auth", "backend"],  # Don't start frontend for tests
    )

    launcher = DevLauncher(config)

    try:
        # Start all services
        success = await launcher.run()
        if not success:
            pytest.fail("Failed to start services via dev_launcher")

        yield launcher

    finally:
        # Cleanup
        await launcher.shutdown()


@pytest.fixture(scope="session")
async def service_discovery(dev_launcher):
    """Provides service discovery for real service endpoints."""
    try:
        from dev_launcher.discovery import ServiceDiscovery
    except ImportError:
        pytest.skip("Service discovery not available")
        return

    discovery = ServiceDiscovery()

    # Wait for services to register
    await discovery.wait_for_service("auth", timeout=30.0)
    await discovery.wait_for_service("backend", timeout=30.0)

    return discovery


@pytest.fixture(scope="session")
async def real_services(dev_launcher, service_discovery):
    """Provides real services with typed clients."""
    try:
        from tests.clients import TestClientFactory
    except ImportError:
        pytest.skip("Test client factory not available")
        return

    factory = TestClientFactory(service_discovery)

    # Create clients
    auth_client = await factory.create_auth_client()

    # Create test user and get token
    test_user_data = await auth_client.create_test_user()
    token = test_user_data["token"]

    # Create authenticated clients
    backend_client = await factory.create_backend_client(token=token)

    class RealServiceContext:
        def __init__(self):
            self.auth_client = auth_client
            self.backend_client = backend_client
            self.factory = factory
            self.test_user = test_user_data

        async def create_websocket_client(self, token: Optional[str] = None):
            """Create WebSocket client with optional custom token."""
            ws_token = token or self.test_user["token"]
            return await self.factory.create_websocket_client(ws_token)

    context = RealServiceContext()

    yield context

    # Cleanup
    await factory.cleanup()


# =============================================================================
# E2E TESTING FIXTURES
# Consolidated from tests/e2e/conftest.py
# =============================================================================

import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

# Configure E2E test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
e2e_logger = logging.getLogger("e2e_conftest")

# E2E Test Environment Configuration
E2E_CONFIG = {
    "auth_service_url": get_env().get("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "backend_url": get_env().get("E2E_BACKEND_URL", "http://localhost:8000"),
    "websocket_url": get_env().get("E2E_WEBSOCKET_URL", "ws://localhost:8000/ws"),
    "redis_url": get_env().get("E2E_REDIS_URL", "redis://localhost:6379"),
    "postgres_url": get_env().get("E2E_POSTGRES_URL", "postgresql://postgres:netra@localhost:5432/netra_test"),
    "clickhouse_url": get_env().get("E2E_CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_test"),
    "test_timeout": int(get_env().get("E2E_TEST_TIMEOUT", "300")),  # 5 minutes
    "performance_mode": get_env().get("E2E_PERFORMANCE_MODE", "true").lower() == "true"
}


class E2EEnvironmentValidator:
    """Validates E2E test environment prerequisites."""
    
    @staticmethod
    async def validate_services_available() -> Dict[str, bool]:
        """Validate that all required services are available."""
        try:
            import asyncpg
            import httpx
            import redis
        except ImportError:
            return {"import_error": True}
        
        service_status = {}
        
        # Check Auth Service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{E2E_CONFIG['auth_service_url']}/health", timeout=10.0)
                service_status["auth_service"] = response.status_code == 200
        except Exception:
            service_status["auth_service"] = False
        
        # Check Backend Service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{E2E_CONFIG['backend_url']}/health", timeout=10.0)
                service_status["backend"] = response.status_code == 200
        except Exception:
            service_status["backend"] = False
        
        # Check Redis
        try:
            redis_client = redis.Redis.from_url(E2E_CONFIG["redis_url"], decode_responses=True)
            await redis_client.ping()
            service_status["redis"] = True
            await redis_client.aclose() if hasattr(redis_client, 'aclose') else None
        except Exception:
            service_status["redis"] = False
        
        # Check PostgreSQL
        try:
            conn = await asyncpg.connect(E2E_CONFIG["postgres_url"])
            await conn.fetchval("SELECT 1")
            service_status["postgres"] = True
            await conn.close()
        except Exception:
            service_status["postgres"] = False
        
        return service_status
    
    @staticmethod
    def validate_environment_variables() -> Dict[str, bool]:
        """Validate required environment variables are set."""
        required_vars = [
            "GOOGLE_API_KEY",  # For real LLM testing
            "JWT_SECRET_KEY",  # For authentication
            "FERNET_KEY"       # For encryption
        ]
        
        var_status = {}
        for var in required_vars:
            var_status[var] = get_env().get(var) is not None
            
        return var_status


@pytest.fixture(scope="session")
async def validate_e2e_environment():
    """Validate E2E test environment before running tests."""
    e2e_logger.info("Validating E2E test environment...")
    
    # Skip E2E tests if not explicitly enabled
    if not get_env().get("RUN_E2E_TESTS", "false").lower() == "true":
        pytest.skip("E2E tests disabled (set RUN_E2E_TESTS=true to enable)")
    
    validator = E2EEnvironmentValidator()
    
    # Validate services
    service_status = await validator.validate_services_available()
    failed_services = [name for name, status in service_status.items() if not status]
    
    if failed_services:
        pytest.skip(f"Required services unavailable: {failed_services}")
    
    # Validate environment variables
    env_status = validator.validate_environment_variables()
    missing_vars = [var for var, status in env_status.items() if not status]
    
    if missing_vars:
        pytest.skip(f"Required environment variables missing: {missing_vars}")
    
    e2e_logger.info("E2E environment validation passed")
    return {
        "services": service_status,
        "environment": env_status,
        "config": E2E_CONFIG
    }


@pytest.fixture
def performance_monitor():
    """Monitor test performance and validate against requirements."""
    class PerformanceMonitor:
        def __init__(self):
            self.measurements = {}
            
        def start_measurement(self, operation: str):
            self.measurements[operation] = {"start": time.time()}
            
        def end_measurement(self, operation: str):
            if operation in self.measurements:
                self.measurements[operation]["duration"] = time.time() - self.measurements[operation]["start"]
                
        def validate_requirement(self, operation: str, max_duration: float = None):
            if operation not in self.measurements:
                raise ValueError(f"No measurement found for operation: {operation}")
                
            duration = self.measurements[operation]["duration"]
            max_allowed = max_duration or 10.0
            
            if duration > max_allowed:
                raise AssertionError(f"{operation} took {duration:.2f}s (max: {max_allowed}s)")
                
            return duration
    
    return PerformanceMonitor()


@pytest.fixture
def e2e_logger():
    """Provide specialized E2E test logger."""
    logger = logging.getLogger("e2e_test")
    logger.setLevel(logging.INFO)
    
    class E2ELogger:
        def __init__(self, base_logger):
            self.logger = base_logger
            
        def test_start(self, test_name: str):
            self.logger.info(f"[START] {test_name}")
            
        def test_success(self, test_name: str, duration: float):
            self.logger.info(f"[SUCCESS] {test_name} completed in {duration:.2f}s")
            
        def test_failure(self, test_name: str, error: str):
            self.logger.error(f"[FAILURE] {test_name} failed: {error}")
            
        def performance_metric(self, operation: str, duration: float, limit: float):
            status = "PASS" if duration <= limit else "FAIL"
            self.logger.info(f"[PERF-{status}] {operation}: {duration:.2f}s (limit: {limit}s)")
            
        def business_impact(self, message: str):
            self.logger.info(f"[BUSINESS] {message}")
    
    return E2ELogger(logger)


@pytest.fixture(autouse=True)
def setup_e2e_test_environment():
    """Auto-setup E2E test environment variables."""
    env = get_env()
    env.set("TESTING", "1", source="e2e_test_setup")
    env.set("NETRA_ENV", "e2e_testing", source="e2e_test_setup")
    env.set("USE_REAL_SERVICES", "true", source="e2e_test_setup")
    env.set("AUTH_FAST_TEST_MODE", "true", source="e2e_test_setup")
    
    # Set longer timeouts for E2E tests
    env.set("HTTP_TIMEOUT", "30", source="e2e_test_setup")
    env.set("WEBSOCKET_TIMEOUT", "30", source="e2e_test_setup")
    env.set("LLM_TIMEOUT", "60", source="e2e_test_setup")
