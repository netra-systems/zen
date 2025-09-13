"""
Shared fixtures for LLM Agent E2E tests
Extracted from oversized test files to maintain 450-line limit
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService

def create_mock_llm_client():
    """Create a mock LLM client for testing agents."""
    mock_client = MagicMock()
    
    # Setup base async call methods
    mock_client.call_llm = AsyncMock(return_value={
        "content": "Mock LLM response",
        "tool_calls": []
    })
    
    mock_client.ask_llm = AsyncMock(return_value=json.dumps({
        "analysis": "Mock analysis",
        "confidence": 0.95,
        "recommendations": []
    }))
    
    # Setup structured response methods
    mock_client.get_structured_response = AsyncMock(return_value={
        "result": "success",
        "data": {}
    })
    
    return mock_client

@pytest.fixture
def mock_llm_manager():
    """Create properly mocked LLM manager"""
    llm_manager = Mock(spec=LLMManager)
    _setup_basic_llm_responses(llm_manager)
    _setup_structured_llm_responses(llm_manager)
    _setup_triage_agent_responses(llm_manager)
    return llm_manager

def _setup_basic_llm_responses(llm_manager: Mock) -> None:
    """Setup basic LLM response mocks."""
    llm_manager.call_llm = AsyncMock(return_value={
        "content": "I'll help you optimize your AI workload",
        "tool_calls": []
    })

def _setup_structured_llm_responses(llm_manager: Mock) -> None:
    """Setup structured LLM response mocks."""
    llm_manager.ask_llm = AsyncMock(return_value=json.dumps(_get_optimization_response()))

def _get_optimization_response() -> Dict[str, Any]:
    """Get mock optimization response data."""
    return {
        "category": "optimization",
        "confidence": 0.95,
        "requires_data": True,
        "requires_optimization": True,
        "requires_actions": True,
        "analysis": "User needs AI workload optimization"
    }

def _setup_triage_agent_responses(llm_manager: Mock) -> None:
    """Setup triage agent structured LLM responses."""
    from netra_backend.app.agents.triage.unified_triage_agent import (
        Complexity,
        ExtractedEntities,
        Priority,
        TriageMetadata,
        TriageResult,
        UserIntent,
    )
    llm_manager.ask_structured_llm = AsyncMock(return_value=_create_triage_result())

def _create_triage_result() -> 'TriageResult':
    """Create mock triage result."""
    from netra_backend.app.agents.triage.unified_triage_agent import (
        Complexity,
        ExtractedEntities,
        Priority,
        TriageMetadata,
        TriageResult,
        UserIntent,
    )
    return TriageResult(
        category="AI Optimization",
        confidence_score=0.95,
        priority=Priority.HIGH,
        complexity=Complexity.MODERATE,
        is_admin_mode=False,
        extracted_entities=_create_extracted_entities(),
        user_intent=_create_user_intent(),
        tool_recommendations=[],
        metadata=_create_triage_metadata()
    )

def _create_extracted_entities() -> 'ExtractedEntities':
    """Create mock extracted entities."""
    from netra_backend.app.agents.triage.unified_triage_agent import ExtractedEntities
    return ExtractedEntities(
        models_mentioned=["GPT-4", "Claude"],
        metrics_mentioned=["latency", "throughput"],
        time_ranges=[]
    )

def _create_user_intent() -> 'UserIntent':
    """Create mock user intent."""
    from netra_backend.app.agents.triage.unified_triage_agent import UserIntent
    return UserIntent(
        primary_intent="optimize",
        secondary_intents=["analyze", "monitor"]
    )

def _create_triage_metadata() -> 'TriageMetadata':
    """Create mock triage metadata."""
    from netra_backend.app.agents.triage.unified_triage_agent import TriageMetadata
    return TriageMetadata(
        triage_duration_ms=150,
        cache_hit=False,
        fallback_used=False,
        retry_count=0
    )

@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    
    # Mock async context manager for begin()
    async_context_mock = AsyncMock()
    async_context_mock.__aenter__ = AsyncMock(return_value=async_context_mock)
    async_context_mock.__aexit__ = AsyncMock(return_value=None)
    session.begin = Mock(return_value=async_context_mock)
    
    return session

@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager"""
    ws_manager = Mock()
    ws_manager.send_message = AsyncMock()
    ws_manager.broadcast = AsyncMock()
    ws_manager.send_agent_log = AsyncMock()
    ws_manager.send_error = AsyncMock()
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

@pytest.fixture
def mock_persistence_service():
    """Create mock persistence service"""
    mock_persistence = AsyncMock()
    
    # Mock the save_agent_state to handle both interfaces
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:  # (request, session) signature
            return (True, "test_id")
        elif len(args) == 5:  # (run_id, thread_id, user_id, state, db_session) signature
            return True
        else:
            return (True, "test_id")
    
    mock_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    return mock_persistence

@pytest.fixture
def supervisor_agent(mock_db_session, mock_llm_manager, 
                    mock_websocket_manager, mock_tool_dispatcher, mock_persistence_service):
    """Create supervisor agent with all dependencies mocked"""
    # Patch state persistence to avoid hanging
    with patch('netra_backend.app.agents.supervisor_consolidated.state_persistence_service', mock_persistence_service):
        supervisor = SupervisorAgent(
            mock_db_session,
            mock_llm_manager,
            mock_websocket_manager,
            mock_tool_dispatcher
        )
        
        # Set required IDs
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
        
        # Mock the execution engine to prevent hanging
        supervisor.engine.execute_pipeline = AsyncMock(return_value=[])
        
        # Mock state persistence attribute with proper async methods
        supervisor.state_persistence = mock_persistence_service
        
        return supervisor

def create_mock_infrastructure():
    """Create mock infrastructure for e2e testing"""
    db_session = AsyncMock(spec=AsyncSession)
    llm_manager = Mock(spec=LLMManager)
    ws_manager = Mock()
    return db_session, llm_manager, ws_manager

def setup_llm_responses(llm_manager):
    """Setup LLM responses for full optimization flow"""
    responses = [
        {"category": "optimization", "requires_analysis": True},
        {"bottleneck": "memory", "utilization": 0.95},
        {"recommendations": ["Use gradient checkpointing", "Reduce batch size"]}
    ]
    response_index = 0
    async def mock_structured_llm(*args, **kwargs):
        nonlocal response_index
        result = responses[response_index]
        response_index += 1
        return result
    llm_manager.ask_structured_llm = AsyncMock(side_effect=mock_structured_llm)
    llm_manager.call_llm = AsyncMock(return_value={"content": "Optimization complete"})

def setup_websocket_manager(ws_manager):
    """Setup websocket manager for testing"""
    ws_manager.send_message = AsyncMock()

def create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence):
    """Create supervisor with all mocked dependencies"""
    from netra_backend.app.agents.supervisor.execution_context import (
        AgentExecutionResult,
    )
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    dispatcher = Mock(spec=ToolDispatcher)
    dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
    supervisor = SupervisorAgent(db_session, llm_manager, ws_manager, dispatcher)
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    supervisor.state_persistence = mock_persistence
    supervisor.engine.execute_pipeline = AsyncMock(return_value=[
        AgentExecutionResult(success=True, state=None),
        AgentExecutionResult(success=True, state=None),
        AgentExecutionResult(success=True, state=None)
    ])
    return supervisor