"""
Supervisor Agent Orchestration Tests - Workflow Patterns
Tests for advanced workflow patterns, resource management, and coordination strategies.
Compliance: <300 lines, 25-line max functions, modular design.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

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
from netra_backend.tests.supervisor_extensions import (
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

class TestWorkflowPatterns:
    """Test common workflow patterns and coordination strategies"""
    
    async def _setup_fanout_supervisor(self):
        """Setup supervisor with mocks for fan-out test"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        setup_triage_agent_mock(supervisor, {
            'user_request': "Fan out test",
            'triage_result': {"parallel_tasks": ["data_analysis", "optimization", "validation"]}
        })
        return supervisor

    async def _mock_data_processor(self, state, run_id, stream_updates=True):
        """Mock data processor for fan-out test"""
        await asyncio.sleep(0.02)
        state.data_result = {"processor": "data", "result": "data_processed"}
        return state

    async def _mock_opt_processor(self, state, run_id, stream_updates=True):
        """Mock optimization processor for fan-out test"""
        await asyncio.sleep(0.03)
        state.optimizations_result = {
            "optimization_type": "processor_test",
            "processor": "optimization",
            "result": "optimizations_processed"
        }
        return state

    async def _mock_validation_processor(self, state, run_id, stream_updates=True):
        """Mock validation processor for fan-out test"""
        await asyncio.sleep(0.01)
        if hasattr(state, 'data_result') and state.data_result:
            state.data_result["validation"] = {"processor": "validation", "status": "valid"}
        else:
            state.data_result = {"validation": {"processor": "validation", "status": "valid"}}
        return state

    def _setup_parallel_processors(self, supervisor):
        """Setup parallel processors for fan-out test"""
        supervisor.agents["data"].execute = self._mock_data_processor
        supervisor.agents["optimization"].execute = self._mock_opt_processor
        validation_agent = AsyncMock()
        validation_agent.execute = self._mock_validation_processor
        supervisor.agents["validation"] = validation_agent

    async def _execute_triage_phase(self, supervisor, state, context):
        """Execute triage phase of fan-out test"""
        triage_result = await supervisor._route_to_agent(state, context, "triage")
        assert triage_result.success
        return triage_result

    async def _execute_parallel_phase(self, supervisor, state, context):
        """Execute parallel processing phase"""
        # Create separate state copies for each parallel task to avoid conflicts
        import copy
        state_data = copy.deepcopy(state)
        state_opt = copy.deepcopy(state)
        state_val = copy.deepcopy(state)
        parallel_tasks = [
            supervisor._route_to_agent(state_data, context, "data"),
            supervisor._route_to_agent(state_opt, context, "optimization"),
            supervisor._route_to_agent(state_val, context, "validation")
        ]
        return await asyncio.gather(*parallel_tasks)

    def _verify_fanin_results(self, parallel_results):
        """Verify fan-in results from parallel processing"""
        assert all(result.success for result in parallel_results)
        data_result = next((r for r in parallel_results if hasattr(r.state, 'data_result') 
                          and r.state.data_result and r.state.data_result.get("processor") == "data"), None)
        opt_result = next((r for r in parallel_results if hasattr(r.state, 'optimizations_result') 
                          and r.state.optimizations_result), None)
        validation_result = next((r for r in parallel_results 
                               if hasattr(r.state, 'data_result') and r.state.data_result
                               and r.state.data_result.get("validation")), None)
        assert data_result and data_result.state.data_result["result"] == "data_processed"
        assert opt_result and opt_result.state.optimizations_result["result"] == "optimizations_processed"
        assert validation_result and validation_result.state.data_result["validation"]["status"] == "valid"

    async def test_fan_out_fan_in_pattern(self):
        """Test fan-out/fan-in pattern for parallel processing"""
        supervisor = await self._setup_fanout_supervisor()
        self._setup_parallel_processors(supervisor)
        state = create_agent_state("Fan out test")
        context = create_execution_context("fanout-test")
        triage_result = await self._execute_triage_phase(supervisor, state, context)
        parallel_results = await self._execute_parallel_phase(supervisor, triage_result.state, context)
        self._verify_fanin_results(parallel_results)
        
    async def test_pipeline_with_feedback_loops(self):
        """Test pipeline with feedback loops and iterative refinement"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        iteration_count = 0
        
        async def mock_iterative_processor(state, run_id, stream_updates=True):
            nonlocal iteration_count
            iteration_count += 1
            
            # Simulate improvement over iterations
            quality_score = min(0.5 + (iteration_count * 0.2), 0.9)
            
            state.optimizations_result = {
                "optimization_type": "iterative",
                "iteration": iteration_count,
                "quality_score": quality_score,
                "converged": quality_score >= 0.9
            }
            return state
        
        supervisor.agents["optimization"].execute = mock_iterative_processor
        
        state = create_agent_state("Iterative test")
        context = create_execution_context("feedback-test")
        
        # Iterative refinement loop
        max_iterations = 5
        current_state = state
        
        for iteration in range(max_iterations):
            result = await supervisor._route_to_agent(current_state, context, "optimization")
            assert result.success
            
            current_state = result.state
            quality_score = current_state.optimizations_result["quality_score"]
            
            # Check convergence
            if current_state.optimizations_result["converged"]:
                break
        
        # Verify convergence
        assert current_state.optimizations_result["converged"]
        assert current_state.optimizations_result["quality_score"] >= 0.9
        assert iteration_count <= 3  # Should converge quickly

class TestResourceManagement:
    """Test resource management and coordination"""
    
    async def test_resource_contention_handling(self):
        """Test handling of resource contention between agents"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Simulate resource lock mechanism
        resource_lock = asyncio.Lock()
        
        async def resource_intensive_task(agent_name, duration):
            async with resource_lock:
                await asyncio.sleep(duration)
                return f"{agent_name}_completed"
        
        # Setup agents that compete for resources
        async def mock_data_agent(state, run_id, stream_updates=True):
            result = await resource_intensive_task("data", 0.05)
            state.data_result = {"resource_usage": result}
            return state
        
        async def mock_opt_agent(state, run_id, stream_updates=True):
            result = await resource_intensive_task("optimization", 0.03)
            state.optimizations_result = {
                "optimization_type": "resource_test",
                "resource_usage": result
            }
            return state
        
        supervisor.agents["data"].execute = mock_data_agent
        supervisor.agents["optimization"].execute = mock_opt_agent
        
        state = create_agent_state("Resource test")
        context = create_execution_context("resource-test")
        
        # Launch competing tasks
        start_time = asyncio.get_event_loop().time()
        
        tasks = [
            supervisor._route_to_agent(state, context, "data"),
            supervisor._route_to_agent(state, context, "optimization")
        ]
        
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Should take longer than individual tasks due to contention
        assert end_time - start_time >= 0.08  # Sum of both tasks
        
        # Both should complete successfully
        assert all(result.success for result in results)
        assert "completed" in results[0].state.data_result["resource_usage"]
        assert "completed" in results[1].state.optimizations_result["resource_usage"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
