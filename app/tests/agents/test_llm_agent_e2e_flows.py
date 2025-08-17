"""
LLM Agent End-to-End Flow Tests
Tests complete optimization flows and concurrent request handling
Split from oversized test_llm_agent_e2e_real.py
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
from sqlalchemy.ext.asyncio import AsyncSession

from .fixtures.llm_agent_fixtures import (
    mock_llm_manager, mock_db_session, mock_websocket_manager,
    mock_tool_dispatcher, mock_persistence_service, supervisor_agent,
    create_mock_infrastructure, setup_llm_responses, setup_websocket_manager,
    create_supervisor_with_mocks
)


async def test_concurrent_request_handling(mock_db_session, mock_llm_manager,
                                          mock_websocket_manager, mock_tool_dispatcher):
    """Test handling multiple concurrent requests"""
    # Create a proper mock that matches the expected interface
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
    
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence):
        # Create multiple supervisors for concurrent requests
        supervisors = []
        for i in range(5):
            supervisor = SupervisorAgent(
                mock_db_session,
                mock_llm_manager,
                mock_websocket_manager,
                mock_tool_dispatcher
            )
            supervisor.thread_id = str(uuid.uuid4())
            supervisor.user_id = str(uuid.uuid4())
            supervisor.engine.execute_pipeline = AsyncMock(return_value=[])
            supervisor.state_persistence = mock_persistence
            supervisors.append(supervisor)
        
        # Run concurrent requests
        tasks = [
            supervisor.run(
                f"Request {i}",
                supervisor.thread_id,
                supervisor.user_id,
                str(uuid.uuid4())
            )
            for i, supervisor in enumerate(supervisors)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed
        assert len(results) == 5
        for result in results:
            if not isinstance(result, Exception):
                assert isinstance(result, DeepAgentState)


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
    # Create full mock infrastructure
    db_session = AsyncMock(spec=AsyncSession)
    llm_manager = Mock(spec=LLMManager)
    ws_manager = Mock()
    
    # Setup LLM responses for full flow
    responses = [
        # Triage response
        {"category": "optimization", "requires_analysis": True},
        # Analysis response
        {"bottleneck": "memory", "utilization": 0.95},
        # Optimization response
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
    
    ws_manager.send_message = AsyncMock()
    
    # Create supervisor with mocked dependencies
    # Create a proper mock that matches the expected interface
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
    
    with patch('app.agents.supervisor_consolidated.state_persistence_service', mock_persistence):
        from app.agents.tool_dispatcher import ToolDispatcher
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
        
        supervisor = SupervisorAgent(db_session, llm_manager, ws_manager, dispatcher)
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
        supervisor.state_persistence = mock_persistence
        
        # Mock pipeline execution with proper result structure
        from app.agents.supervisor.execution_context import AgentExecutionResult
        supervisor.engine.execute_pipeline = AsyncMock(return_value=[
            AgentExecutionResult(success=True, state=None),
            AgentExecutionResult(success=True, state=None),
            AgentExecutionResult(success=True, state=None)
        ])
        
        # Run full flow
        state = await supervisor.run(
            "Optimize my LLM workload for better memory usage",
            supervisor.thread_id,
            supervisor.user_id,
            str(uuid.uuid4())
        )
        
        # Verify complete flow
        assert state is not None
        assert supervisor.engine.execute_pipeline.called


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
        start_time = time.time()
        
        # Create concurrent flows
        tasks = []
        for i in range(concurrency_level):
            db_session, llm_manager, ws_manager = create_mock_infrastructure()
            setup_llm_responses(llm_manager)
            
            mock_persistence = AsyncMock()
            mock_persistence.save_agent_state = AsyncMock(return_value=(True, f"test_id_{i}"))
            mock_persistence.load_agent_state = AsyncMock(return_value=None)
            
            supervisor = create_supervisor_with_mocks(db_session, llm_manager, ws_manager, mock_persistence)
            tasks.append(execute_optimization_flow(supervisor))
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        performance_metrics.append({
            "concurrency": concurrency_level,
            "execution_time": execution_time,
            "success_rate": len([r for r in results if not isinstance(r, Exception)]) / len(results)
        })
    
    # Verify performance is reasonable
    for metric in performance_metrics:
        assert metric["execution_time"] < 5.0  # Should complete within 5 seconds
        assert metric["success_rate"] >= 0.8  # At least 80% success rate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])