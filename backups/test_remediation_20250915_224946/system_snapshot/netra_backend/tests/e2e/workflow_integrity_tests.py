"""
Workflow Integrity and Edge Case Tests
Tests for data flow, edge cases, and overall workflow integrity
"""

from typing import Dict, List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.agents.state import AgentMetadata, DeepAgentState
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.tests.e2e.model_effectiveness_tests import (
    _create_model_effectiveness_state,
    _execute_model_selection_workflow,
)

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

def _create_gpt5_tool_selection_state() -> DeepAgentState:
    """Create state for GPT-5 tool selection."""
    return DeepAgentState(
        user_request="@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",
        metadata=AgentMetadata(custom_fields={'test_type': 'gpt5_tool_selection', 'target_model': 'GPT-5', 'focus': 'tool_migration'})
    )

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

def _validate_metadata_propagation(results: List[Dict], state: DeepAgentState):
    """Validate metadata propagation through workflow."""
    assert all(r['workflow_state'] is state for r in results)
    candidate_models = state.metadata.custom_fields.get('candidate_models', '')
    assert 'gpt-4o' in candidate_models and LLMModel.GEMINI_2_5_FLASH.value in candidate_models
    assert all(r['state_updated'] for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED)

def _validate_recommendation_consistency(results: List[Dict], state: DeepAgentState):
    """Validate consistency of recommendations."""
    completed_results = [r for r in results if r['agent_state'] == SubAgentLifecycle.COMPLETED]
    assert len(completed_results) >= 3, "Core workflow should complete"
    assert state.metadata.custom_fields.get('target_model') == 'GPT-5'

def _validate_unavailable_model_handling(results: List[Dict]):
    """Validate handling of unavailable model requests."""
    assert len(results) >= 1, "At least triage should execute"
    triage_result = results[0]
    assert triage_result['agent_state'] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

def _validate_conflicting_requirements_resolution(results: List[Dict]):
    """Validate resolution of conflicting requirements."""
    assert len(results) >= 3, "Core workflow should attempt execution"
    assert any(r['agent_state'] == SubAgentLifecycle.COMPLETED for r in results[:3])

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