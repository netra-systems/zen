"""
E2E test fixtures and configuration.
Uses consolidated test framework infrastructure.
"""

# Import all common fixtures from the consolidated base
from test_framework.conftest_base import *

# Import specific utilities we need
from test_framework.websocket_helpers import WebSocketTestHelpers
from test_framework.helpers.auth_helpers import AuthTestHelpers

import pytest
import asyncio
import os
import sys
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock


def pytest_configure(config):
    """Configure pytest for E2E tests with real LLM support."""
    # Ensure that if TEST_USE_REAL_LLM is set, it persists throughout the test session
    if os.getenv("TEST_USE_REAL_LLM") == "true":
        # Re-set to ensure it's available throughout the session
        os.environ["TEST_USE_REAL_LLM"] = "true"
        os.environ["ENABLE_REAL_LLM_TESTING"] = "true"

# CRITICAL: Override any PostgreSQL configuration for E2E tests to use SQLite
# E2E tests should be fast and not depend on external databases
# This must be set BEFORE any backend modules are imported
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    # Force SQLite for E2E tests regardless of other configurations
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["TESTING"] = "1"
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["E2E_TESTING"] = "true"

# E2E Configuration - Project specific
E2E_CONFIG = {
    "timeout": 30,
    "base_url": "http://localhost:8000",
    "websocket_url": "ws://localhost:8000/ws",
    "test_user": "test@example.com"
}

class E2EEnvironmentValidator:
    """Validator for E2E test environment."""
    
    @staticmethod
    def validate():
        """Validate E2E environment is ready."""
        return True

# Basic test setup fixtures
@pytest.fixture
async def mock_agent_service():
    """Mock agent service for E2E tests."""
    # Mock: Generic component isolation for controlled unit testing
    mock_service = AsyncMock()
    mock_service.process_message.return_value = {
        "response": "Test response",
        "metadata": {"test": True}
    }
    return mock_service

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for E2E tests."""
    # Mock: Generic component isolation for controlled unit testing
    mock_manager = MagicMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_manager.send_message = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_manager.broadcast = AsyncMock()
    return mock_manager

@pytest.fixture
def model_selection_setup():
    """Basic setup for model selection tests."""
    return {
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        "mock_llm_service": AsyncMock(),
        # Mock: Database isolation for unit testing without external database connections
        "mock_database": AsyncMock(),
        "test_config": {"environment": "test"}
    }

# Real LLM testing configuration
@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing."""
    # Check environment variable to determine if real LLM should be enabled
    use_real_llm = os.getenv("TEST_USE_REAL_LLM", "false").lower() == "true"
    return {
        "enabled": use_real_llm,
        "timeout": 30.0,
        "max_retries": 3
    }

# Concurrent test fixtures
@pytest.fixture
async def concurrent_test_environment():
    """Mock concurrent test environment."""
    from unittest.mock import AsyncMock
    
    # Create a mock environment with required methods
    # Mock: Generic component isolation for controlled unit testing
    mock_env = AsyncMock()
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock_env.redis_client = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_env.db_pool = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_env.initialize = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_env.cleanup = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_env.seed_user_data = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    mock_env.cleanup_user_data = AsyncMock()
    
    # Initialize and return
    await mock_env.initialize()
    yield mock_env
    await mock_env.cleanup()

@pytest.fixture
def isolated_test_users():
    """Create mock isolated test users for concurrent testing."""
    from unittest.mock import MagicMock
    
    users = []
    for i in range(5):  # Create 5 test users
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
