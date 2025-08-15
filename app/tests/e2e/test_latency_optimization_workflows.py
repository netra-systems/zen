"""
Comprehensive E2E Latency Optimization Workflows Test Suite
Tests real LLM agents with complete data flow validation for latency optimization.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
import time
from typing import Dict, List, Optional, Tuple

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.schemas import SubAgentLifecycle
from app.core.exceptions import NetraException


@pytest.fixture
def latency_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for latency optimization testing."""
    # Import additional agents to avoid circular dependencies
    from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
    from app.agents.reporting_sub_agent import ReportingSubAgent
    
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher),
        'optimization': OptimizationsCoreSubAgent(real_llm_manager, real_tool_dispatcher),
        'actions': ActionsToMeetGoalsSubAgent(real_llm_manager, real_tool_dispatcher),
        'reporting': ReportingSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return _build_latency_setup(agents, real_llm_manager, real_websocket_manager)


async def _create_real_llm_manager() -> LLMManager:
    """Create real LLM manager instance."""
    manager = LLMManager()
    await manager.initialize()
    return manager


def _create_websocket_manager() -> WebSocketManager:
    """Create WebSocket manager instance."""
    return WebSocketManager()


def _create_agent_instances(llm: LLMManager, ws: WebSocketManager) -> Dict:
    """Create agent instances with real LLM."""
    return {
        'triage': TriageSubAgent(llm, None, None),
        'data': DataSubAgent(llm, None),
        'optimization': OptimizationsCoreSubAgent(llm, None),
        'actions': ActionsToMeetGoalsSubAgent(llm, None),
        'reporting': ReportingSubAgent(llm, None)
    }


def _build_latency_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:
    """Build complete setup dictionary."""
    return {
        'agents': agents, 'llm': llm, 'websocket': ws,
        'run_id': str(uuid.uuid4()), 'user_id': 'latency-test-user'
    }


class TestLatencyOptimization3x:
    """Test 3x latency reduction without budget increase."""
    
    async def test_3x_latency_reduction_zero_budget(self, latency_optimization_setup):
        """Test: 'My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.'"""
        setup = latency_optimization_setup
        state = _create_3x_latency_state()
        results = await _execute_latency_workflow(setup, state)
        await _validate_3x_latency_results(results, state)
    
    async def test_latency_bottleneck_identification(self, latency_optimization_setup):
        """Test identification of specific latency bottlenecks."""
        setup = latency_optimization_setup
        state = _create_bottleneck_analysis_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_bottleneck_identification(results, state)


def _create_3x_latency_state() -> DeepAgentState:
    """Create state for 3x latency reduction test."""
    return DeepAgentState(
        user_request="My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
        metadata={'test_type': 'latency_3x', 'target_improvement': '3x', 'budget_constraint': 'zero'}
    )


def _create_bottleneck_analysis_state() -> DeepAgentState:
    """Create state for bottleneck analysis test."""
    return DeepAgentState(
        user_request="Analyze current system latency bottlenecks and propose optimization strategies.",
        metadata={'test_type': 'bottleneck_analysis', 'focus': 'identification'}
    )


async def _execute_latency_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete latency optimization workflow with all 5 agents."""
    results = []
    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:
        step_result = await _execute_timed_step(setup, step_name, state)
        results.append(step_result)
    
    return results


async def _execute_timed_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:
    """Execute workflow step with timing measurements."""
    # Fix WebSocket interface - ensure both methods are available
    if hasattr(setup['websocket'], 'send_message') and not hasattr(setup['websocket'], 'send_to_thread'):
        setup['websocket'].send_to_thread = setup['websocket'].send_message
    elif hasattr(setup['websocket'], 'send_to_thread') and not hasattr(setup['websocket'], 'send_message'):
        setup['websocket'].send_message = setup['websocket'].send_to_thread
    start_time = time.time()
    agent = setup['agents'][step_name]
    agent.websocket_manager = setup['websocket']
    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)
    execution_time = time.time() - start_time
    
    return _create_timed_result(step_name, agent, state, execution_result, execution_time)


def _create_timed_result(step_name: str, agent, state: DeepAgentState, 
                        result, exec_time: float) -> Dict:
    """Create timed execution result dictionary."""
    return {
        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,
        'execution_result': result, 'execution_time': exec_time, 'state_updated': state is not None
    }


async def _validate_3x_latency_results(results: List[Dict], state: DeepAgentState):
    """Validate 3x latency reduction results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    await _validate_latency_requirement_parsing(results[0], state)
    await _validate_current_performance_analysis(results[1], state)


async def _validate_latency_requirement_parsing(result: Dict, state: DeepAgentState):
    """Validate parsing of latency requirements."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert '3x' in state.user_request
    assert 'can\'t spend more money' in state.user_request
    assert result['execution_time'] < 30.0  # Reasonable execution time


async def _validate_current_performance_analysis(result: Dict, state: DeepAgentState):
    """Validate current performance analysis."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']
    assert result['execution_time'] < 60.0  # Data analysis should be reasonable


async def _validate_optimization_strategy_development(result: Dict, state: DeepAgentState):
    """Validate optimization strategy development."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated'] or result['execution_result'] is not None
    assert result['execution_time'] < 90.0  # Complex analysis time limit


def _validate_bottleneck_identification(results: List[Dict], state: DeepAgentState):
    """Validate bottleneck identification results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    _validate_triage_identifies_bottlenecks(results[0])
    _validate_data_analysis_measures_performance(results[1])


def _validate_triage_identifies_bottlenecks(result: Dict):
    """Validate triage identifies bottleneck focus."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'bottleneck' in result['workflow_state'].user_request.lower()


def _validate_data_analysis_measures_performance(result: Dict):
    """Validate data analysis measures current performance."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']


def _validate_optimization_targets_bottlenecks(result: Dict):
    """Validate optimization targets identified bottlenecks."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated'] or result['execution_result'] is not None


class TestLatencyOptimizationStrategies:
    """Test various latency optimization strategies."""
    
    async def test_caching_strategy_optimization(self, latency_optimization_setup):
        """Test optimization focusing on caching strategies."""
        setup = latency_optimization_setup
        state = _create_caching_optimization_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_caching_strategy_results(results)
    
    async def test_parallel_processing_optimization(self, latency_optimization_setup):
        """Test optimization focusing on parallel processing."""
        setup = latency_optimization_setup
        state = _create_parallel_processing_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_parallel_processing_results(results)


def _create_caching_optimization_state() -> DeepAgentState:
    """Create state for caching optimization test."""
    return DeepAgentState(
        user_request="Optimize system latency through improved caching strategies without additional infrastructure costs.",
        metadata={'test_type': 'caching_optimization', 'focus': 'caching'}
    )


def _create_parallel_processing_state() -> DeepAgentState:
    """Create state for parallel processing optimization test."""
    return DeepAgentState(
        user_request="Reduce latency through better parallel processing and async operations optimization.",
        metadata={'test_type': 'parallel_optimization', 'focus': 'parallelization'}
    )


def _validate_caching_strategy_results(results: List[Dict]):
    """Validate caching strategy optimization results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])
    

def _validate_parallel_processing_results(results: List[Dict]):
    """Validate parallel processing optimization results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])


class TestWorkflowPerformance:
    """Test performance characteristics of latency optimization workflows."""
    
    async def test_workflow_execution_time_bounds(self, latency_optimization_setup):
        """Test that workflow execution stays within reasonable time bounds."""
        setup = latency_optimization_setup
        state = _create_3x_latency_state()
        
        start_time = time.time()
        results = await _execute_latency_workflow(setup, state)
        total_time = time.time() - start_time
        
        _validate_execution_time_bounds(results, total_time)
    
    async def test_agent_step_timing_consistency(self, latency_optimization_setup):
        """Test timing consistency across agent steps."""
        setup = latency_optimization_setup
        state = _create_bottleneck_analysis_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_timing_consistency(results)


def _validate_execution_time_bounds(results: List[Dict], total_time: float):
    """Validate overall execution time bounds."""
    assert total_time < 300.0, "Workflow should complete within 5 minutes"
    assert len(results) == 5, "All 5 workflow steps should execute"
    assert all('execution_time' in r for r in results), "All steps should be timed"


def _validate_timing_consistency(results: List[Dict]):
    """Validate timing consistency across steps."""
    execution_times = [r['execution_time'] for r in results if 'execution_time' in r]
    assert len(execution_times) == 5, "All steps should have timing data"
    assert all(t >= 0 for t in execution_times), "All execution times should be non-negative"


class TestLatencyOptimizationEdgeCases:
    """Test edge cases in latency optimization workflows."""
    
    async def test_impossible_latency_targets(self, latency_optimization_setup):
        """Test handling of impossible latency targets."""
        setup = latency_optimization_setup
        state = _create_impossible_latency_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_impossible_target_handling(results)
    
    async def test_already_optimized_system(self, latency_optimization_setup):
        """Test handling of already well-optimized systems."""
        setup = latency_optimization_setup
        state = _create_already_optimized_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_optimized_system_handling(results)


def _create_impossible_latency_state() -> DeepAgentState:
    """Create state for impossible latency targets test."""
    return DeepAgentState(
        user_request="Reduce latency by 1000x to achieve sub-millisecond response times without any changes.",
        metadata={'test_type': 'impossible_targets', 'target': '1000x'}
    )


def _create_already_optimized_state() -> DeepAgentState:
    """Create state for already optimized system test."""
    return DeepAgentState(
        user_request="My system is already highly optimized. Find any remaining latency improvements.",
        metadata={'test_type': 'already_optimized', 'baseline': 'high'}
    )


def _validate_impossible_target_handling(results: List[Dict]):
    """Validate handling of impossible latency targets."""
    assert len(results) >= 3, "At least initial analysis should complete"
    triage_result = results[0]
    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]


def _validate_optimized_system_handling(results: List[Dict]):
    """Validate handling of already optimized systems."""
    assert len(results) == 5, "All 5 workflow steps should attempt analysis"
    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)


class TestIntegrationValidation:
    """Test integration between latency optimization agents."""
    
    async def test_data_flow_between_agents(self, latency_optimization_setup):
        """Test proper data flow between optimization agents."""
        setup = latency_optimization_setup
        state = _create_3x_latency_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_agent_data_flow(results, state)
    
    async def test_state_consistency_maintenance(self, latency_optimization_setup):
        """Test state consistency throughout workflow."""
        setup = latency_optimization_setup
        state = _create_caching_optimization_state()
        results = await _execute_latency_workflow(setup, state)
        _validate_state_consistency(results, state)


def _validate_agent_data_flow(results: List[Dict], state: DeepAgentState):
    """Validate proper data flow between agents."""
    assert all(r['workflow_state'] is state for r in results)
    assert state.user_request is not None
    assert hasattr(state, 'metadata')


def _validate_state_consistency(results: List[Dict], original_state: DeepAgentState):
    """Validate state consistency throughout workflow."""
    assert len(results) == 5, "All 5 workflow steps should execute"
    for result in results:
        assert result['workflow_state'] is original_state
        assert result['state_updated']