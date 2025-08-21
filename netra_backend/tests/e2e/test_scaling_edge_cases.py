"""
Scaling Edge Cases Tests
Tests edge cases in scaling analysis workflows.
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
    create_extreme_usage_state, create_declining_usage_state,
    validate_extreme_usage_handling, validate_declining_usage_handling
)


@pytest.fixture
def scaling_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for scaling impact analysis testing."""
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return create_scaling_setup(agents, real_llm_manager, real_websocket_manager)


class TestScalingEdgeCases:
    """Test edge cases in scaling analysis workflows."""
    
    async def test_extreme_usage_increase(self, scaling_analysis_setup):
        """Test handling of extreme usage increase scenarios."""
        setup = scaling_analysis_setup
        state = create_extreme_usage_state()
        results = await execute_scaling_workflow(setup, state)
        validate_extreme_usage_handling(results)
    
    async def test_declining_usage_analysis(self, scaling_analysis_setup):
        """Test analysis of declining usage scenarios."""
        setup = scaling_analysis_setup
        state = create_declining_usage_state()
        results = await execute_scaling_workflow(setup, state)
        validate_declining_usage_handling(results)