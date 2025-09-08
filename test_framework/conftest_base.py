"""
Unified base conftest fixtures for all test infrastructure.
Consolidates common fixtures from multiple conftest.py files across the project.

This module provides:
- Docker Compose based test infrastructure (default)
- Common environment setup
- Shared mock fixtures  
- Database fixtures
- WebSocket test fixtures
- Authentication fixtures
- Service mocks

USAGE: Import specific fixtures in service-specific conftest.py files as needed.

TEST INFRASTRUCTURE:
By default, tests use Docker Compose for service isolation. This can be controlled via:
- TEST_SERVICE_MODE=docker (default) - Use Docker Compose
- TEST_SERVICE_MODE=local - Use dev_launcher (legacy)  
- TEST_SERVICE_MODE=mock - Use mocks only (no real services)
"""

import asyncio
import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import Docker test manager for service orchestration
from test_framework.docker_test_manager import (
    DockerTestManager,
    ServiceMode
)

# Singleton instance of DockerTestManager
_test_manager_instance = None

def get_test_manager() -> DockerTestManager:
    """Get or create the singleton DockerTestManager instance."""
    global _test_manager_instance
    if _test_manager_instance is None:
        _test_manager_instance = DockerTestManager()
    return _test_manager_instance

# Use centralized environment management for test framework
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            import os
            return os.environ.get(key, default)  # @marked: Fallback environment wrapper
        def set(self, key, value, source="test_framework"):
            import os
            os.environ[key] = value  # @marked: Fallback environment wrapper
        def enable_isolation(self):
            pass
    
    def get_env():
        return FallbackEnv()

# =============================================================================
# ENVIRONMENT SETUP - COMMON FOR ALL TESTS
# =============================================================================

# Set base testing environment variables using IsolatedEnvironment
# CRITICAL: Only set test environment if we're actually running tests
if "pytest" in sys.modules or get_env().get("PYTEST_CURRENT_TEST"):
    env = get_env()
    env.enable_isolation()  # Enable isolation for all tests
    
    env.set("TESTING", "1", "test_framework_base")
    env.set("NETRA_ENV", "testing", "test_framework_base")
    env.set("ENVIRONMENT", "testing", "test_framework_base")
    env.set("LOG_LEVEL", "INFO", "test_framework_base")
    
    # Network and service configuration
    env.set("REDIS_HOST", "localhost", "test_framework_base")
    env.set("CLICKHOUSE_HOST", "localhost", "test_framework_base")
    env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test_framework_base")
    
    # Authentication secrets required for tests
    env.set("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-do-not-use-in-production", "test_framework_base")
    env.set("SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production", "test_framework_base")
    
    # FastMCP home directory workaround for Windows compatibility
    # Ensures Path.home() works correctly in FastMCP settings initialization
    from pathlib import Path
    if os.name == 'nt':  # Windows
        # Ensure HOME is set for FastMCP compatibility
        if not env.get("HOME"):
            userprofile = env.get("USERPROFILE") 
            if userprofile:
                env.set("HOME", userprofile, "test_framework_fastmcp_workaround")
            else:
                # Last resort fallback
                homedrive = env.get("HOMEDRIVE", "C:")
                homepath = env.get("HOMEPATH", "\\Users\\Default")
                env.set("HOME", f"{homedrive}{homepath}", "test_framework_fastmcp_workaround")
        
        # Verify Path.home() will work before FastMCP imports
        try:
            Path.home()
        except (OSError, RuntimeError) as e:
            # If Path.home() still fails, set a test-safe directory
            import tempfile
            test_home = os.path.join(tempfile.gettempdir(), "test_home")
            os.makedirs(test_home, exist_ok=True)
            env.set("HOME", test_home, "test_framework_fastmcp_fallback")
    env.set("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-32-chars-minimum-length", "test_framework_base")
    env.set("SERVICE_ID", "test-service-auth", "test_framework_base")
    env.set("FERNET_KEY", "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao=", "test_framework_base")
    env.set("ENCRYPTION_KEY", "test-encryption-key-32-chars-long", "test_framework_base")
    
    # Disable heavy services for faster testing
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test_framework_base")
    env.set("CLICKHOUSE_ENABLED", "false", "test_framework_base")
    env.set("TEST_DISABLE_REDIS", "true", "test_framework_base")
    
    # CRITICAL: Set TEST_DISABLE_REDIS for cross-service test configuration consistency
    # Note: This is a legacy compatibility requirement for auth_service
    # TODO: Migrate auth_service to use IsolatedEnvironment
    import os as os_legacy
    os_legacy.environ["TEST_DISABLE_REDIS"] = "true"  # @marked: Cross-service test config - legacy compatibility

# =============================================================================
# COMMON FIXTURES
# =============================================================================

@pytest.fixture
def common_test_user():
    """Common test user data for all services"""
    return {
        "id": "test-user-123",
        "email": "test@example.com", 
        "name": "Test User",
        "is_active": True,
        "is_superuser": False
    }

@pytest.fixture
def sample_data():
    """Basic sample data for tests"""
    return {"test": "data", "status": "active"}

# =============================================================================
# REDIS MOCKS
# =============================================================================

@pytest.fixture
def mock_redis_client():
    """Common Redis client mock for all tests"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    mock.connect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
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
    return mock

@pytest.fixture
def mock_redis_manager():
    """Common Redis manager mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    mock.enabled = True
    # Mock: Async component isolation for testing without real async operations
    mock.get = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.set = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.delete = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.exists = AsyncMock(return_value=False)
    return mock

# =============================================================================
# WEBSOCKET FIXTURES
# =============================================================================

@pytest.fixture
def mock_websocket_manager():
    """Unified WebSocket manager mock for all services"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    mock.active_connections = {}
    # Mock: Async component isolation for testing without real async operations
    mock.connect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.disconnect = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_message = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.broadcast = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.shutdown = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_upgrade_prompt = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_tier_limits_warning = AsyncMock(return_value=None)
    # Mock: Security service isolation for auth testing without real token validation
    mock.send_security_confirmation = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_dashboard_update = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_onboarding_update = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_optimization_results = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_optimization_result = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_dashboard_ready = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_team_upgrade_offer = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_purchase_confirmation = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.send_sharing_ready = AsyncMock(return_value=None)
    return mock

# =============================================================================  
# SERVICE MOCKS
# =============================================================================

@pytest.fixture
def mock_clickhouse_client():
    """Common ClickHouse client mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    mock.execute = AsyncMock(return_value=[])
    # Mock: Async component isolation for testing without real async operations
    mock.insert = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.close = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_llm_manager():
    """Common LLM manager mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock.get_llm = MagicMock(return_value=MagicMock())
    # Mock: Async component isolation for testing without real async operations
    mock.generate_response = AsyncMock(return_value={
        "content": "Test response",
        "model": "test-model", 
        "tokens_used": 10,
        "cost": 0.001
    })
    return mock

@pytest.fixture
def mock_background_task_manager():
    """Common background task manager mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_key_manager():
    """Common key manager mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: Service component isolation for predictable testing behavior
    mock.load_from_settings = MagicMock(return_value=mock)
    return mock

@pytest.fixture
def mock_security_service():
    """Common security service mock"""
    # Mock: Generic component isolation for controlled unit testing
    return MagicMock()

@pytest.fixture
def mock_tool_dispatcher():
    """Common tool dispatcher mock"""
    # Mock: Generic component isolation for controlled unit testing
    return MagicMock()

@pytest.fixture
def mock_agent_supervisor():
    """Common agent supervisor mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_agent_service():
    """Common agent service mock"""
    # Mock: Generic component isolation for controlled unit testing
    mock = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    mock.process_message = AsyncMock(return_value={
        "response": "Test response", 
        "metadata": {"test": True}
    })
    return mock

# =============================================================================
# AUTHENTICATION FIXTURES  
# =============================================================================

@pytest.fixture
def mock_auth_redis():
    """Auth-specific Redis mock for session management"""
    # Mock: Generic component isolation for controlled unit testing
    mock = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    mock.ping = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.get = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.set = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.setex = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.delete = AsyncMock(return_value=True)
    # Mock: Async component isolation for testing without real async operations
    mock.exists = AsyncMock(return_value=False)
    return mock

@pytest.fixture
def test_user_data():
    """Test user data for OAuth tests"""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User", 
        "provider": "google"
    }

# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture
def mock_database_factory():
    """Mock database session factory for tests"""
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session = AsyncMock()
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.commit = AsyncMock()
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.rollback = AsyncMock()
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.close = AsyncMock()
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.add = MagicMock()
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.execute = AsyncMock()
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.get = AsyncMock()
    mock_session.id = "mock_session_id"
    
    class MockSessionFactory:
        def __call__(self):
            return self
            
        async def __aenter__(self):
            return mock_session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
    
    return MockSessionFactory()

# =============================================================================
# E2E TEST CONFIGURATION  
# =============================================================================

@pytest.fixture
def e2e_test_config():
    """Common E2E test configuration"""
    # Get environment through isolated environment
    env = get_env()
    return {
        "websocket_url": env.get("E2E_WEBSOCKET_URL", "ws://localhost:8765"),
        "backend_url": env.get("E2E_BACKEND_URL", "http://localhost:8000"),
        "auth_service_url": env.get("E2E_AUTH_SERVICE_URL", "http://localhost:8081"),
        "skip_real_services": env.get("SKIP_REAL_SERVICES", "true").lower() == "true",
        "test_mode": env.get("HIGH_VOLUME_TEST_MODE", "mock"),
        "timeout": int(env.get("E2E_TEST_TIMEOUT", "300")),
        "performance_mode": env.get("E2E_PERFORMANCE_MODE", "true").lower() == "true"
    }

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

@pytest.fixture
def performance_monitor():
    """Monitor test performance and validate against requirements"""
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

# =============================================================================
# LOGGING FIXTURES
# =============================================================================

@pytest.fixture
def e2e_logger():
    """Specialized E2E test logger"""
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

# =============================================================================
# PYTEST HOOKS FOR SERVICE ENABLEMENT
# =============================================================================

def pytest_collection_modifyitems(config, items):
    """Enable services for tests that require them."""
    env = get_env()
    
    # Check if any tests need ClickHouse (marked with real_database)
    needs_clickhouse = False
    for item in items:
        if item.get_closest_marker('real_database'):
            needs_clickhouse = True
            break
    
    # Enable ClickHouse if needed and set marker for runtime detection
    if needs_clickhouse:
        env.set("CLICKHOUSE_ENABLED", "true", "test_framework_real_database")
        env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", "test_framework_real_database")
        env.set("PYTEST_REAL_DATABASE_TEST", "true", "test_framework_real_database")

# =============================================================================
# ASYNC UTILITIES
# =============================================================================

@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function to prevent async issues"""
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

# =============================================================================
# TEST DATA FACTORIES
# =============================================================================

@pytest.fixture
def isolated_test_users():
    """Create isolated test users for concurrent testing"""
    users = []
    for i in range(5):
        # Mock: Generic component isolation for controlled unit testing
        user = MagicMock()
        user.user_id = f"test_user_{i}"
        user.email = f"test{i}@example.com"
        user.session_id = f"session_{i}"
        user.auth_token = f"token_{i}"
        user.websocket_client = None
        user.agent_instance_id = None
        user.startup_metrics = {}
        user.sensitive_data = {"test_data": f"sensitive_{i}"}
        user.context_data = {"budget": 1000 * i, "region": "us-east-1"}
        users.append(user)
    
    return users

# =============================================================================
# DOCKER TEST SERVICE MANAGEMENT 
# =============================================================================

@pytest.fixture(scope="session")
async def docker_test_manager():
    """
    Session-scoped Docker test service manager.
    Automatically starts and stops test services for the entire test session.
    """
    manager = get_test_manager()
    manager.configure_mock_environment()
    
    # Start core services (postgres, redis) by default
    # Tests requiring additional services can start them separately
    await manager.start_services(
        services=["postgres-test", "redis-test"],
        wait_healthy=True,
        timeout=60
    )
    
    yield manager
    
    # Cleanup after all tests
    await manager.stop_services(cleanup_volumes=True)

@pytest.fixture(scope="function")
async def test_services():
    """
    Function-scoped test service fixture.
    Provides access to test services without managing lifecycle.
    Use this for tests that need service URLs or status checks.
    """
    manager = get_test_manager()
    return manager

@pytest.fixture
async def e2e_services():
    """
    Start full E2E service stack (backend, auth, frontend).
    Use this fixture for end-to-end integration tests.
    """
    manager = get_test_manager()
    
    # Start E2E services with the e2e profile
    await manager.start_services(
        services=["backend-test", "auth-test"],
        profiles=["e2e"],
        wait_healthy=True,
        timeout=120
    )
    
    yield manager
    
    # E2E services are stopped by session fixture

@pytest.fixture
def service_urls(test_services):
    """
    Provides URLs for all test services.
    """
    return {
        "postgres": test_services.get_service_url("postgres"),
        "redis": test_services.get_service_url("redis"),
        "backend": test_services.get_service_url("backend"),
        "auth": test_services.get_service_url("auth"),
        "frontend": test_services.get_service_url("frontend")
    }

# =============================================================================
# REAL LLM TESTING
# =============================================================================

@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing"""
    # Get environment through isolated environment
    env = get_env()
    return {
        "enabled": env.get("ENABLE_REAL_LLM_TESTING") == "true",
        "timeout": float(env.get("LLM_TEST_TIMEOUT", "30.0")),
        "max_retries": int(env.get("LLM_TEST_RETRIES", "3"))
    }
