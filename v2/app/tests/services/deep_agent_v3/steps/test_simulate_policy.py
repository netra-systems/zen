
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.deep_agent_v3.steps.simulate_policy import simulate_policy
from app.services.deep_agent_v3.state import AgentState
from app.schema import LearnedPolicy, PredictedOutcome, BaselineMetrics

@pytest.mark.asyncio
async def test_simulate_policy_success():
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
    policy_simulator = MagicMock()
    policy_simulator.simulate = AsyncMock(return_value=PredictedOutcome(supply_option_name="option1", utility_score=0.9, predicted_cost_usd=0.01, predicted_latency_ms=100, predicted_quality_score=0.9, explanation="", confidence=0.9))

    # Act
    result = await simulate_policy(state, policy_simulator)

    # Assert
    assert result == "Successfully simulated policy"
    assert state.predicted_outcomes is not None
    policy_simulator.simulate.assert_called_once_with(state.learned_policies[0])

@pytest.mark.asyncio
async def test_simulate_policy_no_policies():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.learned_policies = []
    policy_simulator = MagicMock()
    policy_simulator.simulate = AsyncMock()

    # Act
    result = await simulate_policy(state, policy_simulator)

    # Assert
    assert result == "No policies to simulate."
    policy_simulator.simulate.assert_not_called()
