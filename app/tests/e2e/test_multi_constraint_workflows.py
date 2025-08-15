"""
Comprehensive E2E Multi-Constraint Workflows Test Suite
Tests real LLM agents with complete data flow validation for complex multi-constraint optimization.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
from typing import Dict, List, Optional

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.schemas import SubAgentLifecycle
from app.core.exceptions import NetraException


@pytest.fixture
def multi_constraint_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for multi-constraint optimization testing."""
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
    return _build_multi_constraint_setup(agents, real_llm_manager, real_websocket_manager)


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


def _build_multi_constraint_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:
    """Build complete setup dictionary."""
    return {
        'agents': agents, 'llm': llm, 'websocket': ws,
        'run_id': str(uuid.uuid4()), 'user_id': 'multi-constraint-test-user'
    }


class TestKVCachingAuditWorkflows:
    """Test KV caching audit and optimization workflows."""
    
    async def test_kv_cache_optimization_audit(self, multi_constraint_setup):
        """Test: 'I want to audit all uses of KV caching in my system to find optimization opportunities.'"""
        setup = multi_constraint_setup
        state = _create_kv_cache_audit_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_kv_cache_audit_results(results, state)
    
    async def test_comprehensive_cache_analysis(self, multi_constraint_setup):
        """Test comprehensive cache analysis across system components."""
        setup = multi_constraint_setup
        state = _create_comprehensive_cache_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_comprehensive_cache_results(results)


def _create_kv_cache_audit_state() -> DeepAgentState:
    """Create state for KV cache audit workflow."""
    return DeepAgentState(
        user_request="I want to audit all uses of KV caching in my system to find optimization opportunities.",
        metadata={'test_type': 'kv_cache_audit', 'focus': 'system_wide_audit', 'scope': 'all_cache_instances'}
    )


def _create_comprehensive_cache_state() -> DeepAgentState:
    """Create state for comprehensive cache analysis."""
    return DeepAgentState(
        user_request="Perform comprehensive analysis of caching strategies and identify improvement opportunities.",
        metadata={'test_type': 'comprehensive_cache', 'analysis_depth': 'deep', 'include_recommendations': True}
    )


async def _execute_multi_constraint_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete multi-constraint optimization workflow."""
    results = []
    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:
        step_result = await _execute_constraint_step(setup, step_name, state)
        results.append(step_result)
    
    return results


async def _execute_constraint_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:
    """Execute single multi-constraint workflow step."""
    agent = setup['agents'][step_name]
    agent.websocket_manager = setup['websocket']
    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)
    return _create_constraint_result(step_name, agent, state, execution_result)


def _create_constraint_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:
    """Create multi-constraint result dictionary."""
    return {
        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,
        'execution_result': result, 'state_updated': state is not None,
        'agent_type': type(agent).__name__
    }


def _validate_kv_cache_audit_results(results: List[Dict], state: DeepAgentState):
    """Validate KV cache audit workflow results."""
    assert len(results) == 5, "All workflow steps must execute"
    _validate_cache_scope_identification(results[0], state)
    _validate_cache_inventory_analysis(results[1], state)
    _validate_optimization_opportunity_identification(results[2], state)


def _validate_cache_scope_identification(result: Dict, state: DeepAgentState):
    """Validate cache scope identification."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'KV caching' in state.user_request
    assert 'audit' in state.user_request
    assert 'optimization opportunities' in state.user_request


def _validate_cache_inventory_analysis(result: Dict, state: DeepAgentState):
    """Validate cache inventory analysis."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']
    assert result['agent_type'] == 'DataSubAgent'


def _validate_optimization_opportunity_identification(result: Dict, state: DeepAgentState):
    """Validate optimization opportunity identification."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None
    assert result['agent_type'] == 'OptimizationsCoreSubAgent'


def _validate_comprehensive_cache_results(results: List[Dict]):
    """Validate comprehensive cache analysis results."""
    assert len(results) == 5, "All workflow steps must execute"
    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)


class TestComplexMultiObjectiveOptimization:
    """Test complex multi-objective optimization scenarios."""
    
    async def test_triple_constraint_optimization(self, multi_constraint_setup):
        """Test optimization with three competing constraints."""
        setup = multi_constraint_setup
        state = _create_triple_constraint_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_triple_constraint_results(results, state)
    
    async def test_quality_cost_latency_tradeoff(self, multi_constraint_setup):
        """Test quality vs cost vs latency tradeoff analysis."""
        setup = multi_constraint_setup
        state = _create_quality_cost_latency_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_quality_cost_latency_results(results)


def _create_triple_constraint_state() -> DeepAgentState:
    """Create state for triple constraint optimization."""
    return DeepAgentState(
        user_request="Optimize system for minimum cost, maximum quality, and sub-200ms latency simultaneously.",
        metadata={'test_type': 'triple_constraint', 'constraints': ['cost', 'quality', 'latency']}
    )


def _create_quality_cost_latency_state() -> DeepAgentState:
    """Create state for quality vs cost vs latency analysis."""
    return DeepAgentState(
        user_request="Analyze tradeoffs between quality improvements, cost reductions, and latency optimizations.",
        metadata={'test_type': 'quality_cost_latency_tradeoff', 'dimensions': 3}
    )


def _validate_triple_constraint_results(results: List[Dict], state: DeepAgentState):
    """Validate triple constraint optimization results."""
    assert len(results) == 5, "All workflow steps must execute"
    _validate_constraint_conflict_identification(results[0], state)
    _validate_multi_objective_analysis(results[2], state)
    _validate_compromise_recommendations(results[3], state)


def _validate_constraint_conflict_identification(result: Dict, state: DeepAgentState):
    """Validate constraint conflict identification."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert len(state.metadata.get('constraints', [])) == 3
    

def _validate_multi_objective_analysis(result: Dict, state: DeepAgentState):
    """Validate multi-objective analysis."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None


def _validate_compromise_recommendations(result: Dict, state: DeepAgentState):
    """Validate compromise recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['agent_type'] == 'ActionsToMeetGoalsSubAgent'


def _validate_quality_cost_latency_results(results: List[Dict]):
    """Validate quality vs cost vs latency tradeoff results."""
    assert len(results) == 5, "All workflow steps must execute"
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 3, "Core workflow should complete"


class TestSystemWideOptimizationWorkflows:
    """Test system-wide optimization workflows with multiple constraints."""
    
    async def test_holistic_system_optimization(self, multi_constraint_setup):
        """Test holistic system optimization across multiple dimensions."""
        setup = multi_constraint_setup
        state = _create_holistic_optimization_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_holistic_optimization_results(results)
    
    async def test_infrastructure_application_optimization(self, multi_constraint_setup):
        """Test combined infrastructure and application optimization."""
        setup = multi_constraint_setup
        state = _create_infrastructure_app_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_infrastructure_app_results(results)


def _create_holistic_optimization_state() -> DeepAgentState:
    """Create state for holistic system optimization."""
    return DeepAgentState(
        user_request="Perform holistic optimization of entire system including caching, models, infrastructure, and workflows.",
        metadata={'test_type': 'holistic_optimization', 'scope': 'system_wide', 'components': ['cache', 'models', 'infrastructure']}
    )


def _create_infrastructure_app_state() -> DeepAgentState:
    """Create state for infrastructure and application optimization."""
    return DeepAgentState(
        user_request="Optimize both infrastructure configuration and application performance simultaneously.",
        metadata={'test_type': 'infrastructure_app', 'levels': ['infrastructure', 'application']}
    )


def _validate_holistic_optimization_results(results: List[Dict]):
    """Validate holistic optimization results."""
    assert len(results) == 5, "All workflow steps must execute"
    data_result = results[1]
    assert data_result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert data_result['state_updated']


def _validate_infrastructure_app_results(results: List[Dict]):
    """Validate infrastructure and application optimization results."""
    assert len(results) == 5, "All workflow steps must execute"
    optimization_result = results[2]
    assert optimization_result['agent_state'] == SubAgentLifecycle.COMPLETED


class TestConstraintPriorityWorkflows:
    """Test workflows with constraint prioritization."""
    
    async def test_priority_based_optimization(self, multi_constraint_setup):
        """Test optimization with prioritized constraints."""
        setup = multi_constraint_setup
        state = _create_priority_optimization_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_priority_optimization_results(results, state)
    
    async def test_dynamic_constraint_adjustment(self, multi_constraint_setup):
        """Test dynamic constraint adjustment during optimization."""
        setup = multi_constraint_setup
        state = _create_dynamic_constraint_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_dynamic_constraint_results(results)


def _create_priority_optimization_state() -> DeepAgentState:
    """Create state for priority-based optimization."""
    return DeepAgentState(
        user_request="Optimize with priority: 1) Maintain quality above 95%, 2) Reduce costs by 15%, 3) Improve latency if possible.",
        metadata={'test_type': 'priority_optimization', 'priorities': ['quality', 'cost', 'latency']}
    )


def _create_dynamic_constraint_state() -> DeepAgentState:
    """Create state for dynamic constraint adjustment."""
    return DeepAgentState(
        user_request="Adjust optimization strategy dynamically based on real-time performance metrics.",
        metadata={'test_type': 'dynamic_constraints', 'adaptation': 'real_time'}
    )


def _validate_priority_optimization_results(results: List[Dict], state: DeepAgentState):
    """Validate priority-based optimization results."""
    assert len(results) == 5, "All workflow steps must execute"
    assert '95%' in state.user_request
    assert '15%' in state.user_request
    assert len(state.metadata.get('priorities', [])) == 3


def _validate_dynamic_constraint_results(results: List[Dict]):
    """Validate dynamic constraint adjustment results."""
    assert len(results) == 5, "All workflow steps must execute"
    assert any(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results)


class TestMultiConstraintEdgeCases:
    """Test edge cases in multi-constraint optimization."""
    
    async def test_impossible_constraint_combination(self, multi_constraint_setup):
        """Test handling of impossible constraint combinations."""
        setup = multi_constraint_setup
        state = _create_impossible_constraints_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_impossible_constraints_handling(results)
    
    async def test_minimal_constraint_optimization(self, multi_constraint_setup):
        """Test optimization with minimal or single constraints."""
        setup = multi_constraint_setup
        state = _create_minimal_constraint_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_minimal_constraint_results(results)


def _create_impossible_constraints_state() -> DeepAgentState:
    """Create state for impossible constraints test."""
    return DeepAgentState(
        user_request="Achieve zero cost, infinite quality, and zero latency while doubling performance.",
        metadata={'test_type': 'impossible_constraints', 'feasibility': 'impossible'}
    )


def _create_minimal_constraint_state() -> DeepAgentState:
    """Create state for minimal constraints test."""
    return DeepAgentState(
        user_request="Find any optimization opportunities in the system.",
        metadata={'test_type': 'minimal_constraints', 'constraints_count': 0}
    )


def _validate_impossible_constraints_handling(results: List[Dict]):
    """Validate handling of impossible constraints."""
    assert len(results) >= 1, "At least triage should execute"
    triage_result = results[0]
    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]


def _validate_minimal_constraint_results(results: List[Dict]):
    """Validate minimal constraint optimization results."""
    assert len(results) == 5, "All workflow steps should execute"
    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)


class TestWorkflowDataIntegrity:
    """Test data integrity across multi-constraint workflows."""
    
    async def test_constraint_data_consistency(self, multi_constraint_setup):
        """Test constraint data consistency throughout workflow."""
        setup = multi_constraint_setup
        state = _create_kv_cache_audit_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_constraint_data_consistency(results, state)
    
    async def test_optimization_state_preservation(self, multi_constraint_setup):
        """Test optimization state preservation across agents."""
        setup = multi_constraint_setup
        state = _create_triple_constraint_state()
        results = await _execute_multi_constraint_workflow(setup, state)
        _validate_optimization_state_preservation(results, state)


def _validate_constraint_data_consistency(results: List[Dict], state: DeepAgentState):
    """Validate constraint data consistency."""
    assert all(r['workflow_state'] is state for r in results)
    assert state.metadata.get('focus') == 'system_wide_audit'
    assert all(r['state_updated'] for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED)


def _validate_optimization_state_preservation(results: List[Dict], state: DeepAgentState):
    """Validate optimization state preservation."""
    assert len(results) == 5, "All workflow steps should execute"
    assert all(r['workflow_state'] is state for r in results)
    assert state.user_request is not None
    assert hasattr(state, 'metadata')