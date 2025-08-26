"""
Unified base conftest fixtures for all test infrastructure.
Consolidates common fixtures from multiple conftest.py files across the project.

This module provides:
- Common environment setup
- Shared mock fixtures  
- Database fixtures
- WebSocket test fixtures
- Authentication fixtures
- Service mocks

USAGE: Import specific fixtures in service-specific conftest.py files as needed.
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

# Use centralized environment management for test framework
try:
    from dev_launcher.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            return os.getenv(key, default)
        def set(self, key, value, source="test_framework"):
            os.environ[key] = value
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
    env.set("LOG_LEVEL", "ERROR", "test_framework_base")
    
    # Network and service configuration
    env.set("REDIS_HOST", "localhost", "test_framework_base")
    env.set("CLICKHOUSE_HOST", "localhost", "test_framework_base")
    env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test_framework_base")
    
    # Authentication secrets required for tests
    env.set("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-do-not-use-in-production", "test_framework_base")
    
    # FastMCP home directory workaround for Windows compatibility
    # Ensures Path.home() works correctly in FastMCP settings initialization
    import os
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
    env.set("FERNET_KEY", "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao=", "test_framework_base")
    env.set("ENCRYPTION_KEY", "test-encryption-key-32-chars-long", "test_framework_base")
    
    # Disable heavy services for faster testing
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test_framework_base")
    env.set("CLICKHOUSE_ENABLED", "false", "test_framework_base")
    env.set("TEST_DISABLE_REDIS", "true", "test_framework_base")

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
    return {
        "websocket_url": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8765"),
        "backend_url": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
        "auth_service_url": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
        "skip_real_services": os.getenv("SKIP_REAL_SERVICES", "true").lower() == "true",
        "test_mode": os.getenv("HIGH_VOLUME_TEST_MODE", "mock"),
        "timeout": int(os.getenv("E2E_TEST_TIMEOUT", "300")),
        "performance_mode": os.getenv("E2E_PERFORMANCE_MODE", "true").lower() == "true"
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
# REAL LLM TESTING
# =============================================================================

@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing"""
    return {
        "enabled": os.environ.get("ENABLE_REAL_LLM_TESTING") == "true",
        "timeout": float(os.environ.get("LLM_TEST_TIMEOUT", "30.0")),
        "max_retries": int(os.environ.get("LLM_TEST_RETRIES", "3"))
    }