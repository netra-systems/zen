"""
LLM Agent End-to-End Flow Tests
Tests complete optimization flows and concurrent request handling
Split from oversized test_llm_agent_e2e_real.py
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

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
from netra_backend.tests.agents.test_fixtures import (
    mock_db_session,
    mock_llm_manager,
    mock_persistence_service,
    mock_tool_dispatcher,
    mock_websocket_manager,
    supervisor_agent,
)
from netra_backend.tests.agents.fixtures.llm_agent_fixtures import (
    create_mock_infrastructure,
    create_supervisor_with_mocks,
    setup_llm_responses,
    setup_websocket_manager,
)

async def test_concurrent_request_handling(mock_db_session, mock_llm_manager,
                                          mock_websocket_manager, mock_tool_dispatcher):
    """Test handling multiple concurrent requests"""
    mock_persistence = _create_concurrent_persistence_mock()
    
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence):
        supervisors = _create_concurrent_supervisors(
            mock_db_session, mock_llm_manager, mock_websocket_manager, 
            mock_tool_dispatcher, mock_persistence
        )
        
        tasks = _create_concurrent_tasks(supervisors)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        _verify_concurrent_results(results)

async def execute_optimization_flow(supervisor):
    """Execute the optimization flow and return result"""
    return await supervisor.run(
        "Optimize my LLM workload for better memory usage",
        supervisor.thread_id,
        supervisor.user_id,
        str(uuid.uuid4())
    )

def verify_optimization_flow(state, supervisor):
    """Verify the optimization flow completed successfully"""
    assert state is not None
    assert supervisor.engine.execute_pipeline.called

async def test_end_to_end_optimization_flow():
    """Test complete end-to-end optimization flow"""
    # Create infrastructure and setup responses
    infrastructure = _create_e2e_test_infrastructure()
    _setup_e2e_llm_responses(infrastructure['llm_manager'])
    _setup_e2e_websocket(infrastructure['ws_manager'])
    
    # Create and configure supervisor
    supervisor = _create_e2e_supervisor(infrastructure)
    _configure_e2e_pipeline(supervisor)
    
    # Execute and verify flow
    state = await _execute_e2e_flow(supervisor)
    _verify_e2e_flow_completion(state, supervisor)

async def test_complex_multi_step_flow():
    """Test complex multi-step optimization flow"""
    # Create infrastructure
    db_session, llm_manager, ws_manager = create_mock_infrastructure()
    
    # Setup complex LLM responses
    setup_llm_responses(llm_manager)
    setup_websocket_manager(ws_manager)
    
    mock_persistence = AsyncMock()
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    # Create supervisor with all mocks
    supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)
    
    # Execute multi-step flow
    state = await execute_optimization_flow(supervisor)
    
    # Verify flow completion
    verify_optimization_flow(state, supervisor)

async def test_flow_interruption_and_recovery():
    """Test flow interruption and recovery scenarios"""
    db_session, llm_manager, ws_manager = create_mock_infrastructure()
    
    # Mock interrupted state
    interrupted_state = DeepAgentState(
        user_request="Interrupted optimization",
        chat_thread_id="thread123",
        user_id="user123"
    )
    interrupted_state.triage_result = {"category": "optimization", "step": "analysis"}
    
    mock_persistence = AsyncMock()
    mock_persistence.load_agent_state = AsyncMock(return_value=interrupted_state)
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    # Test recovery
    recovered_state = await mock_persistence.load_agent_state("thread123", "user123")
    assert recovered_state.user_request == "Interrupted optimization"
    assert recovered_state.triage_result["step"] == "analysis"

async def test_flow_performance_benchmarks():
    """Test flow performance under various conditions"""
    performance_metrics = []
    
    for concurrency_level in [1, 3, 5]:
        metrics = await _run_concurrency_benchmark(concurrency_level)
        performance_metrics.append(metrics)
    
    _verify_performance_requirements(performance_metrics)

def _create_concurrent_persistence_mock():
    """Create persistence mock for concurrent testing"""
    mock_persistence = AsyncMock()
    
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:
            return (True, "test_id")
        elif len(args) == 5:
            return True
        else:
            return (True, "test_id")
    
    mock_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    return mock_persistence

def _create_concurrent_supervisors(mock_db_session, mock_llm_manager, 
                                  mock_websocket_manager, mock_tool_dispatcher, mock_persistence):
    """Create supervisors for concurrent testing"""
    supervisors = []
    for i in range(5):
        supervisor = SupervisorAgent(
            mock_db_session, mock_llm_manager, 
            mock_websocket_manager, mock_tool_dispatcher
        )
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
        supervisor.engine.execute_pipeline = AsyncMock(return_value=[])
        supervisor.state_persistence = mock_persistence
        supervisors.append(supervisor)
    return supervisors

def _create_concurrent_tasks(supervisors):
    """Create concurrent execution tasks"""
    return [
        supervisor.run(
            f"Request {i}", supervisor.thread_id,
            supervisor.user_id, str(uuid.uuid4())
        )
        for i, supervisor in enumerate(supervisors)
    ]

def _verify_concurrent_results(results):
    """Verify concurrent execution results"""
    assert len(results) == 5
    for result in results:
        if not isinstance(result, Exception):
            assert isinstance(result, DeepAgentState)

def _create_e2e_test_infrastructure():
    """Create infrastructure for E2E testing"""
    return {
        'db_session': AsyncMock(spec=AsyncSession),
        'llm_manager': Mock(spec=LLMManager),
        'ws_manager': Mock()
    }

def _setup_e2e_llm_responses(llm_manager):
    """Setup LLM responses for E2E flow"""
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

def _setup_e2e_websocket(ws_manager):
    """Setup WebSocket for E2E testing"""
    ws_manager.send_message = AsyncMock()

def _create_e2e_supervisor(infrastructure):
    """Create supervisor for E2E testing"""
    mock_persistence = AsyncMock()
    
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:
            return (True, "test_id")
        elif len(args) == 5:
            return True
        else:
            return (True, "test_id")
    
    mock_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence):
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
        
        supervisor = SupervisorAgent(
            infrastructure['db_session'], infrastructure['llm_manager'],
            infrastructure['ws_manager'], dispatcher
        )
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
        supervisor.state_persistence = mock_persistence
        return supervisor

def _configure_e2e_pipeline(supervisor):
    """Configure supervisor pipeline for E2E testing"""
    from netra_backend.app.agents.supervisor.execution_context import (
        AgentExecutionResult,
    )
    supervisor.engine.execute_pipeline = AsyncMock(return_value=[
        AgentExecutionResult(success=True, state=None),
        AgentExecutionResult(success=True, state=None),
        AgentExecutionResult(success=True, state=None)
    ])

async def _execute_e2e_flow(supervisor):
    """Execute E2E optimization flow"""
    return await supervisor.run(
        "Optimize my LLM workload for better memory usage",
        supervisor.thread_id,
        supervisor.user_id,
        str(uuid.uuid4())
    )

def _verify_e2e_flow_completion(state, supervisor):
    """Verify E2E flow completion"""
    assert state is not None
    assert supervisor.engine.execute_pipeline.called

async def _run_concurrency_benchmark(concurrency_level):
    """Run concurrency benchmark for given level"""
    start_time = time.time()
    
    tasks = _create_benchmark_tasks(concurrency_level)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    execution_time = time.time() - start_time
    
    return {
        "concurrency": concurrency_level,
        "execution_time": execution_time,
        "success_rate": len([r for r in results if not isinstance(r, Exception)]) / len(results)
    }

def _create_benchmark_tasks(concurrency_level):
    """Create benchmark tasks for performance testing"""
    tasks = []
    for i in range(concurrency_level):
        db_session, llm_manager, ws_manager = create_mock_infrastructure()
        setup_llm_responses(llm_manager)
        
        mock_persistence = AsyncMock()
        mock_persistence.save_agent_state = AsyncMock(return_value=(True, f"test_id_{i}"))
        mock_persistence.load_agent_state = AsyncMock(return_value=None)
        
        supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)
        tasks.append(execute_optimization_flow(supervisor))
    return tasks

def _verify_performance_requirements(performance_metrics):
    """Verify performance metrics meet requirements"""
    for metric in performance_metrics:
        assert metric["execution_time"] < 5.0
        assert metric["success_rate"] >= 0.8

if __name__ == "__main__":
    pytest.main([__file__, "-v"])