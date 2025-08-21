"""
Scaling Workflow Integrity Tests
Tests integrity of complete scaling analysis workflows.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent

from netra_backend.tests.e2e.scaling_test_helpers import (

# Add project root to path
    create_scaling_setup, execute_scaling_workflow,
    create_50_percent_increase_state, create_gradual_scaling_state,
    validate_data_consistency_across_agents, validate_recommendation_coherence
)


@pytest.fixture
def scaling_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for scaling impact analysis testing."""
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return create_scaling_setup(agents, real_llm_manager, real_websocket_manager)


class TestScalingWorkflowIntegrity:
    """Test integrity of complete scaling analysis workflows."""
    
    async def test_end_to_end_data_consistency(self, scaling_analysis_setup):
        """Test data consistency throughout scaling analysis workflow."""
        setup = scaling_analysis_setup
        state = create_50_percent_increase_state()
        results = await execute_scaling_workflow(setup, state)
        validate_data_consistency_across_agents(results, state)
    
    async def test_scaling_recommendations_coherence(self, scaling_analysis_setup):
        """Test coherence of scaling recommendations across agents."""
        setup = scaling_analysis_setup
        state = create_gradual_scaling_state()
        results = await execute_scaling_workflow(setup, state)
        validate_recommendation_coherence(results)