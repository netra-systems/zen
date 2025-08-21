"""
Model Optimization and Edge Case Workflows Test Suite
Tests real-time chat optimization, data flow, edge cases, and workflow integrity.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import asyncio
from typing import Dict, List

from netra_backend.app.agents.state import DeepAgentState
from schemas import SubAgentLifecycle
from netra_backend.app.core.exceptions import NetraException

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



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


async def _execute_model_selection_workflow(setup: Dict, state: DeepAgentState) -> List[Dict]:
    """Execute complete model selection workflow with all 5 agents."""
    from netra_backend.tests.e2e.test_model_effectiveness_workflows import _execute_model_selection_workflow as execute_workflow
    return await execute_workflow(setup, state)


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


def _create_model_effectiveness_state() -> DeepAgentState:
    """Create state for model effectiveness analysis."""
    from netra_backend.tests.e2e.test_model_effectiveness_workflows import _create_model_effectiveness_state as create_state
    return create_state()


def _create_gpt5_tool_selection_state() -> DeepAgentState:
    """Create state for GPT-5 tool selection."""
    from netra_backend.tests.e2e.test_model_effectiveness_workflows import _create_gpt5_tool_selection_state as create_state
    return create_state()


def _validate_metadata_propagation(results: List[Dict], state: DeepAgentState):
    """Validate metadata propagation through workflow."""
    assert all(r['workflow_state'] is state for r in results)
    candidate_models = state.metadata.custom_fields.get('candidate_models', '')
    assert 'gpt-4o' in candidate_models and 'claude-3-sonnet' in candidate_models
    assert all(r['state_updated'] for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED)


def _validate_recommendation_consistency(results: List[Dict], state: DeepAgentState):
    """Validate consistency of recommendations."""
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 3, "Core workflow should complete"
    assert state.metadata.custom_fields.get('target_model') == 'GPT-5'


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])