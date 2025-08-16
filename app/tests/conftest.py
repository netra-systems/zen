import os
import sys

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
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/netra_test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
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
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from app.db.session import get_db_session
from app.config import settings

# Temporarily disabled to fix test hanging issue
# @pytest.fixture(scope="function")
# def event_loop():
#     import asyncio
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()

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
        from app.llm.llm_manager import LLMManager
        from app.config import settings
        return LLMManager(settings)
    else:
        return _create_mock_llm_manager()


def _create_mock_llm_manager():
    """Create properly configured async mock LLM manager."""
    from unittest.mock import AsyncMock, MagicMock
    mock_manager = MagicMock()
    # Mock all expected async methods to return proper responses
    mock_manager.get_response = AsyncMock(return_value="Mock LLM response")
    mock_manager.get_structured_response = AsyncMock(return_value={"analysis": "mock analysis", "recommendations": []})
    mock_manager.generate = AsyncMock(return_value="Mock generated content")
    mock_manager.stream_response = AsyncMock()
    # Add latency-specific mocking for performance testing
    mock_manager.generate_structured = AsyncMock(return_value={"optimizations": ["cache optimization", "parallel processing"], "confidence": 0.85})
    mock_manager.analyze_performance = AsyncMock(return_value={"latency_ms": 250, "throughput": 1000, "bottlenecks": ["database", "api calls"]})
    return mock_manager


@pytest.fixture(scope="function") 
def real_websocket_manager():
    """Create real WebSocket manager for E2E tests with interface compatibility."""
    from app.ws_manager import WebSocketManager
    from unittest.mock import AsyncMock
    manager = WebSocketManager()
    # Add interface compatibility for agents expecting send_message
    if not hasattr(manager, 'send_message'):
        manager.send_message = manager.send_message_to_user
    # Mock methods to prevent actual WebSocket operations in tests
    manager.send_message = AsyncMock(return_value=True)
    manager.send_to_thread = AsyncMock(return_value=True)
    manager.send_message_to_user = AsyncMock(return_value=True)
    return manager


@pytest.fixture(scope="function")
def real_tool_dispatcher():
    """Create real tool dispatcher when needed, otherwise proper mock."""
    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
        from app.agents.tool_dispatcher import ToolDispatcher
        dispatcher = ToolDispatcher()
        return dispatcher
    else:
        from unittest.mock import AsyncMock, MagicMock
        mock_dispatcher = MagicMock()
        # Mock expected methods for tool dispatch
        mock_dispatcher.execute = AsyncMock(return_value={"result": "mock tool execution", "success": True})
        mock_dispatcher.dispatch_tool = AsyncMock(return_value={"output": "mock output"})
        mock_dispatcher.get_available_tools = MagicMock(return_value=[])
        return mock_dispatcher


@pytest.fixture(scope="function")
def real_agent_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Create real agent setup for E2E testing."""
    agents = _create_real_agents(real_llm_manager, real_tool_dispatcher)
    return _build_real_setup_dict(agents, real_llm_manager, real_websocket_manager, real_tool_dispatcher)


def _create_real_agents(llm_manager, tool_dispatcher):
    """Create real agent instances with proper dependencies."""
    from app.agents.triage_sub_agent.agent import TriageSubAgent
    from app.agents.data_sub_agent.agent import DataSubAgent
    from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    from app.agents.reporting_sub_agent import ReportingSubAgent
    return {
        'triage': TriageSubAgent(llm_manager, tool_dispatcher),
        'data': DataSubAgent(llm_manager, tool_dispatcher),
        'optimization': OptimizationsCoreSubAgent(llm_manager, tool_dispatcher),
        'reporting': ReportingSubAgent(llm_manager, tool_dispatcher)
    }


def _build_real_setup_dict(agents, llm_manager, websocket_manager, tool_dispatcher):
    """Build real setup dictionary for E2E tests."""
    import uuid
    return {
        'agents': agents, 'llm': llm_manager, 'websocket': websocket_manager,
        'dispatcher': tool_dispatcher, 'run_id': str(uuid.uuid4()), 'user_id': 'test-user-e2e'
    }