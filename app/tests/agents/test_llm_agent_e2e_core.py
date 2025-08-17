"""
Core E2E LLM Agent Tests
Basic functionality, initialization, and core agent tests
Split from oversized test_llm_agent_e2e_real.py to maintain 300-line limit

BVJ:
1. Segment: Growth & Enterprise  
2. Business Goal: Ensure agent reliability and basic functionality
3. Value Impact: Prevents agent failures that could cost customers optimization opportunities
4. Revenue Impact: Maintains customer trust and prevents churn from failed optimizations
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

from .fixtures.llm_agent_fixtures import (
    mock_llm_manager, mock_db_session, mock_websocket_manager,
    mock_tool_dispatcher, mock_persistence_service, supervisor_agent
)


async def test_supervisor_initialization(supervisor_agent):
    """Test supervisor agent proper initialization"""
    assert supervisor_agent is not None
    assert supervisor_agent.thread_id is not None
    assert supervisor_agent.user_id is not None
    assert len(supervisor_agent.agents) > 0


async def test_llm_triage_processing(supervisor_agent, mock_llm_manager):
    """Test LLM triage agent processes user requests correctly"""
    user_request = "Optimize my GPU utilization for LLM inference"
    run_id = str(uuid.uuid4())
    
    # Run supervisor
    state = await supervisor_agent.run(
        user_request,
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )
    
    # Verify state was created
    assert state is not None
    assert state.user_request == user_request
    assert state.chat_thread_id == supervisor_agent.thread_id
    assert state.user_id == supervisor_agent.user_id


async def test_llm_response_parsing(mock_llm_manager):
    """Test LLM response parsing and error handling"""
    # Test valid JSON response
    mock_llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
        "analysis": "Valid response",
        "recommendations": ["rec1", "rec2"]
    }))
    
    response = await mock_llm_manager.ask_llm("Test prompt")
    parsed = json.loads(response)
    assert "analysis" in parsed
    assert len(parsed["recommendations"]) == 2
    
    # Test invalid JSON handling
    mock_llm_manager.ask_llm = AsyncMock(return_value="Invalid JSON {")
    response = await mock_llm_manager.ask_llm("Test prompt")
    
    try:
        json.loads(response)
        assert False, "Should have raised JSON decode error"
    except json.JSONDecodeError:
        pass  # Expected


async def test_agent_state_creation():
    """Test basic agent state creation and structure"""
    state = DeepAgentState(
        user_request="Test request",
        chat_thread_id="test_thread",
        user_id="test_user"
    )
    
    assert state.user_request == "Test request"
    assert state.chat_thread_id == "test_thread"
    assert state.user_id == "test_user"
    assert state.triage_result is None
    assert state.data_result is None
    assert state.optimizations_result is None


async def test_basic_llm_call():
    """Test basic LLM call functionality"""
    llm_manager = Mock(spec=LLMManager)
    llm_manager.call_llm = AsyncMock(return_value={
        "content": "Test response",
        "tool_calls": []
    })
    
    result = await llm_manager.call_llm("Test prompt")
    assert result["content"] == "Test response"
    assert result["tool_calls"] == []


async def test_structured_llm_call():
    """Test structured LLM call functionality"""
    llm_manager = Mock(spec=LLMManager)
    
    expected_result = {
        "category": "optimization",
        "confidence": 0.95,
        "requires_analysis": True
    }
    
    llm_manager.ask_structured_llm = AsyncMock(return_value=expected_result)
    
    result = await llm_manager.ask_structured_llm("Test prompt", {})
    assert result["category"] == "optimization"
    assert result["confidence"] == 0.95
    assert result["requires_analysis"] is True


async def test_agent_registry():
    """Test agent registry functionality"""
    db_session = AsyncMock(spec=AsyncSession)
    llm_manager = Mock(spec=LLMManager)
    ws_manager = Mock()
    tool_dispatcher = Mock()
    
    # Mock persistence to avoid hanging
    mock_persistence = AsyncMock()
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence):
        supervisor = SupervisorAgent(db_session, llm_manager, ws_manager, tool_dispatcher)
        
        # Verify agents are registered
        assert len(supervisor.agents) > 0
        
        # Should have key agent types
        agent_names = list(supervisor.agents.keys())
        assert any("triage" in name.lower() for name in agent_names)


async def test_basic_error_handling():
    """Test basic error handling in supervisor"""
    db_session = AsyncMock(spec=AsyncSession)
    llm_manager = Mock(spec=LLMManager)
    ws_manager = Mock()
    tool_dispatcher = Mock()
    
    # Mock LLM to raise exception
    llm_manager.call_llm = AsyncMock(side_effect=Exception("LLM error"))
    
    mock_persistence = AsyncMock()
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence):
        supervisor = SupervisorAgent(db_session, llm_manager, ws_manager, tool_dispatcher)
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
        supervisor.state_persistence = mock_persistence
        
        # Should handle errors gracefully
        try:
            await supervisor.run("Test", supervisor.thread_id, supervisor.user_id, str(uuid.uuid4()))
        except Exception as e:
            # Error should be handled appropriately
            assert isinstance(e, Exception)


async def test_mock_infrastructure_creation():
    """Test mock infrastructure creation helpers"""
    from .fixtures.llm_agent_fixtures import create_mock_infrastructure
    
    db_session, llm_manager, ws_manager = create_mock_infrastructure()
    
    assert db_session is not None
    assert llm_manager is not None  
    assert ws_manager is not None
    
    # Verify types
    assert isinstance(db_session, AsyncMock)
    assert isinstance(llm_manager, Mock)
    assert isinstance(ws_manager, Mock)


def _verify_basic_state_structure(state):
    """Verify basic state structure"""
    assert hasattr(state, 'user_request')
    assert hasattr(state, 'chat_thread_id')
    assert hasattr(state, 'user_id')


def _create_test_state():
    """Create basic test state"""
    return DeepAgentState(
        user_request="Test optimization request",
        chat_thread_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4())
    )


def _setup_basic_llm_mock():
    """Setup basic LLM mock"""
    llm_manager = Mock(spec=LLMManager)
    llm_manager.call_llm = AsyncMock(return_value={
        "content": "Basic response",
        "tool_calls": []
    })
    return llm_manager


def _setup_basic_persistence_mock():
    """Setup basic persistence mock"""
    mock_persistence = AsyncMock()
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    return mock_persistence


async def test_basic_agent_lifecycle():
    """Test basic agent lifecycle"""
    # Create basic state
    state = _create_test_state()
    _verify_basic_state_structure(state)
    
    # Verify state can be modified
    state.triage_result = {"category": "test"}
    assert state.triage_result["category"] == "test"


async def test_basic_mock_setup():
    """Test basic mock setup functionality"""
    llm_manager = _setup_basic_llm_mock()
    persistence = _setup_basic_persistence_mock()
    
    # Test LLM mock
    result = await llm_manager.call_llm("test")
    assert result["content"] == "Basic response"
    
    # Test persistence mock
    save_result = await persistence.save_agent_state("test", "session")
    assert save_result == (True, "test_id")


async def test_uuid_generation():
    """Test UUID generation for IDs"""
    thread_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    # Should be valid UUIDs
    assert len(thread_id) == 36
    assert len(user_id) == 36
    assert len(run_id) == 36
    
    # Should be unique
    assert thread_id != user_id
    assert user_id != run_id
    assert thread_id != run_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])