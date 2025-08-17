"""
Shared fixtures for LLM Agent E2E tests
Extracted from oversized test files to maintain 300-line limit
"""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
from datetime import datetime
import time

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.services.agent_service import AgentService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_llm_manager():
    """Create properly mocked LLM manager"""
    llm_manager = Mock(spec=LLMManager)
    
    # Mock standard LLM responses
    llm_manager.call_llm = AsyncMock(return_value={
        "content": "I'll help you optimize your AI workload",
        "tool_calls": []
    })
    
    # Mock structured responses for triage
    llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
        "category": "optimization",
        "confidence": 0.95,
        "requires_data": True,
        "requires_optimization": True,
        "requires_actions": True,
        "analysis": "User needs AI workload optimization"
    }))
    
    # Mock structured LLM for triage agent
    from app.agents.triage_sub_agent import (
        TriageResult, Priority, Complexity, UserIntent,
        ExtractedEntities, TriageMetadata
    )
    
    llm_manager.ask_structured_llm = AsyncMock(return_value=TriageResult(
        category="AI Optimization",
        confidence_score=0.95,
        priority=Priority.HIGH,
        complexity=Complexity.MODERATE,
        is_admin_mode=False,
        extracted_entities=ExtractedEntities(
            models_mentioned=["GPT-4", "Claude"],
            metrics_mentioned=["latency", "throughput"],
            time_ranges=[]
        ),
        user_intent=UserIntent(
            primary_intent="optimize",
            secondary_intents=["analyze", "monitor"]
        ),
        tool_recommendations=[],
        metadata=TriageMetadata(
            triage_duration_ms=150,
            cache_hit=False,
            fallback_used=False,
            retry_count=0
        )
    ))
    
    return llm_manager


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
    from app.agents.tool_dispatcher import ToolDispatcher
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
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence_service):
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
    from app.agents.tool_dispatcher import ToolDispatcher
    from app.agents.supervisor.execution_context import AgentExecutionResult
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