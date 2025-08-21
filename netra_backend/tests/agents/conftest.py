"""Shared fixtures for agent tests."""

import os
import sys
import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Add the project root directory to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json

from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.app.services.websocket.ws_manager import WebSocketManager


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
    from netra_backend.app.agents.triage_sub_agent.models import TriageResult
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
    llm_manager.call_llm = AsyncMock(side_effect=_mock_call_llm)
    llm_manager.ask_llm = AsyncMock(side_effect=_mock_ask_llm)
    llm_manager.ask_structured_llm = AsyncMock(side_effect=_mock_ask_structured_llm)
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
def agent(mock_dependencies):
    """Create DataSubAgent instance with mocked dependencies for test compatibility"""
    from unittest.mock import patch

    from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
    
    llm_manager, tool_dispatcher = mock_dependencies
    with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager') as mock_redis_class:
        # Setup proper async mocks for redis operations
        mock_redis_instance = Mock()
        mock_redis_instance.get = AsyncMock()
        mock_redis_instance.set = AsyncMock()
        mock_redis_instance.delete = AsyncMock()
        mock_redis_instance.exists = AsyncMock()
        mock_redis_class.return_value = mock_redis_instance
        
        agent = DataSubAgent(llm_manager, tool_dispatcher)
        # Ensure redis_manager is properly mocked
        if hasattr(agent, 'redis_manager') and agent.redis_manager:
            agent.redis_manager.get = AsyncMock()
            agent.redis_manager.set = AsyncMock()
    return agent


@pytest.fixture
def service(agent):
    """Alias agent as service for integration test compatibility"""
    return agent


@pytest.fixture
def sample_performance_data():
    """Sample performance metrics data for testing"""
    return [
        {
            'time_bucket': '2024-01-01T12:00:00',
            'event_count': 100,
            'latency_p50': 50.0,
            'latency_p95': 95.0,
            'latency_p99': 99.0,
            'avg_throughput': 1000.0,
            'peak_throughput': 2000.0,
            'error_rate': 0.5,
            'total_cost': 10.0,
            'unique_workloads': 5
        }
    ]


@pytest.fixture
def sample_anomaly_data():
    """Sample anomaly detection data for testing"""
    return [
        {
            'timestamp': '2024-01-01T12:00:00',
            'value': 50.0,
            'avg_value': 50.0,
            'std_value': 10.0,
            'z_score': 0.0
        },
        {
            'timestamp': '2024-01-01T12:01:00',
            'value': 100.0,
            'avg_value': 50.0,
            'std_value': 10.0,
            'z_score': 5.0
        }
    ]


@pytest.fixture
def sample_usage_patterns():
    """Sample usage pattern data for testing"""
    return [
        {'day_of_week': 1, 'hour': 9, 'total_events': 1000, 'avg_latency': 50.0},
        {'day_of_week': 1, 'hour': 10, 'total_events': 1500, 'avg_latency': 45.0},
        {'day_of_week': 1, 'hour': 11, 'total_events': 2000, 'avg_latency': 55.0}
    ]


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