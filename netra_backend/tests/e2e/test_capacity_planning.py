"""
Capacity Planning Workflow Tests
Tests capacity planning workflows for different scaling scenarios.
Maximum 300 lines, functions ≤8 lines.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest

from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.state import DeepAgentState

# Add project root to path
from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
)
from tests.scaling_test_helpers import (
    create_gradual_scaling_state,
    # Add project root to path
    create_scaling_setup,
    create_traffic_spike_state,
    execute_scaling_workflow,
    validate_gradual_scaling_plan,
    validate_spike_handling_strategy,
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


@pytest.mark.real_llm
class TestExamplePromptsCapacityPlanning:
    """Test specific example prompt EP-003 with real LLM validation."""
    
    async def test_ep_003_usage_increase_impact_real_llm(self, scaling_analysis_setup):
        """Test EP-003: Usage increase impact analysis using real LLM."""
        setup = scaling_analysis_setup
        state = _create_ep_003_state()
        results = await execute_scaling_workflow(setup, state)
        await _validate_ep_003_results(results, state, setup)


def _create_ep_003_state() -> DeepAgentState:
    """Create state for EP-003 example prompt test."""
    return DeepAgentState(
        user_request="I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
        metadata={'test_type': 'ep_003', 'prompt_id': 'EP-003', 'usage_increase': '50%', 'timeframe': 'next_month'}
    )


async def _validate_ep_003_results(results, state: DeepAgentState, setup):
    """Validate EP-003 results with enhanced quality checks."""
    _validate_capacity_planning_results(results, state)
    await _validate_response_quality_ep_003(results, setup)


def _validate_capacity_planning_results(results, state: DeepAgentState):
    """Validate capacity planning workflow results."""
    assert len(results) > 0, "No results returned from workflow"
    assert '50%' in state.user_request
    assert any('usage' in str(result).lower() for result in results)
    assert any('cost' in str(result).lower() or 'rate limit' in str(result).lower() for result in results)


async def _validate_response_quality_ep_003(results, setup):
    """Validate response quality for EP-003 using quality gate service."""
    quality_service = QualityGateService()
    final_result = results[-1] if results else None
    
    if final_result:
        response_text = _extract_response_text(final_result)
        is_valid, score, feedback = await quality_service.validate_content(
            content=response_text, content_type=ContentType.CAPACITY_ANALYSIS, quality_level=QualityLevel.MEDIUM
        )
        assert is_valid, f"EP-003 response quality validation failed: {feedback}"
        assert score >= 70, f"EP-003 quality score too low: {score}"


def _extract_response_text(result) -> str:
    """Extract response text from workflow result."""
    if isinstance(result, dict):
        return str(result.get('execution_result', result.get('response', str(result))))
    return str(result)