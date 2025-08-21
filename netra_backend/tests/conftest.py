import os
import sys
from netra_backend.app.core.network_constants import ServicePorts, HostConstants, DatabaseConstants

# Set test environment variables BEFORE importing any app modules
# Use isolated values if TEST_ISOLATION is enabled
if os.environ.get("TEST_ISOLATION") == "1":
    # When using test isolation, environment is already configured
    # Just ensure critical test flags are set
    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("LOG_LEVEL", "ERROR")
    os.environ.setdefault("DEV_MODE_DISABLE_CLICKHOUSE", "true")
    os.environ.setdefault("CLICKHOUSE_ENABLED", "false")
else:
    # Standard test environment setup
    os.environ["TESTING"] = "1"
    # Use PostgreSQL URL format even for tests to satisfy validator
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
    os.environ["REDIS_USERNAME"] = ""
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["TEST_DISABLE_REDIS"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
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
    else:
        # Use mock keys for regular testing
        os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
        os.environ.setdefault("GOOGLE_API_KEY", "test-gemini-api-key")  # Same as GEMINI
        os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
        os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-api-key")

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from netra_backend.app.db.base import Base
from netra_backend.app.main import app
from fastapi.testclient import TestClient
from netra_backend.app.db.session import get_db_session
from netra_backend.app.config import settings
from netra_backend.app.tests.conftest_helpers import (
    _setup_basic_llm_mocks, _setup_performance_llm_mocks,
    _setup_websocket_interface_compatibility, _setup_websocket_test_mocks,
    _create_real_tool_dispatcher, _create_mock_tool_dispatcher,
    _import_agent_classes, _instantiate_agents
)

# Import all models to ensure they are registered with Base before creating tables
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
from netra_backend.app.db.models_postgres import *  # Import all postgres models
from netra_backend.app.db.models_content import *  # Import all content models
from netra_backend.app.db.models_agent_state import *  # Import all agent state models

# Initialize database on import to ensure async_session_factory is available
from netra_backend.app.db.postgres import initialize_postgres
try:
    initialize_postgres()
except Exception as e:
    # Log but don't fail on import - some tests may not need database
    import logging
    logging.getLogger(__name__).warning(f"Failed to initialize database in conftest.py: {e}")

# Temporarily disabled to fix test hanging issue
# @pytest.fixture(scope="function")
# def event_loop():
#     import asyncio
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()

@pytest.fixture(scope="function")
def ensure_db_initialized():
    """Ensure database is initialized for tests that need it."""
    from netra_backend.app.db.postgres import async_session_factory, initialize_postgres
    
    if async_session_factory is None:
        try:
            initialize_postgres()
        except Exception as e:
            pytest.skip(f"Cannot initialize database for test: {e}")
    
    # Return the session factory for convenience
    return async_session_factory

@pytest.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    async_session = sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db_session]


# Real LLM Testing Fixtures
@pytest.fixture(scope="function")
def real_llm_manager():
    """Create real LLM manager when ENABLE_REAL_LLM_TESTING=true, otherwise proper mock."""
    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.config import settings
        return LLMManager(settings)
    else:
        return _create_mock_llm_manager()


def _create_mock_llm_manager():
    """Create properly configured async mock LLM manager."""
    from unittest.mock import AsyncMock, MagicMock
    mock_manager = MagicMock()
    _setup_basic_llm_mocks(mock_manager)
    _setup_performance_llm_mocks(mock_manager)
    return mock_manager


@pytest.fixture(scope="function") 
def real_websocket_manager():
    """Create real WebSocket manager for E2E tests with interface compatibility."""
    from netra_backend.app.ws_manager import WebSocketManager
    manager = WebSocketManager()
    _setup_websocket_interface_compatibility(manager)
    _setup_websocket_test_mocks(manager)
    return manager


@pytest.fixture(scope="function")
def real_tool_dispatcher():
    """Create real tool dispatcher when needed, otherwise proper mock."""
    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
        return _create_real_tool_dispatcher()
    return _create_mock_tool_dispatcher()


@pytest.fixture(scope="function")
def real_agent_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Create real agent setup for E2E testing."""
    agents = _create_real_agents(real_llm_manager, real_tool_dispatcher)
    return _build_real_setup_dict(agents, real_llm_manager, real_websocket_manager, real_tool_dispatcher)


def _create_real_agents(llm_manager, tool_dispatcher):
    """Create real agent instances with proper dependencies."""
    agent_classes = _import_agent_classes()
    return _instantiate_agents(agent_classes, llm_manager, tool_dispatcher)


def _build_real_setup_dict(agents, llm_manager, websocket_manager, tool_dispatcher):
    """Build real setup dictionary for E2E tests."""
    import uuid
    return {
        'agents': agents, 'llm': llm_manager, 'websocket': websocket_manager,
        'dispatcher': tool_dispatcher, 'run_id': str(uuid.uuid4()), 'user_id': 'test-user-e2e'
    }