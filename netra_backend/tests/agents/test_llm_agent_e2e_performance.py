"""
Performance E2E LLM Agent Tests  
Performance metrics, concurrency, error recovery, and complete optimization flows
Split from oversized test_llm_agent_e2e_real.py to maintain 450-line limit

BVJ:
1. Segment: Growth & Enterprise
2. Business Goal: Ensure agent performance meets customer SLA requirements
3. Value Impact: Prevents performance degradation that could reduce optimization efficiency  
4. Revenue Impact: Maintains customer satisfaction and prevents performance-related churn
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

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

# Add project root to path
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.tests.agents.test_fixtures import (
    create_mock_infrastructure,
    create_supervisor_with_mocks,
    mock_db_session,
    # Add project root to path
    mock_llm_manager,
    mock_persistence_service,
    mock_tool_dispatcher,
    mock_websocket_manager,
    setup_llm_responses,
    setup_websocket_manager,
    supervisor_agent,
)
from netra_backend.tests.helpers.performance_test_helpers import (
    create_benchmark_supervisor,
    create_e2e_persistence_mock,
    create_flow_persistence_mock,
    create_lightweight_supervisor,
    execute_lightweight_flow,
    execute_optimization_flow,
    run_concurrency_benchmark,
    setup_e2e_responses,
    verify_performance_requirements,
)


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


async def test_error_recovery(supervisor_agent):
    """Test error handling and recovery mechanisms"""
    # Simulate error in execution pipeline
    supervisor_agent.engine.execute_pipeline = AsyncMock(
        side_effect=Exception("Pipeline error")
    )
    
    # Should handle error gracefully
    try:
        await supervisor_agent.run(
            "Test error",
            supervisor_agent.thread_id,
            supervisor_agent.user_id,
            str(uuid.uuid4())
        )
    except Exception as e:
        assert "Pipeline error" in str(e)


async def test_concurrent_request_handling_optimized():
    """Test handling multiple concurrent requests with optimized setup"""
    # Create optimized mock infrastructure
    supervisors = _create_concurrent_supervisors(3)
    
    # Run concurrent requests
    tasks = _create_concurrent_tasks(supervisors)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify all completed
    assert len(results) == 3
    _verify_concurrent_results(results)


async def test_end_to_end_optimization_flow_optimized():
    """Test complete end-to-end optimization flow with optimized structure"""
    # Create infrastructure with optimized setup
    infrastructure = _create_e2e_infrastructure()
    supervisor = _create_e2e_supervisor(infrastructure)
    
    # Run full flow
    state = await _execute_e2e_flow(supervisor)
    
    # Verify complete flow
    _verify_e2e_completion(state, supervisor)


async def test_complex_multi_step_flow():
    """Test complex multi-step optimization flow"""
    # Create infrastructure
    db_session, llm_manager, ws_manager = create_mock_infrastructure()
    
    # Setup complex responses
    _setup_complex_flow_responses(llm_manager, ws_manager)
    
    mock_persistence = _create_flow_persistence_mock()
    
    # Create supervisor with all mocks
    supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)
    
    # Execute multi-step flow
    state = await _execute_optimization_flow(supervisor)
    
    # Verify flow completion
    _verify_optimization_flow(state, supervisor)


async def test_flow_interruption_and_recovery():
    """Test flow interruption and recovery scenarios"""
    db_session, llm_manager, ws_manager = create_mock_infrastructure()
    
    # Create interrupted state scenario
    interrupted_state = _create_interrupted_state()
    
    mock_persistence = _create_recovery_persistence_mock(interrupted_state)
    
    # Test recovery
    recovered_state = await mock_persistence.load_agent_state("thread123", "user123")
    _verify_recovery_state(recovered_state)


async def test_flow_performance_benchmarks():
    """Test flow performance under various conditions"""
    performance_metrics = []
    
    for concurrency_level in [1, 3, 5]:
        metrics = await _run_performance_benchmark(concurrency_level)
        performance_metrics.append(metrics)
    
    # Verify performance is reasonable
    _verify_performance_metrics(performance_metrics)


async def test_high_load_scenarios():
    """Test system behavior under high load"""
    # Create high load scenario
    task_count = 10
    start_time = time.time()
    
    tasks = []
    for i in range(task_count):
        infrastructure = _create_lightweight_infrastructure()
        supervisor = _create_lightweight_supervisor(infrastructure)
        tasks.append(_execute_lightweight_flow(supervisor))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    execution_time = time.time() - start_time
    
    # Verify high load performance
    success_count = len([r for r in results if not isinstance(r, Exception)])
    assert success_count >= task_count * 0.8  # 80% success rate
    assert execution_time < 10.0  # Should complete within 10 seconds


def _create_concurrent_supervisors(count):
    """Create supervisors for concurrent testing"""
    supervisors = []
    for i in range(count):
        infrastructure = _create_mock_infrastructure_light()
        supervisor = _create_lightweight_supervisor(infrastructure)
        supervisors.append(supervisor)
    return supervisors


def _create_concurrent_tasks(supervisors):
    """Create concurrent execution tasks"""
    return [
        supervisor.run(
            f"Request {i}",
            supervisor.thread_id,
            supervisor.user_id,
            str(uuid.uuid4())
        )
        for i, supervisor in enumerate(supervisors)
    ]


def _verify_concurrent_results(results):
    """Verify concurrent execution results"""
    for result in results:
        if not isinstance(result, Exception):
            assert isinstance(result, DeepAgentState)


def _create_e2e_infrastructure():
    """Create infrastructure for end-to-end testing"""
    db_session = AsyncMock(spec=AsyncSession)
    llm_manager = Mock(spec=LLMManager)
    ws_manager = Mock()
    return (db_session, llm_manager, ws_manager)


def _create_e2e_supervisor(infrastructure):
    """Create supervisor for end-to-end testing"""
    db_session, llm_manager, ws_manager = infrastructure
    _setup_e2e_responses(llm_manager)
    ws_manager.send_message = AsyncMock()
    
    mock_persistence = _create_e2e_persistence_mock()
    return create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)


async def _execute_e2e_flow(supervisor):
    """Execute end-to-end optimization flow"""
    return await supervisor.run(
        "Optimize my LLM workload for better memory usage",
        supervisor.thread_id,
        supervisor.user_id,
        str(uuid.uuid4())
    )


def _verify_e2e_completion(state, supervisor):
    """Verify end-to-end flow completion"""
    assert state is not None
    assert supervisor.engine.execute_pipeline.called


def _setup_complex_flow_responses(llm_manager, ws_manager):
    """Setup complex flow responses"""
    setup_llm_responses(llm_manager)
    setup_websocket_manager(ws_manager)


def _create_flow_persistence_mock():
    """Create persistence mock for flow testing"""
    mock_persistence = AsyncMock()
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    return mock_persistence


async def _execute_optimization_flow(supervisor):
    """Execute optimization flow and return result"""
    return await supervisor.run(
        "Optimize my LLM workload for better memory usage",
        supervisor.thread_id,
        supervisor.user_id,
        str(uuid.uuid4())
    )


def _verify_optimization_flow(state, supervisor):
    """Verify optimization flow completed successfully"""
    assert state is not None
    assert supervisor.engine.execute_pipeline.called


def _create_interrupted_state():
    """Create interrupted state for testing"""
    interrupted_state = DeepAgentState(
        user_request="Interrupted optimization",
        chat_thread_id="thread123", 
        user_id="user123"
    )
    interrupted_state.triage_result = {"category": "optimization", "step": "analysis"}
    return interrupted_state


def _create_recovery_persistence_mock(interrupted_state):
    """Create recovery persistence mock"""
    mock_persistence = AsyncMock()
    mock_persistence.load_agent_state = AsyncMock(return_value=interrupted_state)
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    return mock_persistence


def _verify_recovery_state(recovered_state):
    """Verify recovered state"""
    assert recovered_state.user_request == "Interrupted optimization"
    assert recovered_state.triage_result["step"] == "analysis"


async def _run_performance_benchmark(concurrency_level):
    """Run performance benchmark for given concurrency level"""
    start_time = time.time()
    
    # Create concurrent flows
    tasks = []
    for i in range(concurrency_level):
        infrastructure = _create_benchmark_infrastructure()
        supervisor = _create_benchmark_supervisor(infrastructure, i)
        tasks.append(_execute_optimization_flow(supervisor))
    
    # Execute all tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)
    execution_time = time.time() - start_time
    
    return {
        "concurrency": concurrency_level,
        "execution_time": execution_time,
        "success_rate": len([r for r in results if not isinstance(r, Exception)]) / len(results)
    }


def _verify_performance_metrics(performance_metrics):
    """Verify performance metrics meet requirements"""
    for metric in performance_metrics:
        assert metric["execution_time"] < 5.0  # Should complete within 5 seconds
        assert metric["success_rate"] >= 0.8  # At least 80% success rate




if __name__ == "__main__":
    pytest.main([__file__, "-v"])