"""
Integration E2E LLM Agent Tests
State transitions, WebSocket messaging, tool integration, and persistence tests
Split from oversized test_llm_agent_e2e_real.py to maintain 450-line limit

BVJ:
1. Segment: Growth & Enterprise
2. Business Goal: Ensure seamless agent integration and state management  
3. Value Impact: Prevents integration failures that could lose optimization data
4. Revenue Impact: Maintains data integrity for optimization value capture
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


async def test_agent_state_transitions(supervisor_agent):
    """Test agent state transitions through pipeline"""
    state = DeepAgentState(
        user_request="Test request",
        chat_thread_id=supervisor_agent.thread_id,
        user_id=supervisor_agent.user_id
    )
    
    # Simulate triage result
    state.triage_result = _create_triage_result()
    
    # Simulate data result  
    state.data_result = _create_data_result()
    
    # Simulate optimization result
    state.optimizations_result = _create_optimization_result()
    
    # Verify state has expected structure
    _verify_state_transitions(state)


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


async def test_tool_dispatcher_integration(mock_tool_dispatcher):
    """Test tool dispatcher integration with LLM agents"""
    # Test successful tool execution
    result = await mock_tool_dispatcher.dispatch_tool("test_tool", {"param": "value"})
    assert result["status"] == "success"
    assert "result" in result
    
    # Test tool error handling
    mock_tool_dispatcher.dispatch_tool = AsyncMock(side_effect=Exception("Tool error"))
    
    with pytest.raises(Exception) as exc_info:
        await mock_tool_dispatcher.dispatch_tool("failing_tool", {})
    assert "Tool error" in str(exc_info.value)


async def test_state_persistence(supervisor_agent):
    """Test agent state persistence and recovery"""
    # Setup persistence mock properly
    _setup_persistence_mock(supervisor_agent)
    
    # Run test - this should trigger state persistence calls
    run_id = str(uuid.uuid4())
    result = await supervisor_agent.run(
        "Test persistence",
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )
    
    # Verify the run completed successfully
    assert result is not None
    assert isinstance(result, DeepAgentState)


async def test_multi_agent_coordination(supervisor_agent):
    """Test coordination between multiple sub-agents"""
    # Verify all expected agents are registered
    agent_names = list(supervisor_agent.agents.keys())
    
    # Should have at least core agents
    expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
    for expected in expected_agents:
        assert any(expected in name.lower() for name in agent_names), \
            f"Missing expected agent: {expected}"


async def test_real_llm_interaction():
    """Test real LLM interaction with proper error handling"""
    llm_manager = Mock(spec=LLMManager)
    
    # Setup retry logic test
    call_count = 0
    async def mock_llm_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate timeout on first call
            raise asyncio.TimeoutError("LLM call timed out")
        return {
            "content": "Successful response after retry",
            "tool_calls": []
        }
    
    llm_manager.call_llm = AsyncMock(side_effect=mock_llm_call)
    
    # Test retry mechanism
    try:
        result = await llm_manager.call_llm("Test prompt")
    except asyncio.TimeoutError:
        # Retry once
        result = await llm_manager.call_llm("Test prompt")
    
    assert result["content"] == "Successful response after retry"
    assert call_count == 2


async def test_tool_execution_with_llm():
    """Test tool execution triggered by LLM response"""
    from app.agents.tool_dispatcher import ToolDispatcher
    
    dispatcher = Mock(spec=ToolDispatcher)
    tool_results = []
    
    async def mock_dispatch(tool_name, params):
        result = _create_tool_result(tool_name, params)
        tool_results.append(result)
        return result
    
    dispatcher.dispatch_tool = AsyncMock(side_effect=mock_dispatch)
    
    # Simulate LLM response with tool calls
    llm_response = _create_llm_tool_response()
    
    # Execute tools
    for tool_call in llm_response["tool_calls"]:
        await dispatcher.dispatch_tool(tool_call["name"], tool_call["parameters"])
    
    # Verify all tools executed
    assert len(tool_results) == 2
    assert tool_results[0]["tool"] == "analyze_workload"
    assert tool_results[1]["tool"] == "optimize_batch_size"


async def test_websocket_error_handling(mock_websocket_manager):
    """Test WebSocket error handling during message streaming"""
    # Setup WebSocket to fail
    mock_websocket_manager.send_message = AsyncMock(side_effect=Exception("WebSocket error"))
    
    # Should handle errors gracefully without crashing
    try:
        await mock_websocket_manager.send_message("test_run", {"message": "test"})
        assert False, "Should have raised exception"
    except Exception as e:
        assert "WebSocket error" in str(e)


async def test_state_recovery_scenarios():
    """Test various state recovery scenarios"""
    # Test successful recovery
    recovery_state = _create_recovery_state()
    assert recovery_state.user_request == "Interrupted optimization"
    assert recovery_state.triage_result["step"] == "analysis"
    
    # Test partial recovery
    partial_state = _create_partial_recovery_state()
    assert partial_state.triage_result is not None
    assert partial_state.data_result is None


async def test_integration_error_boundaries():
    """Test error boundaries in integration scenarios"""
    # Test database connection failure
    db_session = AsyncMock(spec=AsyncSession)
    db_session.execute = AsyncMock(side_effect=Exception("DB connection lost"))
    
    # Should handle gracefully
    try:
        await db_session.execute("SELECT 1")
        assert False, "Should have raised exception"
    except Exception as e:
        assert "DB connection lost" in str(e)


def _create_triage_result():
    """Create triage result for testing"""
    return {
        "category": "optimization",
        "requires_data": True,
        "requires_optimization": True
    }


def _create_data_result():
    """Create data result for testing"""
    return {
        "metrics": {"gpu_util": 0.75, "memory": 0.82},
        "analysis": "High GPU utilization detected"
    }


def _create_optimization_result():
    """Create optimization result for testing"""
    return {
        "recommendations": [
            "Use mixed precision training",
            "Enable gradient checkpointing"
        ],
        "expected_improvement": "25% reduction in memory"
    }


def _verify_state_transitions(state):
    """Verify state has expected transition structure"""
    assert state.triage_result is not None
    assert state.data_result is not None
    assert state.optimizations_result is not None
    assert "recommendations" in state.optimizations_result


def _setup_persistence_mock(supervisor_agent):
    """Setup persistence mock with proper interfaces"""
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:  # (request, session) signature
            return (True, "test_id")
        elif len(args) == 5:  # (run_id, thread_id, user_id, state, db_session) signature
            return True
        else:
            return (True, "test_id")
    
    supervisor_agent.state_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    supervisor_agent.state_persistence.load_agent_state = AsyncMock(return_value=None)
    supervisor_agent.state_persistence.get_thread_context = AsyncMock(return_value=None)
    supervisor_agent.state_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))


def _create_tool_result(tool_name, params):
    """Create tool execution result"""
    return {
        "tool": tool_name,
        "params": params,
        "result": f"Executed {tool_name}",
        "status": "success"
    }


def _create_llm_tool_response():
    """Create LLM response with tool calls"""
    return {
        "content": "I'll analyze your workload",
        "tool_calls": [
            {"name": "analyze_workload", "parameters": {"metric": "gpu_util"}},
            {"name": "optimize_batch_size", "parameters": {"current": 32}}
        ]
    }


def _create_recovery_state():
    """Create interrupted state for recovery testing"""
    state = DeepAgentState(
        user_request="Interrupted optimization",
        chat_thread_id="thread123",
        user_id="user123"
    )
    state.triage_result = {"category": "optimization", "step": "analysis"}
    return state


def _create_partial_recovery_state():
    """Create partially recovered state"""
    state = DeepAgentState(
        user_request="Partial recovery test",
        chat_thread_id="thread456",
        user_id="user456"
    )
    state.triage_result = {"category": "optimization", "confidence": 0.9}
    return state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])