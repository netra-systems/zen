
import pytest
from unittest.mock import MagicMock
from app.services.deep_agent_v3.steps.generate_final_report import generate_final_report
from app.services.deep_agent_v3.state import AgentState
from app.schema import LearnedPolicy, PredictedOutcome, BaselineMetrics

@pytest.mark.asyncio
async def test_generate_final_report_success():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.learned_policies=[
        LearnedPolicy(
            pattern_name="pattern1",
            optimal_supply_option_name="option1",
            predicted_outcome=PredictedOutcome(supply_option_name="option1", utility_score=0.9, predicted_cost_usd=0.01, predicted_latency_ms=100, predicted_quality_score=0.9, explanation="", confidence=0.9),
            alternative_outcomes=[],
            baseline_metrics=BaselineMetrics(avg_cost_usd=0.0, avg_latency_ms=0.0, avg_quality_score=0.0),
            pattern_impact_fraction=0
        )
    ]
    state.predicted_outcomes=[
        PredictedOutcome(supply_option_name="option1", utility_score=0.9, predicted_cost_usd=0.01, predicted_latency_ms=100, predicted_quality_score=0.9, explanation="test explanation", confidence=0.9)
    ]

    # Act
    result = await generate_final_report(state)

    # Assert
    assert result == "Final report generated."
    assert state.final_report is not None
    assert "pattern1" in state.final_report
    assert "option1" in state.final_report
    assert "test explanation" in state.final_report

@pytest.mark.asyncio
async def test_generate_final_report_no_policies():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.learned_policies = []

    # Act & Assert
    with pytest.raises(ValueError):
        await generate_final_report(state)
