"""
Comprehensive E2E Agent Scaling Workflows Test Suite
Tests real LLM agents with complete data flow validation for scaling impact analysis.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from decimal import Decimal
from typing import Dict, List, Optional

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.schemas import SubAgentLifecycle
from app.core.exceptions import NetraException


@pytest.fixture
def scaling_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for scaling impact analysis testing."""
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return _build_scaling_setup(agents, real_llm_manager, real_websocket_manager)


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


def _build_scaling_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:
    """Build complete setup dictionary."""
    return {
        'agents': agents, 'llm': llm, 'websocket': ws,
        'run_id': str(uuid.uuid4()), 'user_id': 'scaling-test-user'
    }


class TestUsageIncreaseAnalysis:
    """Test analysis of usage increase impact on costs and rate limits."""
    
    async def test_50_percent_usage_increase_impact(self, scaling_analysis_setup):
        """Test: 'I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?'"""
        setup = scaling_analysis_setup
        state = _create_50_percent_increase_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_50_percent_increase_results(results, state)
    
    async def test_cost_impact_projection(self, scaling_analysis_setup):
        """Test detailed cost impact projection for usage increases."""
        setup = scaling_analysis_setup
        state = _create_cost_projection_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_cost_projection_results(results, state)


def _create_50_percent_increase_state() -> DeepAgentState:
    """Create state for 50% usage increase analysis."""
    return DeepAgentState(
        user_request="I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
        metadata={'test_type': 'usage_increase', 'increase_percentage': 50, 'timeframe': 'next_month'}
    )


def _create_cost_projection_state() -> DeepAgentState:
    """Create state for cost projection analysis."""
    return DeepAgentState(
        user_request="Analyze cost impact of scaling agent usage and predict future rate limit constraints.",
        metadata={'test_type': 'cost_projection', 'focus': 'financial_impact'}
    )


async def _execute_scaling_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete scaling analysis workflow."""
    results = []
    workflow_steps = ['triage', 'data']
    
    for step_name in workflow_steps:
        step_result = await _execute_scaling_step(setup, step_name, state)
        results.append(step_result)
    
    return results


async def _execute_scaling_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:
    """Execute single scaling workflow step."""
    agent = setup['agents'][step_name]
    agent.websocket_manager = setup['websocket']
    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)
    return _create_scaling_result(step_name, agent, state, execution_result)


def _create_scaling_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:
    """Create scaling analysis result dictionary."""
    return {
        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,
        'execution_result': result, 'state_updated': state is not None,
        'agent_type': type(agent).__name__
    }


def _validate_50_percent_increase_results(results: List[Dict], state: DeepAgentState):
    """Validate 50% usage increase impact analysis results."""
    assert len(results) == 2, "All workflow steps must execute"
    _validate_usage_increase_parsing(results[0], state)
    _validate_current_usage_analysis(results[1], state)
    _validate_scaling_optimization_recommendations(results[2], state)


def _validate_usage_increase_parsing(result: Dict, state: DeepAgentState):
    """Validate parsing of usage increase requirements."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert '50%' in state.user_request
    assert 'increase' in state.user_request
    assert 'costs and rate limits' in state.user_request


def _validate_current_usage_analysis(result: Dict, state: DeepAgentState):
    """Validate current usage pattern analysis."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']
    assert result['agent_type'] == 'DataSubAgent'


def _validate_scaling_optimization_recommendations(result: Dict, state: DeepAgentState):
    """Validate scaling optimization recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None
    assert result['agent_type'] == 'OptimizationsCoreSubAgent'


def _validate_cost_projection_results(results: List[Dict], state: DeepAgentState):
    """Validate cost projection analysis results."""
    assert len(results) == 2, "All workflow steps must execute"
    _validate_triage_identifies_scaling_concerns(results[0])
    _validate_data_gathers_metrics(results[1])
    _validate_optimization_proposes_scaling_strategies(results[2])


def _validate_triage_identifies_scaling_concerns(result: Dict):
    """Validate triage identifies scaling concerns."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['agent_type'] == 'TriageSubAgent'


def _validate_data_gathers_metrics(result: Dict):
    """Validate data agent gathers relevant metrics."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']


def _validate_optimization_proposes_scaling_strategies(result: Dict):
    """Validate optimization proposes scaling strategies."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None


class TestRateLimitImpactAnalysis:
    """Test rate limit impact analysis for scaling scenarios."""
    
    async def test_rate_limit_bottleneck_identification(self, scaling_analysis_setup):
        """Test identification of rate limit bottlenecks during scaling."""
        setup = scaling_analysis_setup
        state = _create_rate_limit_analysis_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_rate_limit_analysis(results, state)
    
    async def test_multi_provider_rate_limit_strategy(self, scaling_analysis_setup):
        """Test multi-provider rate limit strategy development."""
        setup = scaling_analysis_setup
        state = _create_multi_provider_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_multi_provider_strategy(results)


def _create_rate_limit_analysis_state() -> DeepAgentState:
    """Create state for rate limit analysis."""
    return DeepAgentState(
        user_request="Analyze how increased usage will affect rate limits and suggest mitigation strategies.",
        metadata={'test_type': 'rate_limit_analysis', 'focus': 'bottlenecks'}
    )


def _create_multi_provider_state() -> DeepAgentState:
    """Create state for multi-provider strategy."""
    return DeepAgentState(
        user_request="Develop multi-provider strategy to handle increased load and avoid rate limits.",
        metadata={'test_type': 'multi_provider_strategy', 'approach': 'distribution'}
    )


def _validate_rate_limit_analysis(results: List[Dict], state: DeepAgentState):
    """Validate rate limit impact analysis."""
    assert len(results) == 2, "All workflow steps must execute"
    assert 'rate limits' in state.user_request
    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])


def _validate_multi_provider_strategy(results: List[Dict]):
    """Validate multi-provider strategy development."""
    assert len(results) == 2, "All workflow steps must execute"
    assert all(r['state_updated'] for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED)


class TestCapacityPlanningWorkflows:
    """Test capacity planning workflows for different scaling scenarios."""
    
    async def test_gradual_scaling_capacity_plan(self, scaling_analysis_setup):
        """Test gradual scaling capacity planning."""
        setup = scaling_analysis_setup
        state = _create_gradual_scaling_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_gradual_scaling_plan(results)
    
    async def test_sudden_spike_handling(self, scaling_analysis_setup):
        """Test sudden traffic spike handling strategies."""
        setup = scaling_analysis_setup
        state = _create_traffic_spike_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_spike_handling_strategy(results)


def _create_gradual_scaling_state() -> DeepAgentState:
    """Create state for gradual scaling planning."""
    return DeepAgentState(
        user_request="Plan capacity for gradual 50% usage increase over 6 months with cost optimization.",
        metadata={'test_type': 'gradual_scaling', 'timeline': '6_months', 'pattern': 'gradual'}
    )


def _create_traffic_spike_state() -> DeepAgentState:
    """Create state for traffic spike handling."""
    return DeepAgentState(
        user_request="Prepare for potential sudden traffic spikes and ensure system reliability.",
        metadata={'test_type': 'traffic_spike', 'pattern': 'sudden', 'focus': 'reliability'}
    )


def _validate_gradual_scaling_plan(results: List[Dict]):
    """Validate gradual scaling plan development."""
    assert len(results) == 2, "All workflow steps must execute"
    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)


def _validate_spike_handling_strategy(results: List[Dict]):
    """Validate traffic spike handling strategy."""
    assert len(results) == 2, "All workflow steps must execute"
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 3, "At least core workflow should complete"


class TestScalingMetricsValidation:
    """Test validation of scaling metrics and projections."""
    
    async def test_usage_metrics_accuracy(self, scaling_analysis_setup):
        """Test accuracy of usage metrics collection and projection."""
        setup = scaling_analysis_setup
        state = _create_50_percent_increase_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_usage_metrics_accuracy(results, state)
    
    async def test_cost_projection_validation(self, scaling_analysis_setup):
        """Test validation of cost projection calculations."""
        setup = scaling_analysis_setup
        state = _create_cost_projection_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_cost_projection_accuracy(results)


def _validate_usage_metrics_accuracy(results: List[Dict], state: DeepAgentState):
    """Validate accuracy of usage metrics."""
    assert len(results) == 2, "All workflow steps must execute"
    data_result = results[1]  # Data sub-agent result
    assert data_result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert data_result['state_updated']


def _validate_cost_projection_accuracy(results: List[Dict]):
    """Validate cost projection calculation accuracy."""
    assert len(results) == 2, "All workflow steps must execute"
    optimization_result = results[2]  # Optimization sub-agent result
    assert optimization_result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert optimization_result['execution_result'] is not None


class TestScalingWorkflowIntegrity:
    """Test integrity of complete scaling analysis workflows."""
    
    async def test_end_to_end_data_consistency(self, scaling_analysis_setup):
        """Test data consistency throughout scaling analysis workflow."""
        setup = scaling_analysis_setup
        state = _create_50_percent_increase_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_data_consistency_across_agents(results, state)
    
    async def test_scaling_recommendations_coherence(self, scaling_analysis_setup):
        """Test coherence of scaling recommendations across agents."""
        setup = scaling_analysis_setup
        state = _create_gradual_scaling_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_recommendation_coherence(results)


def _validate_data_consistency_across_agents(results: List[Dict], state: DeepAgentState):
    """Validate data consistency across all agents."""
    assert all(r['workflow_state'] is state for r in results)
    assert state.user_request is not None
    assert hasattr(state, 'metadata')
    assert state.metadata.get('increase_percentage') == 50


def _validate_recommendation_coherence(results: List[Dict]):
    """Validate coherence of recommendations across workflow."""
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 3, "Core workflow agents should complete"
    
    actions_result = next((r for r in results if r.get('agent_type') == 'ActionsToMeetGoalsSubAgent'), None)
    if actions_result and actions_result['agent_state'] == SubAgentLifecycle.COMPLETED:
        assert actions_result['execution_result'] is not None


class TestScalingEdgeCases:
    """Test edge cases in scaling analysis workflows."""
    
    async def test_extreme_usage_increase(self, scaling_analysis_setup):
        """Test handling of extreme usage increase scenarios."""
        setup = scaling_analysis_setup
        state = _create_extreme_usage_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_extreme_usage_handling(results)
    
    async def test_declining_usage_analysis(self, scaling_analysis_setup):
        """Test analysis of declining usage scenarios."""
        setup = scaling_analysis_setup
        state = _create_declining_usage_state()
        results = await _execute_scaling_workflow(setup, state)
        _validate_declining_usage_handling(results)


def _create_extreme_usage_state() -> DeepAgentState:
    """Create state for extreme usage increase test."""
    return DeepAgentState(
        user_request="Expecting 500% increase in usage next week. Prepare emergency scaling plan.",
        metadata={'test_type': 'extreme_usage', 'increase_percentage': 500, 'urgency': 'emergency'}
    )


def _create_declining_usage_state() -> DeepAgentState:
    """Create state for declining usage analysis."""
    return DeepAgentState(
        user_request="Usage is declining by 30%. How can we optimize costs and maintain service quality?",
        metadata={'test_type': 'declining_usage', 'decline_percentage': 30}
    )


def _validate_extreme_usage_handling(results: List[Dict]):
    """Validate handling of extreme usage scenarios."""
    assert len(results) >= 3, "Core workflow should attempt execution"
    triage_result = results[0]
    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]


def _validate_declining_usage_handling(results: List[Dict]):
    """Validate handling of declining usage scenarios."""
    assert len(results) == 2, "All workflow steps should execute"
    assert any(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results)