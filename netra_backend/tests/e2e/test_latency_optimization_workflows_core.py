"""
Core Latency Optimization Workflows Test Suite
Tests real LLM agents with complete data flow validation for latency optimization.
Maximum 300 lines, functions ≤8 lines.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import time

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
)
from netra_backend.tests.latency_optimization_helpers import (
    create_3x_latency_state,
    create_bottleneck_analysis_state,
    create_caching_optimization_state,
    create_latency_optimization_setup,
    create_parallel_processing_state,
    execute_latency_workflow,
    validate_3x_latency_results,
    validate_bottleneck_identification,
    validate_caching_strategy_results,
    validate_execution_time_bounds,
    validate_parallel_processing_results,
    validate_timing_consistency,
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

@pytest.mark.real_llm
class TestExamplePromptsPerformanceOptimization:
    """Test specific example prompts EP-002 and EP-004 with real LLM validation."""
    
    async def test_ep_002_latency_budget_constraint_real_llm(self, latency_optimization_setup):
        """Test EP-002: Latency optimization with budget constraints using real LLM."""
        setup = latency_optimization_setup
        state = _create_ep_002_state()
        results = await execute_latency_workflow(setup, state)
        await _validate_ep_002_results(results, state, setup)
    
    async def test_ep_004_function_optimization_real_llm(self, latency_optimization_setup):
        """Test EP-004: Function optimization methods using real LLM."""
        setup = latency_optimization_setup
        state = _create_ep_004_state()
        results = await execute_latency_workflow(setup, state)
        await _validate_ep_004_results(results, state, setup)

def _create_ep_002_state() -> DeepAgentState:
    """Create state for EP-002 example prompt test."""
    return DeepAgentState(
        user_request="My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
        metadata={'test_type': 'ep_002', 'prompt_id': 'EP-002', 'latency_target': '3x', 'budget_constraint': 'zero'}
    )

def _create_ep_004_state() -> DeepAgentState:
    """Create state for EP-004 example prompt test."""
    return DeepAgentState(
        user_request="I need to optimize the 'user_authentication' function. What advanced methods can I use?",
        metadata={'test_type': 'ep_004', 'prompt_id': 'EP-004', 'target_function': 'user_authentication'}
    )

async def _validate_ep_002_results(results, state: DeepAgentState, setup):
    """Validate EP-002 results with enhanced quality checks."""
    await validate_3x_latency_results(results, state)
    await _validate_response_quality_ep_002(results, setup)

async def _validate_ep_004_results(results, state: DeepAgentState, setup):
    """Validate EP-004 results with enhanced quality checks."""
    _validate_function_optimization_results(results, state)
    await _validate_response_quality_ep_004(results, setup)

def _validate_function_optimization_results(results, state: DeepAgentState):
    """Validate function optimization workflow results."""
    assert len(results) > 0, "No results returned from workflow"
    assert 'user_authentication' in state.user_request
    assert any('function' in str(result).lower() for result in results)

async def _validate_response_quality_ep_002(results, setup):
    """Validate response quality for EP-002 using quality gate service."""
    quality_service = QualityGateService()
    final_result = results[-1] if results else None
    
    if final_result and hasattr(final_result, 'get'):
        response_text = _extract_response_text(final_result)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=ContentType.PERFORMANCE_ANALYSIS, quality_level=QualityLevel.MEDIUM
        )
        assert is_valid, f"EP-002 response quality validation failed: {feedback}"
        assert score >= 70, f"EP-002 quality score too low: {score}"

async def _validate_response_quality_ep_004(results, setup):
    """Validate response quality for EP-004 using quality gate service."""
    quality_service = QualityGateService()
    final_result = results[-1] if results else None
    
    if final_result and hasattr(final_result, 'get'):
        response_text = _extract_response_text(final_result)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=ContentType.OPTIMIZATION_REPORT, quality_level=QualityLevel.MEDIUM
        )
        assert is_valid, f"EP-004 response quality validation failed: {feedback}"
        assert score >= 70, f"EP-004 quality score too low: {score}"

def _extract_response_text(result) -> str:
    """Extract response text from workflow result."""
    if isinstance(result, dict):
        return str(result.get('execution_result', result.get('response', str(result))))
    return str(result)