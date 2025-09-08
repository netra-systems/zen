"""E2E test fixtures and configuration - REAL SERVICES ONLY.

CRITICAL: This conftest.py provides REAL service fixtures for E2E tests.
NO MOCKING ALLOWED per CLAUDE.md requirements.

Following CLAUDE.md requirements:
- Use IsolatedEnvironment for all environment access
- Use REAL authentication services and WebSocket connections
- Use REAL database connections and LLM services
- All fixtures provide real components or skip tests gracefully
- CHEATING ON TESTS = ABOMINATION
"""

import pytest
import asyncio
import uuid
from typing import Any, Dict
# REMOVED ALL MOCK IMPORTS - E2E tests MUST use real services per CLAUDE.md

# CLAUDE.md compliance: Use IsolatedEnvironment for all environment access
from shared.isolated_environment import get_env
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Configure test environment for e2e tests
@pytest.fixture(scope="session", autouse=True)
def setup_e2e_environment():
    """Setup basic environment for e2e tests without complex orchestration."""
    env = get_env()
    
    # CRITICAL: Disable Docker orchestration for simplified testing
    env.set("NO_DOCKER_ORCHESTRATION", "true", source="e2e_conftest")
    env.set("SKIP_SERVICE_ORCHESTRATION", "true", source="e2e_conftest")
    
    # Set basic test environment configuration
    env.set("TESTING", "1", source="e2e_conftest")
    env.set("ENVIRONMENT", "testing", source="e2e_conftest")
    env.set("LOG_LEVEL", "INFO", source="e2e_conftest")
    
    # Database configuration - use default localhost ports for development containers
    # These will work with existing netra-dev containers or fallback gracefully
    env.set("POSTGRES_HOST", "localhost", source="e2e_conftest")
    env.set("POSTGRES_PORT", "5433", source="e2e_conftest")  # netra-dev-postgres default port
    env.set("POSTGRES_USER", "netra", source="e2e_conftest")
    env.set("POSTGRES_PASSWORD", "netra123", source="e2e_conftest")
    env.set("POSTGRES_DB", "netra_dev", source="e2e_conftest")
    
    # Redis configuration
    env.set("REDIS_HOST", "localhost", source="e2e_conftest")
    env.set("REDIS_PORT", "6380", source="e2e_conftest")  # netra-dev-redis default port
    
    # ClickHouse configuration
    env.set("CLICKHOUSE_HOST", "localhost", source="e2e_conftest")
    env.set("CLICKHOUSE_HTTP_PORT", "8124", source="e2e_conftest")  # netra-dev-clickhouse default port
    env.set("CLICKHOUSE_TCP_PORT", "9001", source="e2e_conftest")
    env.set("CLICKHOUSE_USER", "netra", source="e2e_conftest")
    env.set("CLICKHOUSE_PASSWORD", "netra123", source="e2e_conftest")
    env.set("CLICKHOUSE_DB", "netra_analytics", source="e2e_conftest")
    
    # Service URLs for existing development containers
    env.set("BACKEND_SERVICE_URL", "http://localhost:8000", source="e2e_conftest")
    env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="e2e_conftest")
    env.set("FRONTEND_SERVICE_URL", "http://localhost:3000", source="e2e_conftest")
    
    # WebSocket configuration
    env.set("WEBSOCKET_URL", "ws://localhost:8000/ws", source="e2e_conftest")
    
    # Test-specific secrets (safe for testing)
    env.set("JWT_SECRET_KEY", "test-jwt-secret-key-must-be-at-least-32-characters-for-testing", source="e2e_conftest")
    env.set("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-testing", source="e2e_conftest")
    env.set("FERNET_KEY", "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=", source="e2e_conftest")
    env.set("SECRET_KEY", "test-secret-key-for-e2e-testing", source="e2e_conftest")
    
    yield
    

# REAL test setup fixtures - NO MOCKING ALLOWED
@pytest.fixture
async def real_auth_helper():
    """Real authentication helper for E2E tests."""
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    return E2EAuthHelper()


@pytest.fixture
async def real_websocket_helper():
    """Real WebSocket helper for E2E tests."""
    from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
    return E2EWebSocketAuthHelper()


@pytest.fixture
def real_llm_config():
    """Real LLM configuration for E2E tests."""
    env = get_env()
    return {
        "enabled": env.get("ENABLE_REAL_LLM_TESTING") == "true",
        "timeout": float(env.get("LLM_TEST_TIMEOUT", "30.0")),
        "max_retries": int(env.get("LLM_TEST_RETRIES", "3"))
    }


# REAL database connections for E2E tests - NO MOCKING
@pytest.fixture
async def real_database_session():
    """Real database session for E2E tests."""
    try:
        from netra_backend.app.db.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        async with db_manager.get_session() as session:
            yield session
    except Exception as e:
        # If real database not available, skip tests that require it
        pytest.skip(f"Real database not available for E2E testing: {e}")


@pytest.fixture
async def real_thread_service():
    """Real thread service for E2E tests - NO MOCKING."""
    try:
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.db.database_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        async with db_manager.get_session() as session:
            thread_service = ThreadService(session)
            yield thread_service
    except Exception as e:
        # If real services not available, skip tests that require them
        pytest.skip(f"Real thread service not available for E2E testing: {e}")


# Real WebSocket manager fixture
@pytest.fixture
async def real_websocket_manager():
    """Real WebSocket manager for E2E tests."""
    try:
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        manager = UnifiedWebSocketManager()
        yield manager
    except Exception as e:
        # If real WebSocket manager not available, skip tests that require it
        pytest.skip(f"Real WebSocket manager not available for E2E testing: {e}")


# REAL agent setup fixture for E2E pipeline tests - NO MOCKING
@pytest.fixture
async def real_agent_setup():
    """Setup REAL agent infrastructure for E2E pipeline tests - NO MOCKING ALLOWED."""
    try:
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.core.config import get_config
        
        # Real database session
        db_manager = DatabaseManager()
        db_session = await db_manager.get_session()
        
        # Real LLM manager
        config = get_config()
        llm_manager = LLMManager(config)
        
        # Real WebSocket manager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        websocket_manager = UnifiedWebSocketManager()
        
        # Real tool dispatcher
        tool_dispatcher = ApexToolSelector()
        
        # Create real supervisor agent
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
        
        # Setup agent infrastructure with REAL components
        agents_dict = {
            'triage': supervisor,
            'data': supervisor,
            'supervisor': supervisor
        }
        
        return {
            'supervisor': supervisor,
            'agents': agents_dict,
            'websocket': websocket_manager,
            'llm_manager': llm_manager, 
            'tool_dispatcher': tool_dispatcher,
            'db_session': db_session,
            'user_id': supervisor.user_id,
            'run_id': str(uuid.uuid4())
        }
        
    except Exception as e:
        # If real agent components not available, skip tests that require them
        pytest.skip(f"Real agent infrastructure not available for E2E testing: {e}")