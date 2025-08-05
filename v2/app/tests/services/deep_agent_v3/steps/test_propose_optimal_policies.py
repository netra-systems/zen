import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.deep_agent_v3.steps.propose_optimal_policies import propose_optimal_policies
from app.services.deep_agent_v3.state import AgentState
from app.schema import DiscoveredPattern

@pytest.mark.asyncio
async def test_propose_optimal_policies_success():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.patterns=[
        DiscoveredPattern(pattern_name="pattern1", pattern_description="desc1", centroid_features={}, member_span_ids=[], member_count=0),
        DiscoveredPattern(pattern_name="pattern2", pattern_description="desc2", centroid_features={}, member_span_ids=[], member_count=0)
    ]
    state.raw_logs = []
    policy_proposer = MagicMock()
    policy_proposer.propose_policies = AsyncMock(return_value=(["policy1", "policy2"], ["outcome1", "outcome2"]))

    # Act
    result = await propose_optimal_policies(state, policy_proposer)

    # Assert
    assert result == "Successfully proposed 2 optimal policies."
    assert len(state.learned_policies) == 2
    assert len(state.predicted_outcomes) == 2
    policy_proposer.propose_policies.assert_called_once_with(state.patterns, {})

@pytest.mark.asyncio
async def test_propose_optimal_policies_no_patterns():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.patterns = []
    policy_proposer = MagicMock()
    policy_proposer.propose_policies = AsyncMock(return_value=([], []))

    # Act
    result = await propose_optimal_policies(state, policy_proposer)

    # Assert
    assert result == "No discovered patterns to propose policies for."
    policy_proposer.propose_policies.assert_not_called()