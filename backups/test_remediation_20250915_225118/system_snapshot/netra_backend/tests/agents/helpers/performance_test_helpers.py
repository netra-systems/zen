"""
Performance Test Helpers
Helper functions for E2E performance testing to maintain 450-line limit
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, Mock

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

def create_benchmark_supervisor(infrastructure, index):
    """Create supervisor for benchmarking"""
    from netra_backend.tests.agents.fixtures.llm_agent_fixtures import (
        create_supervisor_with_mocks,
        setup_llm_responses,
    )
    
    db_session, llm_manager, ws_manager = infrastructure
    setup_llm_responses(llm_manager)
    
    # Mock: Generic component isolation for controlled unit testing
    mock_persistence = AsyncMock()
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, f"test_id_{index}"))
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    
    return create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)

def create_lightweight_supervisor(infrastructure):
    """Create lightweight supervisor for high load testing"""
    from netra_backend.tests.agents.fixtures.llm_agent_fixtures import create_supervisor_with_mocks
    
    db_session, llm_manager, ws_manager = infrastructure
    mock_persistence = create_flow_persistence_mock()
    return create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)

async def execute_lightweight_flow(supervisor):
    """Execute lightweight flow for high load testing"""
    return await supervisor.run(
        "Light test", supervisor.thread_id,
        supervisor.user_id, str(uuid.uuid4())
    )

def setup_e2e_responses(llm_manager):
    """Setup end-to-end LLM responses"""
    from unittest.mock import AsyncMock
    
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
    
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    llm_manager.ask_structured_llm = AsyncMock(side_effect=mock_structured_llm)
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.call_llm = AsyncMock(return_value={"content": "Optimization complete"})

def create_e2e_persistence_mock():
    """Create persistence mock for e2e testing"""
    # Mock: Generic component isolation for controlled unit testing
    mock_persistence = AsyncMock()
    
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:
            return (True, "test_id")
        elif len(args) == 5:
            return True
        else:
            return (True, "test_id")
    
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    return mock_persistence

def create_flow_persistence_mock():
    """Create persistence mock for flow testing"""
    # Mock: Generic component isolation for controlled unit testing
    mock_persistence = AsyncMock()
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.save_agent_state = AsyncMock(return_value=(True, "test_id"))
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.load_agent_state = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock_persistence.get_thread_context = AsyncMock(return_value=None)
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    return mock_persistence

async def run_concurrency_benchmark(concurrency_level):
    """Run concurrency benchmark for given level"""
    from netra_backend.tests.agents.fixtures.llm_agent_fixtures import (
        create_mock_infrastructure,
        create_supervisor_with_mocks,
        setup_llm_responses,
    )
    
    start_time = time.time()
    
    tasks = []
    for i in range(concurrency_level):
        db_session, llm_manager, ws_manager = create_mock_infrastructure()
        setup_llm_responses(llm_manager)
        
        # Mock: Generic component isolation for controlled unit testing
        mock_persistence = AsyncMock()
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_persistence.save_agent_state = AsyncMock(return_value=(True, f"test_id_{i}"))
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_persistence.load_agent_state = AsyncMock(return_value=None)
        
        supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)
        tasks.append(execute_optimization_flow(supervisor))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    execution_time = time.time() - start_time
    
    return {
        "concurrency": concurrency_level,
        "execution_time": execution_time,
        "success_rate": len([r for r in results if not isinstance(r, Exception)]) / len(results)
    }

async def execute_optimization_flow(supervisor):
    """Execute optimization flow and return result"""
    return await supervisor.run(
        "Optimize my LLM workload for better memory usage",
        supervisor.thread_id,
        supervisor.user_id,
        str(uuid.uuid4())
    )

def verify_performance_requirements(performance_metrics):
    """Verify performance metrics meet requirements"""
    for metric in performance_metrics:
        assert metric["execution_time"] < 5.0
        assert metric["success_rate"] >= 0.8
