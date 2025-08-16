"""
Core Latency Optimization Workflows Test Suite
Tests real LLM agents with complete data flow validation for latency optimization.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import time

from app.tests.e2e.latency_optimization_helpers import (
    create_latency_optimization_setup, execute_latency_workflow,
    create_3x_latency_state, create_bottleneck_analysis_state,
    create_caching_optimization_state, create_parallel_processing_state,
    validate_3x_latency_results, validate_bottleneck_identification,
    validate_caching_strategy_results, validate_parallel_processing_results,
    validate_execution_time_bounds, validate_timing_consistency
)


@pytest.fixture
def latency_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for latency optimization testing."""
    return create_latency_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher)


class TestLatencyOptimization3x:
    """Test 3x latency reduction without budget increase."""
    
    async def test_3x_latency_reduction_zero_budget(self, latency_optimization_setup):
        """Test: 'My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.'"""
        setup = latency_optimization_setup
        state = create_3x_latency_state()
        results = await execute_latency_workflow(setup, state)
        await validate_3x_latency_results(results, state)
    
    async def test_latency_bottleneck_identification(self, latency_optimization_setup):
        """Test identification of specific latency bottlenecks."""
        setup = latency_optimization_setup
        state = create_bottleneck_analysis_state()
        results = await execute_latency_workflow(setup, state)
        validate_bottleneck_identification(results, state)


class TestLatencyOptimizationStrategies:
    """Test various latency optimization strategies."""
    
    async def test_caching_strategy_optimization(self, latency_optimization_setup):
        """Test optimization focusing on caching strategies."""
        setup = latency_optimization_setup
        state = create_caching_optimization_state()
        results = await execute_latency_workflow(setup, state)
        validate_caching_strategy_results(results)
    
    async def test_parallel_processing_optimization(self, latency_optimization_setup):
        """Test optimization focusing on parallel processing."""
        setup = latency_optimization_setup
        state = create_parallel_processing_state()
        results = await execute_latency_workflow(setup, state)
        validate_parallel_processing_results(results)


class TestWorkflowPerformance:
    """Test performance characteristics of latency optimization workflows."""
    
    async def test_workflow_execution_time_bounds(self, latency_optimization_setup):
        """Test that workflow execution stays within reasonable time bounds."""
        setup = latency_optimization_setup
        state = create_3x_latency_state()
        
        start_time = time.time()
        results = await execute_latency_workflow(setup, state)
        total_time = time.time() - start_time
        
        validate_execution_time_bounds(results, total_time)
    
    async def test_agent_step_timing_consistency(self, latency_optimization_setup):
        """Test timing consistency across agent steps."""
        setup = latency_optimization_setup
        state = create_bottleneck_analysis_state()
        results = await execute_latency_workflow(setup, state)
        validate_timing_consistency(results)