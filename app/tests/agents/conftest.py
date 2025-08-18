"""Shared fixtures for agent tests."""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.config import get_config
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.tool_dispatcher import ToolDispatcher
from app.services.agent_service import AgentService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.quality_gate_service import QualityGateService
from app.services.corpus_service import CorpusService
import json


def _setup_database_mock() -> AsyncMock:
    """Create mock database session with standard async methods."""
    db_session = AsyncMock(spec=AsyncSession)
    db_session.commit = AsyncMock()
    db_session.rollback = AsyncMock()
    db_session.close = AsyncMock()
    return db_session


async def _mock_call_llm(*args, **kwargs):
    """Mock LLM call returning optimization response."""
    return {
        "content": "Based on analysis, reduce costs by switching to efficient models.",
        "tool_calls": []
    }


async def _mock_ask_llm(*args, **kwargs):
    """Mock LLM ask returning structured JSON response."""
    return json.dumps({
        "category": "optimization",
        "analysis": "Cost optimization required",
        "recommendations": ["Switch to GPT-3.5 for low-complexity tasks", "Implement caching"]
    })


async def _mock_ask_structured_llm(prompt, llm_config_name, schema, **kwargs):
    """Mock structured LLM call with TriageResult support."""
    from app.agents.triage_sub_agent.models import TriageResult
    if schema == TriageResult or hasattr(schema, '__name__') and 'TriageResult' in schema.__name__:
        return TriageResult(
            category="optimization", severity="medium",
            analysis="Cost optimization analysis for provided prompt",
            requirements=["cost reduction", "performance maintenance"],
            next_steps=["analyze_costs", "identify_optimization_opportunities"],
            data_needed=["current_costs", "usage_patterns"],
            suggested_tools=["cost_analyzer", "performance_monitor"]
        )
    try:
        return schema()
    except:
        return Mock()


def _setup_llm_manager() -> Mock:
    """Create LLM manager mock with realistic response methods."""
    llm_manager = Mock(spec=LLMManager)
    llm_manager.call_llm = _mock_call_llm
    llm_manager.ask_llm = _mock_ask_llm
    llm_manager.ask_structured_llm = _mock_ask_structured_llm
    llm_manager.get = Mock(return_value=Mock())
    return llm_manager


def _setup_websocket_tool_dispatcher() -> tuple[WebSocketManager, Mock]:
    """Create websocket manager and tool dispatcher mock."""
    websocket_manager = WebSocketManager()
    tool_dispatcher = Mock(spec=ToolDispatcher)
    tool_dispatcher.dispatch_tool = AsyncMock(return_value={
        "status": "success", "result": "Tool executed successfully"
    })
    tool_dispatcher.has_tool = Mock(return_value=True)
    return websocket_manager, tool_dispatcher


def _setup_core_services() -> tuple[SyntheticDataService, QualityGateService, CorpusService]:
    """Create core business services."""
    synthetic_service = SyntheticDataService()
    quality_service = QualityGateService()
    corpus_service = CorpusService()
    return synthetic_service, quality_service, corpus_service


def _setup_mock_services() -> tuple[Mock, Mock]:
    """Create mock state persistence and apex tool selector services."""
    state_service = Mock()
    state_service.save_state = AsyncMock()
    state_service.load_state = AsyncMock(return_value=None)
    apex_selector = Mock()
    apex_selector.select_tools = AsyncMock(return_value=[])
    apex_selector.dispatch_tool = AsyncMock(return_value={"status": "success"})
    return state_service, apex_selector


def _setup_agents(db_session: AsyncMock, llm_manager: Mock, 
                 websocket_manager: WebSocketManager, tool_dispatcher: Mock) -> tuple[Supervisor, AgentService]:
    """Create supervisor and agent service with proper configuration."""
    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    agent_service = AgentService(supervisor)
    agent_service.websocket_manager = websocket_manager
    return supervisor, agent_service


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for DataSubAgent and other tests"""
    llm_manager = _setup_llm_manager()
    websocket_manager, tool_dispatcher = _setup_websocket_tool_dispatcher()
    return llm_manager, tool_dispatcher


@pytest.fixture
def setup_real_infrastructure():
    """Setup infrastructure for real LLM tests."""
    config = get_config()
    db_session = _setup_database_mock()
    llm_manager = _setup_llm_manager()
    websocket_manager, tool_dispatcher = _setup_websocket_tool_dispatcher()
    synthetic_service, quality_service, corpus_service = _setup_core_services()
    state_persistence_service, apex_tool_selector = _setup_mock_services()
    supervisor, agent_service = _setup_agents(db_session, llm_manager, websocket_manager, tool_dispatcher)
    return {"supervisor": supervisor, "agent_service": agent_service, "db_session": db_session, "llm_manager": llm_manager, "websocket_manager": websocket_manager, "tool_dispatcher": tool_dispatcher, "synthetic_service": synthetic_service, "quality_service": quality_service, "quality_gate_service": quality_service, "corpus_service": corpus_service, "state_persistence_service": state_persistence_service, "apex_tool_selector": apex_tool_selector, "config": config}