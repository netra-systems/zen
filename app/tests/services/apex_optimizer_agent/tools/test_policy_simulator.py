
"""
Comprehensive unit tests for policy_simulator tool.
Designed with ultra-thinking for robust policy simulation testing.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import List

from app.services.apex_optimizer_agent.tools.policy_simulator import policy_simulator, LearnedPolicy


class TestPolicySimulator:
    """Comprehensive test suite for policy_simulator tool"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM manager"""
        return Mock()

    @pytest.fixture
    def mock_policy_simulator_engine(self):
        """Create a mock policy simulator engine"""
        mock_simulator = Mock()
        mock_simulator.simulate = AsyncMock()
        return mock_simulator

    @pytest.fixture
    def sample_learned_policy(self):
        """Create a sample learned policy for testing"""
        return LearnedPolicy(
            pattern_name="high_cost_pattern",
            optimal_supply_option_name="gpt-3.5-turbo"
        )

    @pytest.fixture
    def multiple_learned_policies(self):
        """Create multiple learned policies for testing"""
        return [
            LearnedPolicy(
                pattern_name="high_cost_pattern",
                optimal_supply_option_name="gpt-3.5-turbo"
            ),
            LearnedPolicy(
                pattern_name="high_latency_pattern",
                optimal_supply_option_name="claude-3-haiku"
            ),
            LearnedPolicy(
                pattern_name="quality_critical_pattern",
                optimal_supply_option_name="gpt-4"
            )
        ]

    @pytest.mark.asyncio
    async def test_policy_simulator_empty_policies(self, mock_db_session, mock_llm_manager, mock_policy_simulator_engine):
        """Test policy simulator with empty policies list"""
        result = await policy_simulator.arun({
            "learned_policies": [],
            "db_session": mock_db_session,
            "llm_manager": mock_llm_manager,
            "policy_simulator": mock_policy_simulator_engine
        })
        
        assert result == "No policies to simulate."
        mock_policy_simulator_engine.simulate.assert_not_called()

    @pytest.mark.asyncio
    async def test_policy_simulator_single_policy(self, sample_learned_policy, mock_db_session, mock_llm_manager, mock_policy_simulator_engine):
        """Test policy simulator with single policy"""
        mock_policy_simulator_engine.simulate.return_value = {
            "predicted_cost_reduction": 0.25,
            "predicted_latency_impact": 0.1,
            "confidence_score": 0.85
        }
        
        result = await policy_simulator.arun({
            "learned_policies": [sample_learned_policy],
            "db_session": mock_db_session,
            "llm_manager": mock_llm_manager,
            "policy_simulator": mock_policy_simulator_engine
        })
        
        assert result == "Successfully simulated policy"
        mock_policy_simulator_engine.simulate.assert_called_once_with(sample_learned_policy)

    @pytest.mark.asyncio
    async def test_policy_simulator_multiple_policies_only_simulates_first(self, multiple_learned_policies, mock_db_session, mock_llm_manager, mock_policy_simulator_engine):
        """Test that policy simulator only simulates the first policy (current implementation)"""
        mock_policy_simulator_engine.simulate.return_value = {
            "predicted_outcome": "positive"
        }
        
        result = await policy_simulator.arun({
            "learned_policies": multiple_learned_policies,
            "db_session": mock_db_session,
            "llm_manager": mock_llm_manager,
            "policy_simulator": mock_policy_simulator_engine
        })
        
        assert result == "Successfully simulated policy"
        # Should only be called once with the first policy
        mock_policy_simulator_engine.simulate.assert_called_once_with(multiple_learned_policies[0])

    @pytest.mark.asyncio
    async def test_policy_simulator_simulation_failure(self, sample_learned_policy, mock_db_session, mock_llm_manager, mock_policy_simulator_engine):
        """Test policy simulator when simulation engine fails"""
        mock_policy_simulator_engine.simulate.side_effect = Exception("Simulation engine error")
        
        with pytest.raises(Exception) as exc_info:
            await policy_simulator.arun({
                "learned_policies": [sample_learned_policy],
                "db_session": mock_db_session,
                "llm_manager": mock_llm_manager,
                "policy_simulator": mock_policy_simulator_engine
            })
        
        assert "Simulation engine error" in str(exc_info.value)
        mock_policy_simulator_engine.simulate.assert_called_once_with(sample_learned_policy)

    @pytest.mark.asyncio
    async def test_policy_simulator_with_complex_policy(self, mock_db_session, mock_llm_manager, mock_policy_simulator_engine):
        """Test policy simulator with complex policy names and patterns"""
        complex_policy = LearnedPolicy(
            pattern_name="multi_constraint_optimization_pattern_v2.1",
            optimal_supply_option_name="claude-3-opus-20240229"
        )
        
        mock_policy_simulator_engine.simulate.return_value = {
            "predicted_metrics": {
                "cost_reduction_percentage": 0.32,
                "latency_improvement_ms": 150,
                "quality_score": 0.91
            }
        }
        
        result = await policy_simulator.arun({
            "learned_policies": [complex_policy],
            "db_session": mock_db_session,
            "llm_manager": mock_llm_manager,
            "policy_simulator": mock_policy_simulator_engine
        })
        
        assert result == "Successfully simulated policy"
        mock_policy_simulator_engine.simulate.assert_called_once_with(complex_policy)

    def test_learned_policy_model_validation(self):
        """Test LearnedPolicy model validation"""
        # Valid policy
        valid_policy = LearnedPolicy(
            pattern_name="test_pattern",
            optimal_supply_option_name="test_option"
        )
        assert valid_policy.pattern_name == "test_pattern"
        assert valid_policy.optimal_supply_option_name == "test_option"
        
        # Test with empty strings (should be allowed)
        empty_policy = LearnedPolicy(
            pattern_name="",
            optimal_supply_option_name=""
        )
        assert empty_policy.pattern_name == ""
        assert empty_policy.optimal_supply_option_name == ""

    def test_learned_policy_model_serialization(self):
        """Test LearnedPolicy model serialization"""
        policy = LearnedPolicy(
            pattern_name="serialization_test",
            optimal_supply_option_name="gpt-4-turbo"
        )
        
        policy_dict = policy.model_dump()
        assert policy_dict == {
            "pattern_name": "serialization_test",
            "optimal_supply_option_name": "gpt-4-turbo"
        }
        
        json_str = policy.model_dump_json()
        assert "serialization_test" in json_str
        assert "gpt-4-turbo" in json_str

    @pytest.mark.asyncio
    async def test_policy_simulator_async_behavior(self, sample_learned_policy, mock_db_session, mock_llm_manager, mock_policy_simulator_engine):
        """Test that policy simulator properly handles async operations"""
        import asyncio
        
        async def slow_simulate(policy):
            await asyncio.sleep(0.01)  # Simulate async work
            return {"result": "async_complete"}
        
        mock_policy_simulator_engine.simulate = slow_simulate
        
        start_time = asyncio.get_event_loop().time()
        result = await policy_simulator.arun({
            "learned_policies": [sample_learned_policy],
            "db_session": mock_db_session,
            "llm_manager": mock_llm_manager,
            "policy_simulator": mock_policy_simulator_engine
        })
        elapsed = asyncio.get_event_loop().time() - start_time
        
        assert result == "Successfully simulated policy"
        assert elapsed >= 0.009  # Allow for small timing variations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.apex_optimizer_agent.tools.policy_simulator"])
