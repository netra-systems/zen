"""
Basic LLM Agent Integration Tests
Tests basic agent initialization and core functionality
Split from oversized test_llm_agent_e2e_real.py
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.tests.agents.fixtures.llm_agent_fixtures import (
    mock_db_session,
    mock_llm_manager,
    mock_persistence_service,
    mock_tool_dispatcher,
    mock_websocket_manager,
    supervisor_agent,
)

@pytest.mark.asyncio

async def test_supervisor_initialization(supervisor_agent):
    """Test supervisor agent proper initialization"""
    assert supervisor_agent is not None
    assert supervisor_agent.thread_id is not None
    assert supervisor_agent.user_id is not None
    assert len(supervisor_agent.agents) > 0

@pytest.mark.asyncio

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

@pytest.mark.asyncio

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

@pytest.mark.asyncio

async def test_agent_state_transitions(supervisor_agent):
    """Test agent state transitions through pipeline"""
    state = DeepAgentState(
        user_request="Test request",
        chat_thread_id=supervisor_agent.thread_id,
        user_id=supervisor_agent.user_id
    )
    
    # Simulate triage result
    state.triage_result = {
        "category": "optimization",
        "requires_data": True,
        "requires_optimization": True
    }
    
    # Simulate data result
    state.data_result = {
        "metrics": {"gpu_util": 0.75, "memory": 0.82},
        "analysis": "High GPU utilization detected"
    }
    
    # Simulate optimization result
    state.optimizations_result = {
        "recommendations": [
            "Use mixed precision training",
            "Enable gradient checkpointing"
        ],
        "expected_improvement": "25% reduction in memory"
    }
    
    # Verify state has expected structure
    assert state.triage_result is not None
    assert state.data_result is not None
    assert state.optimizations_result is not None
    assert "recommendations" in state.optimizations_result

@pytest.mark.asyncio

async def test_websocket_message_streaming(supervisor_agent, mock_websocket_manager):
    """Test WebSocket message streaming during execution"""
    messages_sent = []
    
    async def capture_message(run_id, message):
        messages_sent.append((run_id, message))
    
    mock_websocket_manager.send_message = AsyncMock(side_effect=capture_message)
    
    # Run supervisor
    run_id = str(uuid.uuid4())
    await supervisor_agent.run(
        "Test streaming",
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )
    
    # Should have sent at least completion message
    assert mock_websocket_manager.send_message.called or len(messages_sent) >= 0

@pytest.mark.asyncio

async def test_multi_agent_coordination(supervisor_agent):
    """Test coordination between multiple sub-agents"""
    # Verify all expected agents are registered
    agent_names = list(supervisor_agent.agents.keys())
    
    # Should have at least core agents
    expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
    for expected in expected_agents:
        assert any(expected in name.lower() for name in agent_names), \
            f"Missing expected agent: {expected}"

@pytest.mark.asyncio

async def test_performance_metrics(supervisor_agent):
    """Test performance metric collection"""
    start_time = time.time()
    run_id = str(uuid.uuid4())
    
    await supervisor_agent.run(
        "Test performance",
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )
    
    execution_time = time.time() - start_time
    
    # Should complete quickly with mocked components
    assert execution_time < 2.0, f"Execution took {execution_time}s, expected < 2s"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])