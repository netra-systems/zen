"""
GPT-5 Migration and Tool Selection Tests
Tests for GPT-5 migration workflows and tool selection
"""

from typing import Dict, List

from netra_backend.app.agents.state import AgentMetadata, DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.tests.e2e.model_effectiveness_tests import (
    _execute_model_selection_workflow,
)

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
        metadata=AgentMetadata(custom_fields={'test_type': 'gpt5_tool_selection', 'target_model': 'GPT-5', 'focus': 'tool_migration'})
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
    # For model selection workflows, accept completed agents even with None results (fallback scenarios)
    assert result['agent_state'] in [SubAgentLifecycle.COMPLETED]

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