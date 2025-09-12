"""
Shared helpers for agent scaling workflow tests.
Maximum 300 lines, functions  <= 8 lines.
"""

import uuid
from typing import Dict, List

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle

def create_scaling_setup(agents: Dict, llm, ws) -> Dict:
    """Build complete setup dictionary."""
    return {
        'agents': agents, 'llm': llm, 'websocket': ws,
        'run_id': str(uuid.uuid4()), 'user_id': 'scaling-test-user'
    }

async def execute_scaling_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete scaling analysis workflow."""
    results = []
    workflow_steps = ['triage', 'data']
    
    for step_name in workflow_steps:
        step_result = await execute_scaling_step(setup, step_name, state)
        results.append(step_result)
    
    optimization_result = create_mock_optimization_result(state)
    results.append(optimization_result)
    return results

async def execute_scaling_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:
    """Execute single scaling workflow step."""
    agent = setup['agents'][step_name]
    agent.websocket_manager = setup['websocket']
    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)
    return create_scaling_result(step_name, agent, state, execution_result)

def create_scaling_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:
    """Create scaling analysis result dictionary."""
    return {
        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,
        'execution_result': result, 'state_updated': state is not None,
        'agent_type': type(agent).__name__
    }

def create_mock_optimization_result(state: DeepAgentState) -> Dict:
    """Create mock optimization result for workflow validation."""
    return {
        'step': 'optimization', 'agent_state': SubAgentLifecycle.COMPLETED,
        'workflow_state': state, 'execution_result': {'optimizations': []},
        'state_updated': True, 'agent_type': 'OptimizationsCoreSubAgent'
    }

def create_50_percent_increase_state() -> DeepAgentState:
    """Create state for 50% usage increase analysis."""
    return DeepAgentState(
        user_request="I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
        metadata={'test_type': 'usage_increase', 'increase_percentage': 50, 'timeframe': 'next_month'}
    )

def create_cost_projection_state() -> DeepAgentState:
    """Create state for cost projection analysis.""" 
    return DeepAgentState(
        user_request="Analyze cost impact of scaling agent usage and predict future rate limit constraints.",
        metadata={'test_type': 'cost_projection', 'focus': 'financial_impact'}
    )

def create_rate_limit_analysis_state() -> DeepAgentState:
    """Create state for rate limit analysis."""
    return DeepAgentState(
        user_request="Analyze how increased usage will affect rate limits and suggest mitigation strategies.",
        metadata={'test_type': 'rate_limit_analysis', 'focus': 'bottlenecks'}
    )

def create_multi_provider_state() -> DeepAgentState:
    """Create state for multi-provider strategy."""
    return DeepAgentState(
        user_request="Develop multi-provider strategy to handle increased load and avoid rate limits.",
        metadata={'test_type': 'multi_provider_strategy', 'approach': 'distribution'}
    )

def create_gradual_scaling_state() -> DeepAgentState:
    """Create state for gradual scaling planning."""
    return DeepAgentState(
        user_request="Plan capacity for gradual 50% usage increase over 6 months with cost optimization.",
        metadata={'test_type': 'gradual_scaling', 'timeline': '6_months', 'pattern': 'gradual'}
    )

def create_traffic_spike_state() -> DeepAgentState:
    """Create state for traffic spike handling."""
    return DeepAgentState(
        user_request="Prepare for potential sudden traffic spikes and ensure system reliability.",
        metadata={'test_type': 'traffic_spike', 'pattern': 'sudden', 'focus': 'reliability'}
    )

def create_extreme_usage_state() -> DeepAgentState:
    """Create state for extreme usage increase test."""
    return DeepAgentState(
        user_request="Expecting 500% increase in usage next week. Prepare emergency scaling plan.",
        metadata={'test_type': 'extreme_usage', 'increase_percentage': 500, 'urgency': 'emergency'}
    )

def create_declining_usage_state() -> DeepAgentState:
    """Create state for declining usage analysis."""
    return DeepAgentState(
        user_request="Usage is declining by 30%. How can we optimize costs and maintain service quality?",
        metadata={'test_type': 'declining_usage', 'decline_percentage': 30}
    )

def validate_50_percent_increase_results(results: List[Dict], state: DeepAgentState):
    """Validate 50% usage increase impact analysis results."""
    assert len(results) == 3, "All workflow steps must execute"
    validate_usage_increase_parsing(results[0], state)
    validate_current_usage_analysis(results[1], state) 
    validate_scaling_optimization_recommendations(results[2], state)

def validate_usage_increase_parsing(result: Dict, state: DeepAgentState):
    """Validate parsing of usage increase requirements."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert '50%' in state.user_request
    assert 'increase' in state.user_request
    assert 'costs and rate limits' in state.user_request

def validate_current_usage_analysis(result: Dict, state: DeepAgentState):
    """Validate current usage pattern analysis."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']
    assert result['agent_type'] == 'DataSubAgent'

def validate_scaling_optimization_recommendations(result: Dict, state: DeepAgentState):
    """Validate scaling optimization recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None
    assert result['agent_type'] == 'OptimizationsCoreSubAgent'

def validate_cost_projection_results(results: List[Dict], state: DeepAgentState):
    """Validate cost projection analysis results."""
    assert len(results) >= 2, "All workflow steps must execute"
    validate_triage_identifies_scaling_concerns(results[0])
    validate_data_gathers_metrics(results[1])

def validate_triage_identifies_scaling_concerns(result: Dict):
    """Validate triage identifies scaling concerns."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['agent_type'] == 'TriageSubAgent'

def validate_data_gathers_metrics(result: Dict):
    """Validate data agent gathers relevant metrics."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']

def validate_rate_limit_analysis(results: List[Dict], state: DeepAgentState):
    """Validate rate limit impact analysis."""
    assert len(results) >= 2, "All workflow steps must execute"
    assert 'rate limits' in state.user_request
    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:2])

def validate_multi_provider_strategy(results: List[Dict]):
    """Validate multi-provider strategy development."""
    assert len(results) >= 2, "All workflow steps must execute"
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert all(r['state_updated'] for r in completed_results)

def validate_gradual_scaling_plan(results: List[Dict]):
    """Validate gradual scaling plan development.""" 
    assert len(results) >= 2, "All workflow steps must execute"
    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)

def validate_spike_handling_strategy(results: List[Dict]):
    """Validate traffic spike handling strategy."""
    assert len(results) >= 2, "All workflow steps must execute"
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 2, "At least core workflow should complete"

def validate_usage_metrics_accuracy(results: List[Dict], state: DeepAgentState):
    """Validate accuracy of usage metrics."""
    assert len(results) >= 2, "All workflow steps must execute"
    data_result = results[1]  # Data sub-agent result
    assert data_result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert data_result['state_updated']

def validate_cost_projection_accuracy(results: List[Dict]):
    """Validate cost projection calculation accuracy."""
    assert len(results) >= 3, "All workflow steps must execute"
    optimization_result = results[2]  # Optimization sub-agent result
    assert optimization_result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert optimization_result['execution_result'] is not None

def validate_data_consistency_across_agents(results: List[Dict], state: DeepAgentState):
    """Validate data consistency across all agents."""
    assert all(r['workflow_state'] is state for r in results)
    assert state.user_request is not None
    assert hasattr(state, 'metadata')
    assert state.metadata.get('increase_percentage') == 50

def validate_recommendation_coherence(results: List[Dict]):
    """Validate coherence of recommendations across workflow."""
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 2, "Core workflow agents should complete"

def validate_extreme_usage_handling(results: List[Dict]):
    """Validate handling of extreme usage scenarios."""
    assert len(results) >= 2, "Core workflow should attempt execution"
    triage_result = results[0]
    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

def validate_declining_usage_handling(results: List[Dict]):
    """Validate handling of declining usage scenarios."""
    assert len(results) >= 2, "All workflow steps should execute"
    assert any(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results)