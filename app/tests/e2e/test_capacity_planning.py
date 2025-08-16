"""
Capacity Planning Workflow Tests
Tests capacity planning workflows for different scaling scenarios.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent

from app.tests.e2e.scaling_test_helpers import (
    create_scaling_setup, execute_scaling_workflow,
    create_gradual_scaling_state, create_traffic_spike_state,
    validate_gradual_scaling_plan, validate_spike_handling_strategy
)


@pytest.fixture
def scaling_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for scaling impact analysis testing."""
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return create_scaling_setup(agents, real_llm_manager, real_websocket_manager)


class TestCapacityPlanningWorkflows:
    """Test capacity planning workflows for different scaling scenarios."""
    
    async def test_gradual_scaling_capacity_plan(self, scaling_analysis_setup):
        """Test gradual scaling capacity planning."""
        setup = scaling_analysis_setup
        state = create_gradual_scaling_state()
        results = await execute_scaling_workflow(setup, state)
        validate_gradual_scaling_plan(results)
    
    async def test_sudden_spike_handling(self, scaling_analysis_setup):
        """Test sudden traffic spike handling strategies."""
        setup = scaling_analysis_setup
        state = create_traffic_spike_state()
        results = await execute_scaling_workflow(setup, state)
        validate_spike_handling_strategy(results)