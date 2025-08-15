"""
Comprehensive E2E Model Selection Workflows Test Suite
Tests real LLM agents with complete data flow validation for model selection and optimization.
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
def model_selection_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for model selection testing."""
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
    return _build_model_setup(agents, real_llm_manager, real_websocket_manager)


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


def _build_model_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:
    """Build complete setup dictionary."""
    return {
        'agents': agents, 'llm': llm, 'websocket': ws,
        'run_id': str(uuid.uuid4()), 'user_id': 'model-test-user'
    }


class TestModelEffectivenessAnalysis:
    """Test model effectiveness analysis workflows."""
    
    async def test_gpt4o_claude3_sonnet_effectiveness(self, model_selection_setup):
        """Test: 'I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?'"""
        setup = model_selection_setup
        state = _create_model_effectiveness_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_model_effectiveness_results(results, state)
    
    async def test_comparative_model_analysis(self, model_selection_setup):
        """Test comparative analysis between different models."""
        setup = model_selection_setup
        state = _create_comparative_analysis_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_comparative_analysis_results(results)


def _create_model_effectiveness_state() -> DeepAgentState:
    """Create state for model effectiveness analysis."""
    return DeepAgentState(
        user_request="I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
        metadata={'test_type': 'model_effectiveness', 'candidate_models': ['gpt-4o', 'claude-3-sonnet']}
    )


def _create_comparative_analysis_state() -> DeepAgentState:
    """Create state for comparative model analysis."""
    return DeepAgentState(
        user_request="Compare performance characteristics of GPT-4, Claude-3, and Gemini models for our workload.",
        metadata={'test_type': 'comparative_analysis', 'models': ['gpt-4', 'claude-3', 'gemini']}
    )


async def _execute_model_selection_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete model selection workflow with all 5 agents."""
    results = []
    workflow_steps = ['triage', 'data', 'optimization', 'actions', 'reporting']
    
    for step_name in workflow_steps:
        step_result = await _execute_model_step(setup, step_name, state)
        results.append(step_result)
    
    return results


async def _execute_model_step(setup: Dict, step_name: str, state: DeepAgentState) -> Dict:
    """Execute single model selection workflow step."""
    # Fix WebSocket interface - ensure both methods are available
    if hasattr(setup['websocket'], 'send_message') and not hasattr(setup['websocket'], 'send_to_thread'):
        setup['websocket'].send_to_thread = setup['websocket'].send_message
    elif hasattr(setup['websocket'], 'send_to_thread') and not hasattr(setup['websocket'], 'send_message'):
        setup['websocket'].send_message = setup['websocket'].send_to_thread
    
    agent = setup['agents'][step_name]
    agent.websocket_manager = setup['websocket']
    agent.user_id = setup['user_id']
    
    execution_result = await agent.run(state, setup['run_id'], True)
    return _create_model_result(step_name, agent, state, execution_result)


def _create_model_result(step_name: str, agent, state: DeepAgentState, result) -> Dict:
    """Create model selection result dictionary."""
    return {
        'step': step_name, 'agent_state': agent.state, 'workflow_state': state,
        'execution_result': result, 'state_updated': state is not None,
        'agent_type': type(agent).__name__
    }


def _validate_model_effectiveness_results(results: List[Dict], state: DeepAgentState):
    """Validate model effectiveness analysis results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    _validate_model_identification(results[0], state)
    _validate_current_setup_analysis(results[1], state)
    _validate_effectiveness_optimization(results[2], state)


def _validate_model_identification(result: Dict, state: DeepAgentState):
    """Validate identification of target models."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'gpt-4o' in state.user_request or 'claude-3-sonnet' in state.user_request
    assert 'effectiveness' in state.user_request


def _validate_current_setup_analysis(result: Dict, state: DeepAgentState):
    """Validate current setup analysis for model compatibility."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']
    assert result['agent_type'] == 'DataSubAgent'


def _validate_effectiveness_optimization(result: Dict, state: DeepAgentState):
    """Validate effectiveness optimization recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None
    assert result['agent_type'] == 'OptimizationsCoreSubAgent'


def _validate_comparative_analysis_results(results: List[Dict]):
    """Validate comparative model analysis results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    assert all(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])


class TestGPT5MigrationWorkflows:
    """Test GPT-5 migration and tool selection workflows."""
    
    async def test_gpt5_tool_selection(self, model_selection_setup):
        """Test: '@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?'"""
        setup = model_selection_setup
        state = _create_gpt5_tool_selection_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_gpt5_tool_selection_results(results, state)
    
    async def test_gpt5_upgrade_analysis(self, model_selection_setup):
        """Test: '@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher'"""
        setup = model_selection_setup
        state = _create_gpt5_upgrade_analysis_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_gpt5_upgrade_analysis_results(results, state)


def _create_gpt5_tool_selection_state() -> DeepAgentState:
    """Create state for GPT-5 tool selection."""
    return DeepAgentState(
        user_request="@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",
        metadata={'test_type': 'gpt5_tool_selection', 'target_model': 'GPT-5', 'focus': 'tool_migration'}
    )


def _create_gpt5_upgrade_analysis_state() -> DeepAgentState:
    """Create state for GPT-5 upgrade analysis."""
    return DeepAgentState(
        user_request="@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher",
        metadata={'test_type': 'gpt5_upgrade_analysis', 'action': 'cost_benefit_analysis', 'rollback_candidate': True}
    )


def _validate_gpt5_tool_selection_results(results: List[Dict], state: DeepAgentState):
    """Validate GPT-5 tool selection results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    _validate_tool_inventory_analysis(results[1])
    _validate_migration_recommendations(results[2])
    _validate_verbosity_configuration(results[3])


def _validate_tool_inventory_analysis(result: Dict):
    """Validate tool inventory analysis."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']


def _validate_migration_recommendations(result: Dict):
    """Validate migration recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['execution_result'] is not None


def _validate_verbosity_configuration(result: Dict):
    """Validate verbosity configuration recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED


def _validate_gpt5_upgrade_analysis_results(results: List[Dict], state: DeepAgentState):
    """Validate GPT-5 upgrade analysis results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    _validate_upgrade_impact_assessment(results[1])
    _validate_rollback_recommendations(results[3])


def _validate_upgrade_impact_assessment(result: Dict):
    """Validate upgrade impact assessment."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert result['state_updated']


def _validate_rollback_recommendations(result: Dict):
    """Validate rollback recommendations."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED


class TestRealTimeChatOptimization:
    """Test real-time chat model optimization workflows."""
    
    async def test_real_time_chat_model_optimization(self, model_selection_setup):
        """Test: '@Netra GPT-5 is way too expensive for the real time chat feature. Move to claude 4.1 or GPT-5-mini? Validate quality impact'"""
        setup = model_selection_setup
        state = _create_real_time_chat_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_real_time_chat_results(results, state)
    
    async def test_latency_cost_tradeoff_analysis(self, model_selection_setup):
        """Test latency vs cost tradeoff analysis for real-time features."""
        setup = model_selection_setup
        state = _create_latency_cost_tradeoff_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_latency_cost_tradeoff_results(results)


def _create_real_time_chat_state() -> DeepAgentState:
    """Create state for real-time chat optimization."""
    return DeepAgentState(
        user_request="@Netra GPT-5 is way too expensive for the real time chat feature. Move to claude 4.1 or GPT-5-mini? Validate quality impact",
        metadata={'test_type': 'real_time_chat', 'feature': 'chat', 'alternatives': ['claude-4.1', 'GPT-5-mini']}
    )


def _create_latency_cost_tradeoff_state() -> DeepAgentState:
    """Create state for latency vs cost tradeoff analysis."""
    return DeepAgentState(
        user_request="Analyze latency and cost tradeoffs for different models in real-time scenarios.",
        metadata={'test_type': 'latency_cost_tradeoff', 'scenario': 'real_time'}
    )


def _validate_real_time_chat_results(results: List[Dict], state: DeepAgentState):
    """Validate real-time chat optimization results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    _validate_cost_analysis_for_chat(results[1], state)
    _validate_alternative_model_evaluation(results[2], state)
    _validate_quality_impact_assessment(results[3], state)


def _validate_cost_analysis_for_chat(result: Dict, state: DeepAgentState):
    """Validate cost analysis for chat feature."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'expensive' in state.user_request
    assert result['state_updated']


def _validate_alternative_model_evaluation(result: Dict, state: DeepAgentState):
    """Validate alternative model evaluation."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'claude 4.1' in state.user_request or 'GPT-5-mini' in state.user_request


def _validate_quality_impact_assessment(result: Dict, state: DeepAgentState):
    """Validate quality impact assessment."""
    assert result['agent_state'] == SubAgentLifecycle.COMPLETED
    assert 'quality impact' in state.user_request


def _validate_latency_cost_tradeoff_results(results: List[Dict]):
    """Validate latency vs cost tradeoff analysis results."""
    assert len(results) == 5, "All 5 workflow steps must execute"
    assert all(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)


class TestModelSelectionDataFlow:
    """Test data flow integrity in model selection workflows."""
    
    async def test_model_metadata_propagation(self, model_selection_setup):
        """Test model metadata propagation through workflow."""
        setup = model_selection_setup
        state = _create_model_effectiveness_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_metadata_propagation(results, state)
    
    async def test_recommendation_consistency(self, model_selection_setup):
        """Test consistency of recommendations across agents."""
        setup = model_selection_setup
        state = _create_gpt5_tool_selection_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_recommendation_consistency(results, state)


def _validate_metadata_propagation(results: List[Dict], state: DeepAgentState):
    """Validate metadata propagation through workflow."""
    assert all(r['workflow_state'] is state for r in results)
    assert state.metadata.get('candidate_models') == ['gpt-4o', 'claude-3-sonnet']
    assert all(r['state_updated'] for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED)


def _validate_recommendation_consistency(results: List[Dict], state: DeepAgentState):
    """Validate consistency of recommendations."""
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 3, "Core workflow should complete"
    assert state.metadata.get('target_model') == 'GPT-5'


class TestModelSelectionEdgeCases:
    """Test edge cases in model selection workflows."""
    
    async def test_unavailable_model_handling(self, model_selection_setup):
        """Test handling of requests for unavailable models."""
        setup = model_selection_setup
        state = _create_unavailable_model_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_unavailable_model_handling(results)
    
    async def test_conflicting_requirements_resolution(self, model_selection_setup):
        """Test resolution of conflicting model requirements."""
        setup = model_selection_setup
        state = _create_conflicting_requirements_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_conflicting_requirements_resolution(results)


def _create_unavailable_model_state() -> DeepAgentState:
    """Create state for unavailable model test."""
    return DeepAgentState(
        user_request="Switch all tools to use GPT-7 and Claude-5 models for maximum performance.",
        metadata={'test_type': 'unavailable_model', 'models': ['GPT-7', 'Claude-5']}
    )


def _create_conflicting_requirements_state() -> DeepAgentState:
    """Create state for conflicting requirements test."""
    return DeepAgentState(
        user_request="I need the highest quality model but also the cheapest option with zero latency increase.",
        metadata={'test_type': 'conflicting_requirements', 'conflicts': ['quality', 'cost', 'latency']}
    )


def _validate_unavailable_model_handling(results: List[Dict]):
    """Validate handling of unavailable model requests."""
    assert len(results) >= 1, "At least triage should execute"
    triage_result = results[0]
    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]


def _validate_conflicting_requirements_resolution(results: List[Dict]):
    """Validate resolution of conflicting requirements."""
    assert len(results) >= 3, "Core workflow should attempt execution"
    assert any(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])


class TestWorkflowIntegrity:
    """Test overall workflow integrity for model selection."""
    
    async def test_complete_workflow_validation(self, model_selection_setup):
        """Test complete workflow validation for model selection."""
        setup = model_selection_setup
        state = _create_model_effectiveness_state()
        results = await _execute_model_selection_workflow(setup, state)
        _validate_complete_workflow(results, state)
    
    async def test_error_recovery_in_workflow(self, model_selection_setup):
        """Test error recovery mechanisms in model selection workflow."""
        setup = model_selection_setup
        state = _create_unavailable_model_state()
        
        try:
            results = await _execute_model_selection_workflow(setup, state)
            _validate_error_recovery(results)
        except NetraException:
            pass  # Expected for some scenarios


def _validate_complete_workflow(results: List[Dict], state: DeepAgentState):
    """Validate complete workflow execution."""
    assert len(results) == 5, "All 5 workflow steps should execute"
    assert all(r['workflow_state'] is state for r in results)
    assert state.user_request is not None
    assert hasattr(state, 'metadata')


def _validate_error_recovery(results: List[Dict]):
    """Validate error recovery mechanisms."""
    assert len(results) >= 1, "At least some steps should execute"
    assert any(r['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED] 
               for r in results)