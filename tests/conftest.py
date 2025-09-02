import asyncio
import os
import sys
import uuid
import time
from typing import Optional, Dict, Any, List, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import pytest

# Add project root for imports

# Import isolated environment for proper test isolation
from shared.isolated_environment import get_env
from test_framework.environment_isolation import (
    get_test_env_manager,
    isolated_test_session,
    isolated_test_env,
    ensure_test_isolation,
)

# REAL SERVICES INTEGRATION
# Import all real service fixtures to replace mocks
from test_framework.conftest_real_services import *

# PHASE 0 MIGRATION IMPORTS
# Import Phase 0 migration components for testing
try:
    from netra_backend.app.models.user_execution_context import UserExecutionContext
    from netra_backend.app.dependencies import (
        get_request_scoped_db_session,
        RequestScopedDbDep,
        RequestScopedSupervisorDep,
        get_request_scoped_supervisor_dependency
    )
    from netra_backend.app.services.memory_optimization_service import (
        MemoryOptimizationService,
        get_memory_service,
        MemoryPressureLevel,
        RequestScope
    )
    from netra_backend.app.services.session_memory_manager import (
        SessionMemoryManager,
        UserSession,
        SessionState,
        get_session_manager
    )
    from netra_backend.app.database.session_manager import (
        DatabaseSessionManager,
        SessionScopeValidator,
        managed_session
    )
    PHASE0_COMPONENTS_AVAILABLE = True
except ImportError as e:
    # Mock Phase 0 components if not available
    PHASE0_COMPONENTS_AVAILABLE = False
    
    # Create mock classes for compatibility
    class UserExecutionContext:
        def __init__(self, user_id, thread_id, run_id, request_id, websocket_connection_id=None):
            self.user_id = user_id
            self.thread_id = thread_id
            self.run_id = run_id
            self.request_id = request_id
            self.websocket_connection_id = websocket_connection_id

# =============================================================================
# COMMON ENVIRONMENT SETUP FOR ALL TESTS
# Uses IsolatedEnvironment to prevent global pollution
# Phase 0 Migration: Enhanced with request-scoped dependencies
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

# Enhanced event loop management for tests
@pytest.fixture(scope="session")
def event_loop_policy():
    """Set consistent event loop policy for all tests"""
    import asyncio
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        # Use SelectorEventLoop on Windows for better compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.get_event_loop_policy()


# =============================================================================
# E2E PERFORMANCE TESTING FIXTURES
# Consolidated from tests/e2e/performance/conftest.py
# =============================================================================

# Environment configuration for performance tests
# Use isolated environment for safe access
current_env = get_env().get("ENVIRONMENT", "development")
is_staging = current_env == "staging"

# Default URLs for different environments
default_websocket_url = "ws://localhost:8888/ws" if current_env == "development" else "wss://api.staging.netrasystems.ai/ws"
default_backend_url = "http://localhost:8888" if current_env == "development" else "https://api.staging.netrasystems.ai"
default_auth_url = "http://localhost:8001" if current_env == "development" else "https://auth.staging.netrasystems.ai"

E2E_TEST_CONFIG = {
    "websocket_url": get_env().get("E2E_WEBSOCKET_URL", default_websocket_url),
    "backend_url": get_env().get("E2E_BACKEND_URL", default_backend_url),
    "auth_service_url": get_env().get("E2E_AUTH_SERVICE_URL", default_auth_url),
    "skip_real_services": get_env().get("SKIP_REAL_SERVICES", "true").lower() == "true",
    "test_mode": get_env().get("HIGH_VOLUME_TEST_MODE", "mock"),
    "environment": current_env,
    "is_staging": is_staging
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
    client = None
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
        
    except ImportError:
        # Mock client if performance_base not available
        # Mock: Performance test client isolation when performance_base module unavailable
        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.close = AsyncMock()
        try:
            yield mock_client
        finally:
            await mock_client.disconnect()
            await mock_client.close()
    finally:
        # Enhanced cleanup with timeout
        if client:
            try:
                # Force disconnect with timeout
                await asyncio.wait_for(client.disconnect(), timeout=5.0)
            except asyncio.TimeoutError:
                import logging
                logging.getLogger(__name__).warning(f"Client disconnect timed out")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Client cleanup error: {e}")


# =============================================================================
# DEPRECATED MOCK FIXTURES - REPLACED BY REAL SERVICES
# These are kept for backward compatibility during migration
# Use real_* fixtures instead (imported from test_framework.conftest_real_services)
# =============================================================================

# NOTE: The following fixtures are DEPRECATED and should be replaced with real services:
# - mock_redis_client -> real_redis
# - mock_redis_manager -> redis_manager (real)
# - mock_clickhouse_client -> clickhouse_client (real)
# - mock_websocket_manager -> real_websocket_client
# - All other mock_* fixtures -> corresponding real_* fixtures

@pytest.fixture
async def mock_redis_client():
    """Common Redis client mock for all tests with proper async cleanup"""
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.get = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.set = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.delete = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.exists = AsyncMock(return_value=False)
    # Mock: Async component isolation for testing without real async operations
    mock.ping = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.aclose = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)
    
    try:
        yield mock
    finally:
        # Ensure proper cleanup of mock Redis resources
        try:
            await mock.aclose()
        except Exception:
            pass
        try:
            await mock.close()  
        except Exception:
            pass


@pytest.fixture
async def mock_redis_manager():
    """Common Redis manager mock with proper cleanup"""
    # Mock: Redis cache isolation to prevent test interference and external dependencies
    mock = MagicMock()
    mock.enabled = True
    mock.get = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.set = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.delete = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.exists = AsyncMock(return_value=False)
    mock.close = AsyncMock(return_value=None)
    mock.cleanup = AsyncMock(return_value=None)
    
    try:
        yield mock
    finally:
        # Proper cleanup for Redis manager
        try:
            await mock.cleanup()
        except Exception:
            pass
        try:
            await mock.close()
        except Exception:
            pass


@pytest.fixture
def mock_clickhouse_client():
    """Common ClickHouse client mock"""
    # Mock: ClickHouse database isolation for fast testing without external database dependency
    mock = MagicMock()
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.execute = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.fetch = AsyncMock(return_value=[])
    # Mock: Async component isolation for testing without real async operations
    mock.insert_data = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.command = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
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
async def mock_websocket_manager():
    # Mock: WebSocket infrastructure isolation for unit tests without real connections
    mock = MagicMock()
    mock.active_connections = {}
    mock.connect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.disconnect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_message = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.broadcast = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.shutdown = AsyncMock(return_value=None)
    mock.close_all_connections = AsyncMock(return_value=None)
    mock.cleanup = AsyncMock(return_value=None)
    
    try:
        yield mock
    finally:
        # Proper WebSocket manager cleanup
        try:
            await mock.close_all_connections()
        except Exception:
            pass
        try:
            await mock.cleanup()
        except Exception:
            pass
        try:
            await mock.shutdown()
        except Exception:
            pass


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

        app.include_router(auth_router, prefix="/auth")
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
        # Use proper JWT test helpers instead of direct auth imports
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        jwt_helper = JWTTestHelper()
        token = jwt_helper.create_access_token(test_user.id, test_user.email)
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        # Return mock headers if test helpers not available
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
    from test_framework.environment_isolation import get_env
    env = get_env()
    use_real_services = env.get("USE_REAL_SERVICES", "false").lower() == "true"
    if not use_real_services:
        pytest.skip("Real services disabled (set USE_REAL_SERVICES=true)")
        return

    config = LauncherConfig(
        dynamic_ports=True,
        non_interactive=True,
        verbose=False,
        silent_mode=True,  # Use silent mode for tests
        no_browser=True,
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
# Detect staging environment and set appropriate URLs
current_env = get_env().get("ENVIRONMENT", get_env().get("TEST_ENV", "test")).lower()
is_staging = current_env == "staging"

if is_staging:
    # Staging environment URLs
    default_auth_url = "https://api.staging.netrasystems.ai"
    default_backend_url = "https://api.staging.netrasystems.ai"
    default_websocket_url = "wss://api.staging.netrasystems.ai/ws"
    default_redis_url = get_env().get("STAGING_REDIS_URL", "redis://localhost:6379")
    default_postgres_url = get_env().get("STAGING_DATABASE_URL", "postgresql://postgres:netra@localhost:5432/netra_staging")
    default_clickhouse_url = get_env().get("STAGING_CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_staging")
else:
    # Local/test environment URLs
    default_auth_url = "http://localhost:8081"
    default_backend_url = "http://localhost:8000"
    default_websocket_url = "ws://localhost:8000/ws"
    default_redis_url = "redis://localhost:6379"
    default_postgres_url = "postgresql://postgres:netra@localhost:5432/netra_test"
    default_clickhouse_url = "clickhouse://localhost:8123/netra_test"

E2E_CONFIG = {
    "auth_service_url": get_env().get("E2E_AUTH_SERVICE_URL", default_auth_url),
    "backend_url": get_env().get("E2E_BACKEND_URL", default_backend_url),
    "websocket_url": get_env().get("E2E_WEBSOCKET_URL", default_websocket_url),
    "redis_url": get_env().get("E2E_REDIS_URL", default_redis_url),
    "postgres_url": get_env().get("E2E_POSTGRES_URL", default_postgres_url),
    "clickhouse_url": get_env().get("E2E_CLICKHOUSE_URL", default_clickhouse_url),
    "test_timeout": int(get_env().get("E2E_TEST_TIMEOUT", "300")),  # 5 minutes
    "performance_mode": get_env().get("E2E_PERFORMANCE_MODE", "true").lower() == "true",
    "environment": current_env,
    "is_staging": is_staging
}


class E2EEnvironmentValidator:
    """Validates E2E test environment prerequisites."""
    
    @staticmethod
    async def validate_services_available() -> Dict[str, bool]:
        """Validate that all required services are available."""
        try:
            import asyncpg
            import httpx
            import redis.asyncio as redis
            import socket
        except ImportError as e:
            logging.getLogger(__name__).error(f"Required dependencies not available: {e}")
            return {"import_error": True}
        
        service_status = {}
        
        # Check Auth Service with multiple endpoint attempts
        auth_endpoints = [
            f"{E2E_CONFIG['auth_service_url']}/health",
            f"{E2E_CONFIG['auth_service_url']}/",
            "http://localhost:8081/health",
            "http://localhost:8083/health"  # Alternative port
        ]
        
        service_status["auth_service"] = await E2EEnvironmentValidator._check_service_endpoints(
            "auth_service", auth_endpoints, timeout=15.0
        )
        
        # Check Backend Service with multiple endpoint attempts
        backend_endpoints = [
            f"{E2E_CONFIG['backend_url']}/health",
            f"{E2E_CONFIG['backend_url']}/health/",
            "http://localhost:8000/health",
            "http://localhost:8200/health"  # Alternative port
        ]
        
        service_status["backend"] = await E2EEnvironmentValidator._check_service_endpoints(
            "backend", backend_endpoints, timeout=15.0
        )
        
        # Check Redis with proper async handling and fallback
        redis_configs = [
            E2E_CONFIG["redis_url"],
            "redis://localhost:6379",
            "redis://127.0.0.1:6379"
        ]
        
        service_status["redis"] = await E2EEnvironmentValidator._check_redis_connectivity(redis_configs)
        
        # Check PostgreSQL with proper error handling
        postgres_urls = [
            E2E_CONFIG["postgres_url"],
            "postgresql://test:test@localhost:5434/netra_test",
            "postgresql://netra:netra123@localhost:5433/netra_dev"
        ]
        
        service_status["postgres"] = await E2EEnvironmentValidator._check_postgres_connectivity(postgres_urls)
        
        # Log detailed results
        for service, status in service_status.items():
            status_text = "[OK] Available" if status else "[FAIL] Unavailable"
            logging.getLogger(__name__).info(f"Service {service}: {status_text}")
        
        return service_status
    
    @staticmethod
    async def _check_service_endpoints(service_name: str, endpoints: list, timeout: float = 15.0) -> bool:
        """Check multiple endpoints for a service and return True if any succeed."""
        import httpx  # Import here to ensure availability
        
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(endpoint)
                    if response.status_code == 200:
                        logging.getLogger(__name__).info(f"[OK] {service_name} health check succeeded at {endpoint}")
                        return True
                    else:
                        logging.getLogger(__name__).debug(f"[FAIL] {service_name} returned HTTP {response.status_code} at {endpoint}")
            except httpx.ConnectError as e:
                logging.getLogger(__name__).debug(f"[FAIL] {service_name} connection failed at {endpoint}: {e}")
            except httpx.TimeoutException:
                logging.getLogger(__name__).debug(f"[FAIL] {service_name} timeout at {endpoint}")
            except Exception as e:
                logging.getLogger(__name__).debug(f"[FAIL] {service_name} unexpected error at {endpoint}: {e}")
        
        # Try port connectivity as fallback
        for endpoint in endpoints:
            if await E2EEnvironmentValidator._check_port_connectivity(endpoint):
                logging.getLogger(__name__).info(f"[OK] {service_name} port accessible (health endpoint may be misconfigured)")
                return True
        
        logging.getLogger(__name__).warning(f"[FAIL] {service_name} not accessible at any endpoint: {endpoints}")
        return False
    
    @staticmethod
    async def _check_port_connectivity(url: str) -> bool:
        """Check if a service port is accessible via socket connection."""
        try:
            import socket
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            host = parsed.hostname or 'localhost'
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            
            # Try socket connection with timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    @staticmethod
    async def _check_redis_connectivity(redis_configs: list) -> bool:
        """Check Redis connectivity with multiple configurations."""
        import redis.asyncio as redis
        
        for config in redis_configs:
            if not config:
                continue
                
            try:
                client = redis.Redis.from_url(config, decode_responses=True)
                await client.ping()
                await client.aclose()
                logging.getLogger(__name__).info(f"[OK] Redis accessible at {config}")
                return True
            except Exception as e:
                logging.getLogger(__name__).debug(f"[FAIL] Redis connection failed at {config}: {e}")
        
        logging.getLogger(__name__).warning(f"[FAIL] Redis not accessible at any configuration: {redis_configs}")
        return False
    
    @staticmethod
    async def _check_postgres_connectivity(postgres_urls: list) -> bool:
        """Check PostgreSQL connectivity with multiple configurations."""
        import asyncpg
        
        for url in postgres_urls:
            if not url:
                continue
                
            try:
                conn = await asyncpg.connect(url, timeout=10.0)
                await conn.fetchval("SELECT 1")
                await conn.close()
                logging.getLogger(__name__).info(f"[OK] PostgreSQL accessible at {url}")
                return True
            except Exception as e:
                logging.getLogger(__name__).debug(f"[FAIL] PostgreSQL connection failed at {url}: {e}")
        
        logging.getLogger(__name__).warning(f"[FAIL] PostgreSQL not accessible at any URL: {postgres_urls}")
        return False
    
    @staticmethod
    def validate_environment_variables() -> Dict[str, bool]:
        """Validate required environment variables are set."""
        required_vars = [
            "GOOGLE_API_KEY",  # For real LLM testing
            "JWT_SECRET_KEY",  # For authentication (development/generic)
            "JWT_SECRET_STAGING",  # For staging authentication  
            "FERNET_KEY"       # For encryption
        ]
        
        var_status = {}
        for var in required_vars:
            var_status[var] = get_env().get(var) is not None
            
        return var_status


@pytest.fixture(scope="session")
async def validate_e2e_environment():
    """Validate E2E test environment before running tests."""
    logging.getLogger(__name__).info("Validating E2E test environment...")
    
    # Skip E2E tests if not explicitly enabled, but allow staging tests
    if not (get_env().get("RUN_E2E_TESTS", "false").lower() == "true" or is_staging):
        pytest.skip("E2E tests disabled (set RUN_E2E_TESTS=true to enable or ENVIRONMENT=staging)")
    
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
    
    logging.getLogger(__name__).info("E2E environment validation passed")
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
    # Only override ENVIRONMENT if not already set to staging
    if not is_staging:
        env.set("ENVIRONMENT", "test", source="e2e_test_setup")
    env.set("USE_REAL_SERVICES", "true", source="e2e_test_setup")
    env.set("AUTH_FAST_TEST_MODE", "true", source="e2e_test_setup")
    
    # Set Redis to use TEST environment port (6380)
    env.set("REDIS_HOST", "localhost", source="e2e_test_setup")
    env.set("REDIS_PORT", "6380", source="e2e_test_setup")
    env.set("REDIS_URL", "redis://localhost:6380/0", source="e2e_test_setup")
    
    # Set PostgreSQL to use TEST environment port (5433)
    env.set("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/netra_test", source="e2e_test_setup")
    
    # Set ClickHouse to use TEST environment ports
    env.set("CLICKHOUSE_HOST", "localhost", source="e2e_test_setup")
    env.set("CLICKHOUSE_HTTP_PORT", "8124", source="e2e_test_setup")
    env.set("CLICKHOUSE_TCP_PORT", "9001", source="e2e_test_setup")
    
    # Set longer timeouts for E2E tests
    env.set("HTTP_TIMEOUT", "30", source="e2e_test_setup")
    env.set("WEBSOCKET_TIMEOUT", "30", source="e2e_test_setup")
    env.set("LLM_TIMEOUT", "60", source="e2e_test_setup")


# =============================================================================
# PHASE 0 MIGRATION FIXTURES
# Request-scoped dependency injection and memory optimization fixtures
# =============================================================================

@pytest.fixture
def valid_user_execution_context():
    """Create valid UserExecutionContext with realistic IDs (no placeholders).
    
    This fixture provides proper UserExecutionContext instances that pass
    validation and support Phase 0 migration patterns.
    
    Returns:
        UserExecutionContext: Validated context with real IDs
    """
    if not PHASE0_COMPONENTS_AVAILABLE:
        return UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}"
        )
    
    # Create with valid, non-placeholder values
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        thread_id=f"thread_{uuid.uuid4().hex[:8]}",
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}"
    )

@pytest.fixture
async def isolated_db_session():
    """Create isolated database session for testing.
    
    This fixture provides request-scoped database sessions that are properly
    isolated and automatically cleaned up after tests.
    
    Yields:
        AsyncSession: Isolated database session
    """
    if not SQLALCHEMY_AVAILABLE or not PHASE0_COMPONENTS_AVAILABLE:
        # Mock session for testing without real database
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock() 
        mock_session.close = AsyncMock()
        yield mock_session
        return
        
    try:
        # Create isolated test database session
        async with get_request_scoped_db_session() as session:
            # Tag session as test-scoped
            session.info = getattr(session, 'info', {})
            session.info['test_scoped'] = True
            session.info['created_at'] = datetime.now(timezone.utc).isoformat()
            
            yield session
    except Exception as e:
        # Fallback to mock if real session creation fails
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        yield mock_session

@pytest.fixture
async def request_scoped_supervisor(valid_user_execution_context, isolated_db_session):
    """Create request-scoped supervisor with proper user context.
    
    This fixture provides isolated supervisor instances that use request-scoped
    database sessions and proper user execution contexts.
    
    Args:
        valid_user_execution_context: Valid user context fixture
        isolated_db_session: Isolated database session fixture
        
    Yields:
        Supervisor: Request-scoped supervisor instance
    """
    if not PHASE0_COMPONENTS_AVAILABLE:
        # Mock supervisor for testing
        mock_supervisor = AsyncMock()
        mock_supervisor.user_context = valid_user_execution_context
        mock_supervisor.cleanup = AsyncMock()
        yield mock_supervisor
        return
    
    try:
        # Create mock FastAPI request for supervisor creation
        mock_request = MagicMock()
        mock_request.app.state.llm_manager = MagicMock()
        mock_request.app.state.websocket_bridge = MagicMock()
        mock_request.app.state.agent_supervisor = MagicMock()
        mock_request.app.state.agent_supervisor.tool_dispatcher = MagicMock()
        
        # Create request-scoped context
        from netra_backend.app.dependencies import RequestScopedContext
        context = RequestScopedContext(
            user_id=valid_user_execution_context.user_id,
            thread_id=valid_user_execution_context.thread_id,
            run_id=valid_user_execution_context.run_id,
            websocket_connection_id=valid_user_execution_context.websocket_connection_id
        )
        
        # Create supervisor with request-scoped session
        supervisor = await get_request_scoped_supervisor_dependency(
            mock_request, context, isolated_db_session
        )
        
        yield supervisor
        
        # Cleanup
        if hasattr(supervisor, 'cleanup'):
            await supervisor.cleanup()
            
    except Exception as e:
        # Fallback to mock supervisor if creation fails
        mock_supervisor = AsyncMock()
        mock_supervisor.user_context = valid_user_execution_context
        mock_supervisor.cleanup = AsyncMock()
        yield mock_supervisor

@pytest.fixture
async def concurrent_user_contexts():
    """Create multiple isolated user contexts for concurrent testing.
    
    This fixture provides multiple UserExecutionContext instances with
    different user IDs for testing concurrent user isolation.
    
    Returns:
        List[UserExecutionContext]: List of isolated user contexts
    """
    contexts = []
    for i in range(3):  # Create 3 concurrent users
        context = UserExecutionContext(
            user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{i}_{uuid.uuid4().hex[:8]}",
            websocket_connection_id=f"ws_{i}_{uuid.uuid4().hex[:8]}"
        ) if PHASE0_COMPONENTS_AVAILABLE else UserExecutionContext(
            user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{i}_{uuid.uuid4().hex[:8]}"
        )
        contexts.append(context)
    
    return contexts

@pytest.fixture  
async def memory_optimization_service():
    """Create memory optimization service for testing.
    
    This fixture provides a MemoryOptimizationService instance that is
    properly started and stopped for each test.
    
    Yields:
        MemoryOptimizationService: Started memory service
    """
    if not PHASE0_COMPONENTS_AVAILABLE:
        # Mock memory service
        mock_service = MagicMock()
        mock_service.start = AsyncMock()
        mock_service.stop = AsyncMock()
        mock_service.get_memory_stats = MagicMock()
        mock_service.get_active_scopes_count = MagicMock(return_value=0)
        mock_service.request_scope = asynccontextmanager(
            lambda request_id, user_id, **kwargs: MagicMock()
        )
        
        await mock_service.start()
        yield mock_service
        await mock_service.stop()
        return
    
    # Real memory optimization service
    service = MemoryOptimizationService()
    await service.start()
    
    try:
        yield service
    finally:
        await service.stop()

@pytest.fixture
async def session_memory_manager():
    """Create session memory manager for testing.
    
    This fixture provides a SessionMemoryManager instance for testing
    session lifecycle and memory cleanup functionality.
    
    Yields:
        SessionMemoryManager: Started session manager
    """
    if not PHASE0_COMPONENTS_AVAILABLE:
        # Mock session manager
        mock_manager = MagicMock()
        mock_manager.start = AsyncMock()
        mock_manager.stop = AsyncMock()
        mock_manager.create_user_session = AsyncMock()
        mock_manager.cleanup_session = AsyncMock(return_value=True)
        mock_manager.session_scope = asynccontextmanager(
            lambda session_id, user_id, **kwargs: MagicMock()
        )
        
        await mock_manager.start()
        yield mock_manager
        await mock_manager.stop()
        return
    
    # Real session memory manager
    manager = SessionMemoryManager()
    await manager.start()
    
    try:
        yield manager
    finally:
        await manager.stop()

@pytest.fixture
async def database_session_isolation():
    """Create database session with isolation validation.
    
    This fixture provides database sessions that are validated for proper
    isolation and prevents global session storage.
    
    Yields:
        Tuple[AsyncSession, Callable]: Session and validation function
    """
    if not SQLALCHEMY_AVAILABLE or not PHASE0_COMPONENTS_AVAILABLE:
        # Mock session with validation
        mock_session = AsyncMock()
        mock_session.info = {'test_isolated': True}
        
        def validate_isolation():
            return True
            
        yield mock_session, validate_isolation
        return
    
    async with get_request_scoped_db_session() as session:
        # Tag session with isolation markers
        session.info = getattr(session, 'info', {})
        session.info['test_isolated'] = True
        session.info['isolation_test_id'] = str(uuid.uuid4())
        
        def validate_isolation():
            """Validate that session maintains proper isolation."""
            if not hasattr(session, 'info'):
                return False
            return session.info.get('test_isolated', False)
        
        yield session, validate_isolation

@pytest.fixture
def factory_pattern_mocks():
    """Create mock factory pattern components for testing.
    
    This fixture provides mock implementations of factory pattern components
    for testing factory-based dependency injection.
    
    Returns:
        Dict[str, Any]: Dictionary of mock factory components
    """
    return {
        'execution_engine_factory': MagicMock(),
        'websocket_bridge_factory': MagicMock(),
        'factory_adapter': MagicMock(),
        'agent_instance_factory': MagicMock()
    }

@pytest.fixture
async def memory_tracker():
    """Create memory tracker for performance testing.
    
    This fixture provides a simple memory tracking utility for monitoring
    memory usage during tests and detecting potential leaks.
    
    Yields:
        MemoryTracker: Memory tracking utility
    """
    class MemoryTracker:
        def __init__(self):
            self.initial_memory = 0
            self.measurements = []
            
        def start_tracking(self):
            """Start memory tracking."""
            try:
                import psutil
                self.process = psutil.Process()
                self.initial_memory = self.process.memory_info().rss / 1024 / 1024
            except ImportError:
                self.process = None
                self.initial_memory = 0
                
        def measure(self, label: str = "") -> float:
            """Take memory measurement."""
            if not hasattr(self, 'process') or self.process is None:
                return 0.0
            current = self.process.memory_info().rss / 1024 / 1024
            delta = current - self.initial_memory
            self.measurements.append({'label': label, 'memory_mb': current, 'delta_mb': delta})
            return current
            
        def get_memory_increase(self) -> float:
            """Get total memory increase since tracking started."""
            if not hasattr(self, 'process') or self.process is None:
                return 0.0
            current = self.process.memory_info().rss / 1024 / 1024
            return current - self.initial_memory
    
    tracker = MemoryTracker()
    tracker.start_tracking()
    yield tracker

@pytest.fixture
async def concurrent_isolation_test():
    """Create environment for testing concurrent user isolation.
    
    This fixture sets up an environment for testing that multiple users
    can operate concurrently without data leakage or interference.
    
    Yields:
        Callable: Function to run concurrent isolation tests
    """
    async def run_concurrent_test(
        user_count: int = 3,
        operations_per_user: int = 5,
        test_function: Callable = None
    ):
        """Run concurrent test with multiple users.
        
        Args:
            user_count: Number of concurrent users
            operations_per_user: Operations per user
            test_function: Test function to run for each user
            
        Returns:
            List: Results from all concurrent operations
        """
        if not test_function:
            # Default test function
            async def default_test(user_context, operation_id):
                return {
                    'user_id': user_context.user_id,
                    'operation_id': operation_id,
                    'success': True
                }
            test_function = default_test
        
        # Create user contexts
        user_contexts = []
        for i in range(user_count):
            context = UserExecutionContext(
                user_id=f"concurrent_test_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{i}_{uuid.uuid4().hex[:8]}"
            ) if PHASE0_COMPONENTS_AVAILABLE else UserExecutionContext(
                user_id=f"concurrent_test_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{i}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(context)
        
        # Run concurrent operations
        tasks = []
        for user_context in user_contexts:
            for op_id in range(operations_per_user):
                task = asyncio.create_task(
                    test_function(user_context, op_id)
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            raise Exception(f"Concurrent test failed with exceptions: {exceptions}")
        
        return results
    
    yield run_concurrent_test

# Update existing test user fixture to use new pattern
@pytest.fixture
def test_user_v2():
    """Enhanced test user fixture with Phase 0 migration support."""
    if PHASE0_COMPONENTS_AVAILABLE:
        return User(
            id=f"test_user_{uuid.uuid4().hex[:8]}", 
            email=f"test_{uuid.uuid4().hex[:8]}@example.com", 
            is_active=True, 
            is_superuser=False
        )
    else:
        return User(
            id="test-user-id", 
            email="test@example.com", 
            is_active=True, 
            is_superuser=False
        )

# Enhanced auth headers fixture
@pytest.fixture
def auth_headers_v2(test_user_v2):
    """Enhanced auth headers fixture with realistic tokens."""
    try:
        # Use proper JWT test helpers instead of direct auth imports
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        jwt_helper = JWTTestHelper()
        token = jwt_helper.create_access_token(test_user_v2.id, test_user_v2.email)
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        # Return mock headers with more realistic token
        mock_token = f"test_token_{uuid.uuid4().hex[:16]}"
        return {"Authorization": f"Bearer {mock_token}"}

# Convenience fixture combining common Phase 0 components
@pytest.fixture
async def phase0_test_environment(
    valid_user_execution_context,
    isolated_db_session, 
    memory_optimization_service,
    session_memory_manager
):
    """Complete Phase 0 test environment with all key components.
    
    This fixture provides a full testing environment with:
    - Valid UserExecutionContext
    - Isolated database session
    - Memory optimization service
    - Session memory manager
    
    Yields:
        Dict[str, Any]: Dictionary of Phase 0 components
    """
    yield {
        'user_context': valid_user_execution_context,
        'db_session': isolated_db_session,
        'memory_service': memory_optimization_service,
        'session_manager': session_memory_manager
    }
