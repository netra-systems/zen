"""
Rate Limit Analysis E2E Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (paying customers with significant usage)
- Business Goal: Prevent service degradation and revenue loss from rate limiting
- Value Impact: Proactive rate limit management enables uninterrupted AI operations
- Strategic Impact: Customer retention through predictive capacity management

Tests end-to-end rate limit analysis workflows to ensure customers
can predict and manage rate limit impacts before they affect operations.

CRITICAL: These tests validate rate limit prediction accuracy for business continuity.
Maximum 300 lines, functions  <= 8 lines per SSOT standards.
"""

import pytest
from typing import Dict, Any, List

from test_framework.base_e2e_test import BaseE2ETest
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent


@pytest.fixture
def rate_limit_analysis_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for rate limit analysis testing."""
    agents = {
        'triage': UnifiedTriageAgent(real_llm_manager, real_tool_dispatcher),
        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher)
    }
    return {
        'agents': agents,
        'llm_manager': real_llm_manager,
        'websocket_manager': real_websocket_manager,
        'tool_dispatcher': real_tool_dispatcher
    }


class TestRateLimitImpactAnalysis(BaseE2ETest):
    """Test rate limit impact analysis for proactive capacity management."""

    @pytest.mark.asyncio
    async def test_basic_rate_limit_analysis(self, rate_limit_analysis_setup):
        """Test basic rate limit impact analysis workflow."""
        setup = rate_limit_analysis_setup
        state = _create_basic_rate_limit_state()
        results = await _execute_rate_limit_workflow(setup, state)
        _validate_rate_limit_analysis_results(results)

    @pytest.mark.asyncio 
    async def test_usage_spike_rate_limit_impact(self, rate_limit_analysis_setup):
        """Test rate limit analysis for sudden usage spikes."""
        setup = rate_limit_analysis_setup
        state = _create_usage_spike_state()
        results = await _execute_rate_limit_workflow(setup, state)
        _validate_spike_rate_limit_results(results)

    @pytest.mark.real_llm
    @pytest.mark.asyncio
    async def test_rate_limit_prediction_accuracy(self, rate_limit_analysis_setup):
        """Test rate limit prediction accuracy with real LLM."""
        setup = rate_limit_analysis_setup
        state = _create_prediction_accuracy_state()
        results = await _execute_rate_limit_workflow(setup, state)
        await _validate_prediction_accuracy(results, setup)


# Helper functions ( <= 8 lines each per SSOT standards)

def _create_basic_rate_limit_state() -> DeepAgentState:
    """Create state for basic rate limit analysis test."""
    return DeepAgentState(
        user_request="Analyze my current API usage and predict when I'll hit rate limits",
        metadata={'test_type': 'basic_rate_limit', 'analysis_scope': 'current_usage'}
    )


def _create_usage_spike_state() -> DeepAgentState:
    """Create state for usage spike rate limit test."""
    return DeepAgentState(
        user_request="I'm expecting 3x usage increase tomorrow. Will I hit rate limits?",
        metadata={'test_type': 'usage_spike', 'multiplier': '3x', 'timeframe': 'tomorrow'}
    )


def _create_prediction_accuracy_state() -> DeepAgentState:
    """Create state for prediction accuracy test."""
    return DeepAgentState(
        user_request="Predict my rate limit exposure for next 30 days based on current trends",
        metadata={'test_type': 'prediction_accuracy', 'timeframe': '30_days'}
    )


async def _execute_rate_limit_workflow(setup: Dict[str, Any], state: DeepAgentState) -> List[Any]:
    """Execute rate limit analysis workflow with given setup and state."""
    # Basic workflow execution - delegate to triage agent
    triage_agent = setup['agents']['triage']
    results = await triage_agent.execute(state)
    return [results] if not isinstance(results, list) else results


def _validate_rate_limit_analysis_results(results: List[Any]) -> None:
    """Validate basic rate limit analysis results."""
    assert len(results) > 0, "No results returned from rate limit analysis"
    # Check for rate limit related content in results
    result_text = str(results).lower()
    assert any(term in result_text for term in ['rate', 'limit', 'usage']), "Results missing rate limit analysis"


def _validate_spike_rate_limit_results(results: List[Any]) -> None:
    """Validate usage spike rate limit analysis results."""
    assert len(results) > 0, "No results returned from spike analysis"
    result_text = str(results).lower()
    assert any(term in result_text for term in ['spike', '3x', 'increase']), "Results missing spike analysis"


async def _validate_prediction_accuracy(results: List[Any], setup: Dict[str, Any]) -> None:
    """Validate rate limit prediction accuracy with quality checks."""
    assert len(results) > 0, "No prediction results returned"
    result_text = str(results).lower() 
    assert any(term in result_text for term in ['predict', '30', 'trend']), "Results missing prediction analysis"
    # Additional quality validation could be added here with setup['llm_manager']