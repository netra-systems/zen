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

# =============================================================================
# ENVIRONMENT SETUP - COMMON FOR ALL TESTS
# =============================================================================

# Set base testing environment variables
# CRITICAL: Only set test environment if we're actually running tests
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    os.environ["TESTING"] = "1"
    os.environ["NETRA_ENV"] = "testing"
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["LOG_LEVEL"] = "ERROR"
    
    # Network and service configuration
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    
    # Authentication secrets required for tests
    os.environ["JWT_SECRET_KEY"] = (
        "test-jwt-secret-key-for-testing-only-do-not-use-in-production"
    )
    os.environ["SERVICE_SECRET"] = (
        "test-service-secret-for-cross-service-auth-32-chars-minimum-length"
    )
    os.environ["FERNET_KEY"] = "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao="
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-chars-long"
    
    # Disable heavy services for faster testing
    os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
    os.environ["CLICKHOUSE_ENABLED"] = "false"
    os.environ["TEST_DISABLE_REDIS"] = "true"

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
    mock = MagicMock()
    mock.enabled = True
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=None)
    mock.exists = AsyncMock(return_value=False)
    return mock

# =============================================================================
# WEBSOCKET FIXTURES
# =============================================================================

@pytest.fixture
def mock_websocket_manager():
    """Unified WebSocket manager mock for all services"""
    mock = MagicMock()
    mock.active_connections = {}
    mock.connect = AsyncMock(return_value=None)
    mock.disconnect = AsyncMock(return_value=None)
    mock.send_message = AsyncMock(return_value=None)
    mock.broadcast = AsyncMock(return_value=None)
    mock.shutdown = AsyncMock(return_value=None)
    mock.send_upgrade_prompt = AsyncMock(return_value=None)
    mock.send_tier_limits_warning = AsyncMock(return_value=None)
    mock.send_security_confirmation = AsyncMock(return_value=None)
    mock.send_dashboard_update = AsyncMock(return_value=None)
    mock.send_onboarding_update = AsyncMock(return_value=None)
    mock.send_optimization_results = AsyncMock(return_value=None)
    mock.send_optimization_result = AsyncMock(return_value=None)
    mock.send_dashboard_ready = AsyncMock(return_value=None)
    mock.send_team_upgrade_offer = AsyncMock(return_value=None)
    mock.send_purchase_confirmation = AsyncMock(return_value=None)
    mock.send_sharing_ready = AsyncMock(return_value=None)
    return mock

# =============================================================================  
# SERVICE MOCKS
# =============================================================================

@pytest.fixture
def mock_clickhouse_client():
    """Common ClickHouse client mock"""
    mock = MagicMock()
    mock.execute = AsyncMock(return_value=[])
    mock.insert = AsyncMock(return_value=True)
    mock.close = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_llm_manager():
    """Common LLM manager mock"""
    mock = MagicMock()
    mock.get_llm = MagicMock(return_value=MagicMock())
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
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_key_manager():
    """Common key manager mock"""
    mock = MagicMock()
    mock.load_from_settings = MagicMock(return_value=mock)
    return mock

@pytest.fixture
def mock_security_service():
    """Common security service mock"""
    return MagicMock()

@pytest.fixture
def mock_tool_dispatcher():
    """Common tool dispatcher mock"""
    return MagicMock()

@pytest.fixture
def mock_agent_supervisor():
    """Common agent supervisor mock"""
    mock = MagicMock()
    mock.shutdown = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_agent_service():
    """Common agent service mock"""
    mock = AsyncMock()
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
    mock = MagicMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
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
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock()
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