"""
E2E Test Fixtures - Modular and Composable
All fixtures broken into ≤8 line functions for architectural compliance
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import json
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager

# Add project root to path


def _create_basic_llm_responses():
    """Create basic LLM response mocks"""
    return {
        "content": "I'll help you optimize your AI workload",
        "tool_calls": []
    }


def _create_structured_llm_responses():
    """Create structured LLM response data"""
    return json.dumps({
        "category": "optimization",
        "confidence": 0.95,
        "requires_data": True,
        "requires_optimization": True,
        "requires_actions": True,
        "analysis": "User needs AI workload optimization"
    })


def _create_triage_entities():
    """Create triage extracted entities"""
    from netra_backend.app.agents.triage_sub_agent import ExtractedEntities
    return ExtractedEntities(
        models_mentioned=["GPT-4", "Claude"],
        metrics_mentioned=["latency", "throughput"],
        time_ranges=[]
    )


def _create_triage_intent():
    """Create triage user intent"""
    from netra_backend.app.agents.triage_sub_agent import UserIntent
    return UserIntent(
        primary_intent="optimize",
        secondary_intents=["analyze", "monitor"]
    )


def _create_triage_metadata():
    """Create triage metadata"""
    from netra_backend.app.agents.triage_sub_agent import TriageMetadata
    return TriageMetadata(
        triage_duration_ms=150,
        cache_hit=False,
        fallback_used=False,
        retry_count=0
    )


def _create_triage_result():
    """Create complete triage result"""
    from netra_backend.app.agents.triage_sub_agent import (
        Complexity,
        Priority,
        TriageResult,
    )
    return TriageResult(
        category="AI Optimization",
        confidence_score=0.95,
        priority=Priority.HIGH,
        complexity=Complexity.MODERATE,
        is_admin_mode=False,
        extracted_entities=_create_triage_entities(),
        user_intent=_create_triage_intent(),
        tool_recommendations=[],
        metadata=_create_triage_metadata()
    )


@pytest.fixture
def mock_llm_manager():
    """Create properly mocked LLM manager with ≤8 line setup"""
    llm_manager = Mock(spec=LLMManager)
    llm_manager.call_llm = AsyncMock(return_value=_create_basic_llm_responses())
    llm_manager.ask_llm = AsyncMock(return_value=_create_structured_llm_responses())
    llm_manager.ask_structured_llm = AsyncMock(return_value=_create_triage_result())
    return llm_manager


def _setup_db_session_mocks(session):
    """Configure database session mocks"""
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()


def _setup_db_transaction_mocks(session):
    """Configure database transaction mocks"""
    async_context_mock = AsyncMock()
    async_context_mock.__aenter__ = AsyncMock(return_value=async_context_mock)
    async_context_mock.__aexit__ = AsyncMock(return_value=None)
    session.begin = Mock(return_value=async_context_mock)


@pytest.fixture
def mock_db_session():
    """Create mock database session with proper async context"""
    session = AsyncMock(spec=AsyncSession)
    _setup_db_session_mocks(session)
    _setup_db_transaction_mocks(session)
    return session


def _setup_websocket_methods(ws_manager):
    """Configure websocket manager methods"""
    ws_manager.send_message = AsyncMock()
    ws_manager.broadcast = AsyncMock()
    ws_manager.send_agent_log = AsyncMock()
    ws_manager.send_error = AsyncMock()


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager"""
    ws_manager = Mock()
    _setup_websocket_methods(ws_manager)
    ws_manager.send_sub_agent_update = AsyncMock()
    return ws_manager


@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher"""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    dispatcher = Mock(spec=ToolDispatcher)
    dispatcher.dispatch_tool = AsyncMock(return_value={
        "status": "success",
        "result": {"data": "Tool execution successful"}
    })
    return dispatcher


def _create_persistence_mock():
    """Create persistence service mock"""
    mock_persistence = AsyncMock()
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:
            return (True, "test_id")
        elif len(args) == 5:
            return True
        else:
            return (True, "test_id")
    mock_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    return mock_persistence


def _setup_persistence_methods(mock_persistence):
    """Setup persistence service methods"""
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))


@pytest.fixture
def mock_persistence_service():
    """Create mock persistence service fixture"""
    mock_persistence = _create_persistence_mock()
    _setup_persistence_methods(mock_persistence)
    return mock_persistence


def _configure_supervisor_agent(supervisor):
    """Configure supervisor agent with required IDs and mocks"""
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    supervisor.engine.execute_pipeline = AsyncMock(return_value=[])


@pytest.fixture
def supervisor_agent(mock_db_session, mock_llm_manager, 
                    mock_websocket_manager, mock_tool_dispatcher, mock_persistence_service):
    """Create supervisor agent with all dependencies mocked"""
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence_service):
        supervisor = SupervisorAgent(
            mock_db_session,
            mock_llm_manager,
            mock_websocket_manager,
            mock_tool_dispatcher
        )
        _configure_supervisor_agent(supervisor)
        supervisor.state_persistence = mock_persistence_service
        return supervisor