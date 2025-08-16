"""Supervisor Agent Orchestration Tests
Priority: P0 - CRITICAL
Coverage: Agent coordination, state management, and workflow orchestration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from app.agents.state import DeepAgentState
from app.schemas import SubAgentLifecycle
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher

from app.tests.helpers.supervisor_test_helpers import (
    create_supervisor_mocks, create_supervisor_agent, create_execution_context,
    create_agent_state, setup_triage_agent_mock, setup_data_agent_mock,
    setup_optimization_agent_mock, assert_agent_called
)
from app.tests.helpers.supervisor_extensions import install_supervisor_extensions

# Install extension methods for testing
install_supervisor_extensions()


class TestSupervisorOrchestration:
    """Test agent coordination and workflow orchestration"""
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
            state.optimizations_result = DeepAgentState(
                optimization_type="parallel_test",
                recommendations=["Parallel optimization complete"]
            ).__dict__
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
        if triage_result.state.triage_result.get("requires_data"):
            data_result = await supervisor._route_to_agent(triage_result.state, context, "data")
            assert data_result.success
            current_state = data_result.state
        else:
            current_state = triage_result.state
        
        # Branch 2: If requires specialized optimization, use specialized path
        if triage_result.state.triage_result.get("requires_specialized_optimization"):
            opt_result = await supervisor._route_to_agent(current_state, context, "optimization")
            assert opt_result.success
            assert opt_result.state.optimizations_result["optimization_type"] == "specialized"
    async def test_state_accumulation_across_agents(self):
        """Test that state accumulates properly across multiple agents"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Each agent adds to the state
        triage_agent = supervisor.agents["triage"]
        triage_agent.execute = AsyncMock()
        triage_agent.execute.return_value = create_agent_state("State test",
                                                             triage_result={"step": 1, "agent": "triage"})
        
        data_agent = supervisor.agents["data"]
        data_agent.execute = AsyncMock()
        
        def mock_data_execute(state, run_id, stream_updates=True):
            # Preserve existing state and add new data
            result_state = DeepAgentState(
                user_request=state.user_request,
                triage_result=state.triage_result,  # Preserve from triage
                data_result={"step": 2, "agent": "data", "previous_steps": [1]}
            )
            return result_state
        
        data_agent.execute.side_effect = mock_data_execute
        
        opt_agent = supervisor.agents["optimization"]
        opt_agent.execute = AsyncMock()
        
        def mock_opt_execute(state, run_id, stream_updates=True):
            result_state = DeepAgentState(
                user_request=state.user_request,
                triage_result=state.triage_result,  # Preserve
                data_result=state.data_result,  # Preserve
                optimizations_result={
                    "optimization_type": "accumulated",
                    "step": 3,
                    "agent": "optimization",
                    "previous_steps": [1, 2]
                }
            )
            return result_state
        
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


class TestWorkflowPatterns:
    """Test common workflow patterns and coordination strategies"""
    async def test_fan_out_fan_in_pattern(self):
        """Test fan-out/fan-in pattern for parallel processing"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        
        # Single triage fans out to multiple parallel processors
        setup_triage_agent_mock(supervisor, {
            'user_request': "Fan out test",
            'triage_result': {"parallel_tasks": ["data_analysis", "optimization", "validation"]}
        })
        
        # Setup parallel processors
        async def mock_data_processor(state, run_id, stream_updates=True):
            await asyncio.sleep(0.02)
            state.data_result = {"processor": "data", "result": "data_processed"}
            return state
        
        async def mock_opt_processor(state, run_id, stream_updates=True):
            await asyncio.sleep(0.03)
            state.optimizations_result = {
                "optimization_type": "processor_test",
                "processor": "optimization",
                "result": "optimizations_processed"
            }
            return state
        
        # Mock a third processor using the data agent for validation
        async def mock_validation_processor(state, run_id, stream_updates=True):
            await asyncio.sleep(0.01)
            # Add validation result to data_result
            if hasattr(state, 'data_result') and state.data_result:
                state.data_result["validation"] = {"processor": "validation", "status": "valid"}
            else:
                state.data_result = {"validation": {"processor": "validation", "status": "valid"}}
            return state
        
        supervisor.agents["data"].execute = mock_data_processor
        supervisor.agents["optimization"].execute = mock_opt_processor
        
        # Create a third mock agent for validation
        validation_agent = AsyncMock()
        validation_agent.execute = mock_validation_processor
        supervisor.agents["validation"] = validation_agent
        
        state = create_agent_state("Fan out test")
        context = create_execution_context("fanout-test")
        
        # Phase 1: Triage (fan-out trigger)
        triage_result = await supervisor._route_to_agent(state, context, "triage")
        assert triage_result.success
        
        # Phase 2: Fan-out to parallel processors
        parallel_tasks = [
            supervisor._route_to_agent(triage_result.state, context, "data"),
            supervisor._route_to_agent(triage_result.state, context, "optimization"),
            supervisor._route_to_agent(triage_result.state, context, "validation")
        ]
        
        parallel_results = await asyncio.gather(*parallel_tasks)
        
        # Phase 3: Fan-in - combine results
        assert all(result.success for result in parallel_results)
        
        # Verify each processor completed its work
        data_result = next(r for r in parallel_results if hasattr(r.state, 'data_result') 
                          and r.state.data_result.get("processor") == "data")
        opt_result = next(r for r in parallel_results if hasattr(r.state, 'optimizations_result'))
        validation_result = next(r for r in parallel_results 
                               if hasattr(r.state, 'data_result') 
                               and r.state.data_result.get("validation"))
        
        assert data_result.state.data_result["result"] == "data_processed"
        assert opt_result.state.optimizations_result["result"] == "optimizations_processed"
        assert validation_result.state.data_result["validation"]["status"] == "valid"
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