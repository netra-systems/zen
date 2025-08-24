"""
Supervisor Agent Orchestration Tests - Basic Operations
Tests for basic agent coordination, sequential/parallel execution, and state management.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from netra_backend.app.schemas import SubAgentLifecycle

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.tests.helpers.supervisor_extensions import (
    install_supervisor_extensions,
)
from netra_backend.tests.supervisor_test_helpers import (
    assert_agent_called,
    create_agent_state,
    create_execution_context,
    create_supervisor_agent,
    create_supervisor_mocks,
    setup_data_agent_mock,
    setup_optimization_agent_mock,
    setup_triage_agent_mock,
)

# Install extension methods for testing
install_supervisor_extensions()

class TestSupervisorOrchestration:
    """Test agent coordination and workflow orchestration"""
    
    @pytest.mark.asyncio
    
    async def test_sequential_agent_execution(self):
        """Test sequential execution of multiple agents"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Setup agents in sequence: triage -> data -> optimization
        setup_triage_agent_mock(supervisor, {
            'user_request': "Analyze and optimize",
            'triage_result': {"message_type": "complex_query", "requires_data": True}
        })
        
        setup_data_agent_mock(supervisor, {
            'user_request': "Analyze and optimize",
            'data_result': {"analysis": {"metrics": {"accuracy": 0.85}, "trends": "stable"}}
        })
        
        setup_optimization_agent_mock(supervisor, {
            'user_request': "Analyze and optimize",
            'optimizations_result': {
                "optimization_type": "performance",
                "recommendations": ["Increase batch size", "Use mixed precision"]
            }
        })
        
        state = create_agent_state("Analyze and optimize")
        context = create_execution_context("orchestration-test")
        
        # Execute in sequence
        triage_result = await supervisor._route_to_agent(state, context, "triage")
        assert triage_result.success
        
        data_result = await supervisor._route_to_agent(triage_result.state, context, "data")
        assert data_result.success
        
        opt_result = await supervisor._route_to_agent(data_result.state, context, "optimization")
        assert opt_result.success
        
        # Verify final state contains all results
        final_state = opt_result.state
        assert final_state.triage_result.category == "complex_query"
        assert final_state.data_result.confidence_score == 0.85
        assert len(final_state.optimizations_result.recommendations) == 2
        
    @pytest.mark.asyncio
        
    async def test_parallel_agent_execution(self):
        """Test parallel execution of independent agents"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Setup independent agents that can run in parallel
        async def mock_data_execute(state, run_id, stream_updates=True):
            await asyncio.sleep(0.05)  # Simulate work
            state.data_result = {"analysis": "complete", "duration": 0.05}
            return state
        
        async def mock_opt_execute(state, run_id, stream_updates=True):
            await asyncio.sleep(0.03)  # Different duration
            state.optimizations_result = {
                "optimization_type": "parallel_test",
                "recommendations": ["Parallel optimization complete"]
            }
            return state
        
        supervisor.agents["data"].execute = mock_data_execute
        supervisor.agents["optimization"].execute = mock_opt_execute
        
        state = create_agent_state("Parallel test")
        context = create_execution_context("parallel-test")
        
        # Execute in parallel
        start_time = asyncio.get_event_loop().time()
        
        tasks = [
            supervisor._route_to_agent(state, context, "data"),
            supervisor._route_to_agent(state, context, "optimization")
        ]
        
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Should complete faster than sequential execution
        assert end_time - start_time < 0.09  # Less than sum of individual times
        
        # Both should succeed
        assert all(result.success for result in results)
        assert results[0].state.data_result["analysis"] == "complete"
        assert results[1].state.optimizations_result["optimization_type"] == "parallel_test"
        
    @pytest.mark.asyncio
        
    async def test_conditional_workflow_branching(self):
        """Test conditional workflow based on intermediate results"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Setup triage that determines workflow branch
        setup_triage_agent_mock(supervisor, {
            'user_request': "Branch test",
            'triage_result': {
                "message_type": "optimization_query",
                "complexity": "high",
                "requires_data": True,
                "requires_specialized_optimization": True
            }
        })
        
        # Setup different paths based on triage result
        setup_data_agent_mock(supervisor, {
            'user_request': "Branch test",
            'data_result': {"complexity_confirmed": True, "data_volume": "large"}
        })
        
        # Mock specialized optimization agent
        spec_opt_agent = supervisor.agents.get("optimization")
        spec_opt_agent.execute = AsyncMock()
        spec_opt_agent.execute.return_value = create_agent_state("Branch test",
                                                               optimizations_result={
                                                                   "optimization_type": "specialized",
                                                                   "recommendations": ["Advanced GPU optimization"],
                                                                   "estimated_improvement": "25%"
                                                               })
        
        state = create_agent_state("Branch test")
        context = create_execution_context("branch-test")
        
        # Execute workflow with branching logic
        triage_result = await supervisor._route_to_agent(state, context, "triage")
        assert triage_result.success
        
        # Branch 1: If requires_data, run data agent
        if triage_result.state.triage_result.suggested_workflow.next_agent == "DataSubAgent":
            data_result = await supervisor._route_to_agent(triage_result.state, context, "data")
            assert data_result.success
            current_state = data_result.state
        else:
            current_state = triage_result.state
        
        # Branch 2: If requires specialized optimization, use specialized path
        if len(triage_result.state.triage_result.suggested_workflow.required_data_sources) > 0:
            opt_result = await supervisor._route_to_agent(current_state, context, "optimization")
            assert opt_result.success
            assert opt_result.state.optimizations_result["optimization_type"] == "specialized"
            
    @pytest.mark.asyncio
            
    async def test_state_accumulation_across_agents(self):
        """Test that state accumulates properly across multiple agents"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Each agent adds to the state
        triage_agent = supervisor.agents["triage"]
        triage_agent.execute = AsyncMock()
        # Create state with triage_result manually to avoid type conversion
        triage_state = create_agent_state("State test")
        triage_state.triage_result = {"step": 1, "agent": "triage"}
        triage_agent.execute.return_value = triage_state
        
        data_agent = supervisor.agents["data"]
        data_agent.execute = AsyncMock()
        
        def mock_data_execute(state, run_id, stream_updates=True):
            # Modify state in place to avoid type conversion
            state.data_result = {"step": 2, "agent": "data", "previous_steps": [1]}
            return state
        
        data_agent.execute.side_effect = mock_data_execute
        
        opt_agent = supervisor.agents["optimization"]
        opt_agent.execute = AsyncMock()
        
        async def mock_opt_execute(state, run_id, stream_updates=True):
            # Modify state in place to avoid type conversion
            state.optimizations_result = {
                "optimization_type": "accumulated",
                "step": 3,
                "agent": "optimization",
                "previous_steps": [1, 2]
            }
            return state
        
        opt_agent.execute.side_effect = mock_opt_execute
        
        state = create_agent_state("State test")
        context = create_execution_context("accumulation-test")
        
        # Execute agents sequentially
        result1 = await supervisor._route_to_agent(state, context, "triage")
        result2 = await supervisor._route_to_agent(result1.state, context, "data")
        result3 = await supervisor._route_to_agent(result2.state, context, "optimization")
        
        # Verify state accumulation
        final_state = result3.state
        assert final_state.triage_result["step"] == 1
        assert final_state.data_result["step"] == 2
        assert final_state.optimizations_result["step"] == 3
        
        # Verify state references previous steps
        assert final_state.data_result["previous_steps"] == [1]
        assert final_state.optimizations_result["previous_steps"] == [1, 2]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
