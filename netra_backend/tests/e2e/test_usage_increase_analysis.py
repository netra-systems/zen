"""
Usage Increase Analysis Tests
Tests agent analysis of usage increase scenarios for scaling impact.
Maximum 300 lines, functions ≤8 lines.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent

from netra_backend.tests.e2e.scaling_test_helpers import (

# Add project root to path
    create_scaling_setup, execute_scaling_workflow,
    create_50_percent_increase_state, create_cost_projection_state,
    validate_50_percent_increase_results, validate_cost_projection_results
)


@pytest.fixture
def scaling_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for scaling impact analysis testing."""
    agents = {
        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return create_scaling_setup(agents, real_llm_manager, real_websocket_manager)


class TestUsageIncreaseAnalysis:
    """Test analysis of usage increase impact on costs and rate limits."""
    
    async def test_50_percent_usage_increase_impact(self, scaling_analysis_setup):
        """Test: 'I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?'"""
        setup = scaling_analysis_setup
        state = create_50_percent_increase_state()
        results = await execute_scaling_workflow(setup, state)
        validate_50_percent_increase_results(results, state)
    
    async def test_cost_impact_projection(self, scaling_analysis_setup):
        """Test detailed cost impact projection for usage increases."""
        setup = scaling_analysis_setup
        state = create_cost_projection_state()
        results = await execute_scaling_workflow(setup, state)
        validate_cost_projection_results(results, state)