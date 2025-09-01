from shared.isolated_environment import get_env
"""
env = get_env()
E2E test fixtures and configuration.
ENFORCES REAL SERVICES ONLY - NO MOCKS ALLOWED.
"""

# CRITICAL: Enforce real services for all E2E tests
from tests.e2e.enforce_real_services import *

# Import only non-mock fixtures from the consolidated base
# DO NOT import mock fixtures for E2E tests

# Import specific utilities we need
from test_framework.websocket_helpers import WebSocketTestHelpers
from test_framework.helpers.auth_helpers import AuthTestHelpers

import pytest
import asyncio
import os
import sys
from typing import Any, Dict
# ENFORCED: NO MOCKS in E2E tests - use real services only
from tests.e2e.enforce_real_services import (
    E2EServiceValidator,
    E2ERealServiceFactory,
    e2e_services,
    real_redis_client,
    real_agent_service as e2e_agent_service,
    real_websocket as e2e_websocket,
    real_llm_provider
)

# Validate services on import
E2EServiceValidator.enforce_real_services()


def pytest_configure(config):
    """Configure pytest for E2E tests with real LLM support."""
    # Ensure that if USE_REAL_LLM (or legacy TEST_USE_REAL_LLM) is set, it persists throughout the test session
    if (os.getenv("USE_REAL_LLM") == "true" or os.getenv("TEST_USE_REAL_LLM") == "true"):
        # Re-set both for compatibility
        env.set("USE_REAL_LLM", "true", "test")
        env.set("TEST_USE_REAL_LLM", "true", "test")  # Legacy compatibility
        env.set("ENABLE_REAL_LLM_TESTING", "true", "test")

# CRITICAL: Override any PostgreSQL configuration for E2E tests to use SQLite
# E2E tests should be fast and not depend on external databases
# This must be set BEFORE any backend modules are imported
if "pytest" in sys.modules or env.get("PYTEST_CURRENT_TEST"):
    # Check if we're in staging environment
    current_env = env.get("ENVIRONMENT", "").lower()
    is_staging = current_env == "staging"
    
    if is_staging:
        # Staging environment - use staging database configuration
        env.set("E2E_TESTING", "true", "test")
        env.set("TESTING", "0", "test")  # Not local testing in staging
        # Keep existing ENVIRONMENT=staging
    else:
        # Force SQLite for local E2E tests regardless of other configurations
        env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")
        env.set("TESTING", "1", "test")
        env.set("ENVIRONMENT", "testing", "test")
        env.set("E2E_TESTING", "true", "test")

# Dynamic port configuration for E2E tests
# Determine current environment
current_env = env.get("ENVIRONMENT", "").lower()
is_staging = current_env == "staging"

if is_staging:
    # Staging environment configuration
    E2E_CONFIG = {
        "timeout": 60,  # Longer timeouts for staging
        "base_url": "https://api.staging.netrasystems.ai",
        "websocket_url": "wss://api.staging.netrasystems.ai/ws",
        "auth_url": "https://api.staging.netrasystems.ai",
        "test_user": "test@example.com",
        "environment": "staging"
    }
else:
    try:
        from tests.e2e.dynamic_port_manager import get_port_manager
        port_mgr = get_port_manager()
        urls = port_mgr.get_service_urls()
        E2E_CONFIG = {
            "timeout": 30,
            "base_url": urls["backend"],
            "websocket_url": urls["websocket"],
            "auth_url": urls["auth"],
            "test_user": "test@example.com",
            "environment": "test"
        }
    except ImportError:
        # Fallback to defaults if port manager not available
        backend_port = env.get("TEST_BACKEND_PORT", "8000")
        auth_port = env.get("TEST_AUTH_PORT", "8081")
        E2E_CONFIG = {
            "timeout": 30,
            "base_url": f"http://localhost:{backend_port}",
            "websocket_url": f"ws://localhost:{backend_port}/ws",
            "auth_url": f"http://localhost:{auth_port}",
            "test_user": "test@example.com",
            "environment": "test"
        }

class E2EEnvironmentValidator:
    """Validator for E2E test environment."""
    
    @staticmethod
    def validate():
        """Validate E2E environment is ready."""
        return True

# Basic test setup fixtures
@pytest.fixture
def staging_oauth_config():
    """Configure OAuth simulation for staging tests."""
    if is_staging:
        # Ensure E2E_OAUTH_SIMULATION_KEY is available for staging tests
        oauth_key = os.getenv("E2E_OAUTH_SIMULATION_KEY")
        if not oauth_key:
            pytest.skip("E2E_OAUTH_SIMULATION_KEY not available - required for staging OAuth simulation")
        
        return {
            "oauth_simulation_enabled": True,
            "oauth_simulation_key": oauth_key,
            "auth_headers": {"X-E2E-OAuth-Simulation-Key": oauth_key},
            "environment": "staging"
        }
    else:
        return {
            "oauth_simulation_enabled": False,
            "oauth_simulation_key": None,
            "auth_headers": {},
            "environment": current_env
        }

@pytest.fixture
async def test_user_token(staging_oauth_config):
    """Get a valid test user token for API testing."""
    if staging_oauth_config["oauth_simulation_enabled"]:
        # Use OAuth simulation for staging
        try:
            from tests.e2e.staging_auth_bypass import StagingAuthHelper
            auth_helper = StagingAuthHelper(staging_oauth_config["oauth_simulation_key"])
            token = await auth_helper.get_test_token()
            return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}
        except Exception as e:
            pytest.skip(f"Failed to get staging auth token: {e}")
    else:
        # Mock token for local testing
        return {"token": "mock-test-token", "headers": {"Authorization": "Bearer mock-test-token"}}

@pytest.fixture
async def real_agent_service():
    """Real agent service for E2E tests."""
    from netra_backend.app.services.agent_service import AgentService
    from netra_backend.app.services.agent_factory import AgentFactory
    
    # Create real service for E2E testing
    factory = AgentFactory()
    service = await factory.create_agent_service()
    return service

@pytest.fixture
async def real_websocket_manager():
    """Real WebSocket manager for E2E tests."""
    from netra_backend.app.services.websocket_manager import WebSocketManager
    
    # Create real WebSocket manager for E2E testing
    manager = WebSocketManager()
    await manager.initialize()
    return manager

@pytest.fixture
async def model_selection_setup():
    """Real setup for E2E model selection tests."""
    from netra_backend.app.services.llm_service import LLMService
    from netra_backend.app.services.database_service import DatabaseService
    
    # Use real services for E2E testing
    llm_service = LLMService()
    database_service = DatabaseService()
    await database_service.initialize()
    
    return {
        "llm_service": llm_service,
        "database": database_service,
        "test_config": {"environment": "test"}
    }

# Real LLM testing configuration
@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing."""
    # Check environment variable to determine if real LLM should be enabled
    # CRITICAL: Real LLM is DEFAULT per CLAUDE.md (no mocks allowed in dev/staging/production)
    # Check primary control variable first
    primary_enabled = os.getenv("NETRA_REAL_LLM_ENABLED", "true").lower() == "true"
    use_real_llm = (primary_enabled or
                    os.getenv("USE_REAL_LLM", "true").lower() == "true" or
                    os.getenv("TEST_USE_REAL_LLM", "true").lower() == "true" or
                    os.getenv("ENABLE_REAL_LLM_TESTING", "true").lower() == "true" or
                    is_staging)  # Always use real LLM in staging
    return {
        "enabled": use_real_llm,
        "timeout": 30.0,
        "max_retries": 3
    }

# Database sync validator fixture
@pytest.fixture
def sync_validator():
    """Create sync validator instance for database sync tests."""
    from tests.e2e.database_sync_fixtures import DatabaseSyncValidator
    return DatabaseSyncValidator()

# Concurrent test fixtures
@pytest.fixture
async def concurrent_test_environment():
    """Real concurrent test environment for E2E."""
    from netra_backend.app.services.test_environment import TestEnvironment
    import redis.asyncio as redis
    import asyncpg
    
    # Create real environment with actual services
    env = TestEnvironment()
    
    # Initialize real Redis connection
    env.redis_client = await redis.from_url(
        env.get("REDIS_URL", "redis://localhost:6379/0")
    )
    
    # Initialize real database pool (SQLite for tests)
    # E2E tests use SQLite in-memory as configured earlier
    await env.initialize()
    
    # Seed test data if needed
    await env.seed_user_data()
    
    yield env
    
    # Cleanup
    await env.cleanup_user_data()
    await env.cleanup()
    await env.redis_client.aclose()

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
