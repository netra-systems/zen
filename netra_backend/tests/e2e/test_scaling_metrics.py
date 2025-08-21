"""
Scaling Metrics Validation Tests
Tests validation of scaling metrics and projections.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent

from netra_backend.tests.e2e.scaling_test_helpers import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    create_scaling_setup, execute_scaling_workflow,
    create_50_percent_increase_state, create_cost_projection_state,
    validate_usage_metrics_accuracy, validate_cost_projection_accuracy
)


@pytest.fixture
def scaling_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for scaling impact analysis testing."""
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return create_scaling_setup(agents, real_llm_manager, real_websocket_manager)


class TestScalingMetricsValidation:
    """Test validation of scaling metrics and projections."""
    
    async def test_usage_metrics_accuracy(self, scaling_analysis_setup):
        """Test accuracy of usage metrics collection and projection."""
        setup = scaling_analysis_setup
        state = create_50_percent_increase_state()
        results = await execute_scaling_workflow(setup, state)
        validate_usage_metrics_accuracy(results, state)
    
    async def test_cost_projection_validation(self, scaling_analysis_setup):
        """Test validation of cost projection calculations."""
        setup = scaling_analysis_setup
        state = create_cost_projection_state()
        results = await execute_scaling_workflow(setup, state)
        validate_cost_projection_accuracy(results)