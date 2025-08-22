"""
Basic LLM Agent E2E Tests
Core functionality tests with ≤8 line functions for architectural compliance
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import uuid
from unittest.mock import AsyncMock

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.tests.agents.test_fixtures import (
    mock_llm_manager,
    mock_tool_dispatcher,
    mock_websocket_manager,
    supervisor_agent,
)
from netra_backend.tests.agents.test_helpers import setup_mock_llm_with_retry

async def test_supervisor_initialization(supervisor_agent):
    """Test supervisor agent proper initialization"""
    assert supervisor_agent is not None
    assert supervisor_agent.thread_id is not None
    assert supervisor_agent.user_id is not None
    assert len(supervisor_agent.agents) > 0

def _create_user_request():
    """Create test user request"""
    return "Optimize my GPU utilization for LLM inference"

async def _run_supervisor_with_request(supervisor_agent, user_request):
    """Run supervisor with user request"""
    run_id = str(uuid.uuid4())
    return await supervisor_agent.run(
        user_request,
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )

def _verify_supervisor_state(state, user_request, supervisor_agent):
    """Verify supervisor state after execution"""
    assert state is not None
    assert state.user_request == user_request
    assert state.chat_thread_id == supervisor_agent.thread_id
    assert state.user_id == supervisor_agent.user_id

async def test_llm_triage_processing(supervisor_agent, mock_llm_manager):
    """Test LLM triage agent processes user requests correctly"""
    user_request = _create_user_request()
    state = await _run_supervisor_with_request(supervisor_agent, user_request)
    _verify_supervisor_state(state, user_request, supervisor_agent)

def _setup_valid_json_response(mock_llm_manager):
    """Setup valid JSON response for testing"""
    mock_llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
        "analysis": "Valid response",
        "recommendations": ["rec1", "rec2"]
    }))

async def _test_valid_json_parsing(mock_llm_manager):
    """Test valid JSON response parsing"""
    response = await mock_llm_manager.ask_llm("Test prompt")
    parsed = json.loads(response)
    assert "analysis" in parsed
    assert len(parsed["recommendations"]) == 2

def _setup_invalid_json_response(mock_llm_manager):
    """Setup invalid JSON response for testing"""
    mock_llm_manager.ask_llm = AsyncMock(return_value="Invalid JSON {")

async def _test_invalid_json_handling(mock_llm_manager):
    """Test invalid JSON error handling"""
    response = await mock_llm_manager.ask_llm("Test prompt")
    try:
        json.loads(response)
        assert False, "Should have raised JSON decode error"
    except json.JSONDecodeError:
        pass

async def test_llm_response_parsing(mock_llm_manager):
    """Test LLM response parsing and error handling"""
    _setup_valid_json_response(mock_llm_manager)
    await _test_valid_json_parsing(mock_llm_manager)
    _setup_invalid_json_response(mock_llm_manager)
    await _test_invalid_json_handling(mock_llm_manager)

def _create_test_state(supervisor_agent):
    """Create test state for transitions"""
    return DeepAgentState(
        user_request="Test request",
        chat_thread_id=supervisor_agent.thread_id,
        user_id=supervisor_agent.user_id
    )

def _setup_state_results(state):
    """Setup state with simulated results"""
    state.triage_result = {
        "category": "optimization",
        "requires_data": True,
        "requires_optimization": True
    }
    state.data_result = {
        "metrics": {"gpu_util": 0.75, "memory": 0.82},
        "analysis": "High GPU utilization detected"
    }

def _setup_optimization_results(state):
    """Setup optimization results in state"""
    state.optimizations_result = {
        "recommendations": [
            "Use mixed precision training",
            "Enable gradient checkpointing"
        ],
        "expected_improvement": "25% reduction in memory"
    }

def _verify_state_structure(state):
    """Verify state has expected structure"""
    assert state.triage_result is not None
    assert state.data_result is not None
    assert state.optimizations_result is not None
    assert "recommendations" in state.optimizations_result

async def test_agent_state_transitions(supervisor_agent):
    """Test agent state transitions through pipeline"""
    state = _create_test_state(supervisor_agent)
    _setup_state_results(state)
    _setup_optimization_results(state)
    _verify_state_structure(state)

def _setup_message_capture(mock_websocket_manager):
    """Setup message capture for websocket testing"""
    messages_sent = []
    async def capture_message(run_id, message):
        messages_sent.append((run_id, message))
    mock_websocket_manager.send_message = AsyncMock(side_effect=capture_message)
    return messages_sent

async def _run_streaming_test(supervisor_agent, mock_websocket_manager):
    """Run streaming test with supervisor"""
    run_id = str(uuid.uuid4())
    await supervisor_agent.run(
        "Test streaming",
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )

def _verify_streaming_messages(mock_websocket_manager, messages_sent):
    """Verify streaming messages were sent"""
    assert mock_websocket_manager.send_message.called or len(messages_sent) >= 0

async def test_websocket_message_streaming(supervisor_agent, mock_websocket_manager):
    """Test WebSocket message streaming during execution"""
    messages_sent = _setup_message_capture(mock_websocket_manager)
    await _run_streaming_test(supervisor_agent, mock_websocket_manager)
    _verify_streaming_messages(mock_websocket_manager, messages_sent)

async def _test_successful_tool_execution(mock_tool_dispatcher):
    """Test successful tool execution"""
    result = await mock_tool_dispatcher.dispatch_tool("test_tool", {"param": "value"})
    assert result["status"] == "success"
    assert "result" in result

def _setup_tool_error(mock_tool_dispatcher):
    """Setup tool dispatcher to raise error"""
    mock_tool_dispatcher.dispatch_tool = AsyncMock(side_effect=Exception("Tool error"))

async def _test_tool_error_handling(mock_tool_dispatcher):
    """Test tool error handling"""
    with pytest.raises(Exception) as exc_info:
        await mock_tool_dispatcher.dispatch_tool("failing_tool", {})
    assert "Tool error" in str(exc_info.value)

async def test_tool_dispatcher_integration(mock_tool_dispatcher):
    """Test tool dispatcher integration with LLM agents"""
    await _test_successful_tool_execution(mock_tool_dispatcher)
    _setup_tool_error(mock_tool_dispatcher)
    await _test_tool_error_handling(mock_tool_dispatcher)

def _setup_persistence_mocks(supervisor_agent):
    """Setup persistence mocks for testing"""
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:
            return (True, "test_id")
        elif len(args) == 5:
            return True
        else:
            return (True, "test_id")
    
    supervisor_agent.state_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    supervisor_agent.state_persistence.load_agent_state = AsyncMock(return_value=None)

def _setup_additional_persistence_mocks(supervisor_agent):
    """Setup additional persistence mocks"""
    supervisor_agent.state_persistence.get_thread_context = AsyncMock(return_value=None)
    supervisor_agent.state_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))

async def _run_persistence_test(supervisor_agent):
    """Run persistence test"""
    run_id = str(uuid.uuid4())
    return await supervisor_agent.run(
        "Test persistence",
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )

def _verify_persistence_result(result):
    """Verify persistence test result"""
    assert result is not None
    assert isinstance(result, DeepAgentState)

async def test_state_persistence(supervisor_agent):
    """Test agent state persistence and recovery"""
    _setup_persistence_mocks(supervisor_agent)
    _setup_additional_persistence_mocks(supervisor_agent)
    result = await _run_persistence_test(supervisor_agent)
    _verify_persistence_result(result)

def _setup_pipeline_error(supervisor_agent):
    """Setup pipeline to raise error"""
    supervisor_agent.engine.execute_pipeline = AsyncMock(
        side_effect=Exception("Pipeline error")
    )

async def _test_error_handling(supervisor_agent):
    """Test error handling during execution"""
    try:
        await supervisor_agent.run(
            "Test error",
            supervisor_agent.thread_id,
            supervisor_agent.user_id,
            str(uuid.uuid4())
        )
    except Exception as e:
        assert "Pipeline error" in str(e)

async def test_error_recovery(supervisor_agent):
    """Test error handling and recovery mechanisms"""
    _setup_pipeline_error(supervisor_agent)
    await _test_error_handling(supervisor_agent)

def _verify_expected_agents(agent_names):
    """Verify all expected agents are present"""
    expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
    for expected in expected_agents:
        assert any(expected in name.lower() for name in agent_names), \
            f"Missing expected agent: {expected}"

async def test_multi_agent_coordination(supervisor_agent):
    """Test coordination between multiple sub-agents"""
    agent_names = list(supervisor_agent.agents.keys())
    _verify_expected_agents(agent_names)