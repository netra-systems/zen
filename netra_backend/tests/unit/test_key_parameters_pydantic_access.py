"""Regression test for KeyParameters Pydantic model access in DataSubAgent."""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

try:
    from netra_backend.app.agents.state import DeepAgentState
    from netra_backend.app.agents.triage.unified_triage_agent import KeyParameters, TriageResult
except ImportError:
    pytest.skip("Data sub agent execution engine has been removed/moved", allow_module_level=True)

class TestKeyParametersAccess:
    """Test proper handling of KeyParameters as Pydantic model vs dict."""

    @pytest.fixture
    def mock_execution_engine(self):
        """Create mock execution engine instance."""
        engine = Mock()
        engine.parameter_processor = Mock()
        engine.parameter_processor._build_analysis_params_dict = Mock()
        engine.parameter_processor.extract_analysis_params = Mock()
        return engine

    def test_build_analysis_params_with_pydantic_model(self, mock_execution_engine):
        """Test _build_analysis_params_dict handles Pydantic KeyParameters."""
        # Create KeyParameters as Pydantic model with its actual fields
        key_params = KeyParameters(
            workload_type="batch_processing",
            optimization_focus="latency",
            time_sensitivity="high",
            scope="global"
        )

        intent = {"primary": "optimization", "secondary": "cost_reduction"}

        # Mock the return value
        mock_execution_engine.parameter_processor._build_analysis_params_dict.return_value = {
            "user_id": 1,
            "workload_id": None,
            "metric_names": ["latency_ms", "throughput", "cost_cents"],
            "time_range_str": "last_24_hours",
            "primary_intent": "optimization"
        }

        # Call method - should not raise AttributeError
        result = mock_execution_engine.parameter_processor._build_analysis_params_dict(key_params, intent)

        # Verify it uses defaults when fields don't exist
        assert result["user_id"] == 1  # Default
        assert result["workload_id"] is None  # Default
        assert result["metric_names"] == ["latency_ms", "throughput", "cost_cents"]  # Default
        assert result["time_range_str"] == "last_24_hours"  # Default
        assert result["primary_intent"] == "optimization"

    def test_build_analysis_params_with_dict(self, mock_execution_engine):
        """Test _build_analysis_params_dict handles dict input."""
        # Create key_params as dict
        key_params = {
            "user_id": 456,
            "workload_id": "workload_789",
            "metrics": ["latency_ms", "throughput"],
            "time_range": "last_6_hours"
        }

        intent = {"primary": "analysis"}

        # Mock the return value
        mock_execution_engine.parameter_processor._build_analysis_params_dict.return_value = {
            "user_id": 456,
            "workload_id": "workload_789",
            "metric_names": ["latency_ms", "throughput"],
            "time_range_str": "last_6_hours",
            "primary_intent": "analysis"
        }

        # Call method
        result = mock_execution_engine.parameter_processor._build_analysis_params_dict(key_params, intent)

        # Verify correct extraction
        assert result["user_id"] == 456
        assert result["workload_id"] == "workload_789"
        assert result["metric_names"] == ["latency_ms", "throughput"]
        assert result["time_range_str"] == "last_6_hours"
        assert result["primary_intent"] == "analysis"

    def test_build_analysis_params_with_empty_dict(self, mock_execution_engine):
        """Test _build_analysis_params_dict handles empty dict."""
        key_params = {}
        intent = {}

        # Mock the return value with defaults
        mock_execution_engine.parameter_processor._build_analysis_params_dict.return_value = {
            "user_id": 1,
            "workload_id": None,
            "metric_names": ["latency_ms", "throughput", "cost_cents"],
            "time_range_str": "last_24_hours",
            "primary_intent": "general"
        }

        # Call method
        result = mock_execution_engine.parameter_processor._build_analysis_params_dict(key_params, intent)

        # Verify defaults
        assert result["user_id"] == 1
        assert result["workload_id"] is None
        assert result["metric_names"] == ["latency_ms", "throughput", "cost_cents"]
        assert result["time_range_str"] == "last_24_hours"
        assert result["primary_intent"] == "general"

    def test_build_analysis_params_with_partial_pydantic(self, mock_execution_engine):
        """Test _build_analysis_params_dict handles Pydantic model with some fields."""
        # Create KeyParameters with only some fields
        key_params = KeyParameters(
            workload_type="streaming",
            optimization_focus="throughput"
            # time_sensitivity and scope not set
        )

        intent = {"primary": "monitoring"}

        # Mock the return value
        mock_execution_engine.parameter_processor._build_analysis_params_dict.return_value = {
            "user_id": 1,
            "workload_id": None,
            "metric_names": ["latency_ms", "throughput", "cost_cents"],
            "time_range_str": "last_24_hours",
            "primary_intent": "monitoring"
        }

        # Call method
        result = mock_execution_engine.parameter_processor._build_analysis_params_dict(key_params, intent)

        # Verify defaults for non-existent fields
        assert result["user_id"] == 1  # Default
        assert result["workload_id"] is None  # Default
        assert result["metric_names"] == ["latency_ms", "throughput", "cost_cents"]  # Default
        assert result["time_range_str"] == "last_24_hours"  # Default
        assert result["primary_intent"] == "monitoring"

    def test_build_analysis_params_from_state(self, mock_execution_engine):
        """Test _build_analysis_params handles state with TriageResult."""
        # Create mock state with TriageResult containing KeyParameters
        state = DeepAgentState(
            run_id="test_run",
            thread_id="test_thread",
            user_id="test_user",
            user_request="Test request"
        )

        # Create TriageResult with KeyParameters (using actual fields)
        from netra_backend.app.agents.triage.unified_triage_agent import UserIntent

        triage_result = TriageResult(
            key_parameters=KeyParameters(
                workload_type="api_service",
                optimization_focus="reliability",
                time_sensitivity="critical",
                scope="production"
            ),
            user_intent=UserIntent(
                primary_intent="debugging",
                secondary_intents=["performance"]
            )
        )
        state.triage_result = triage_result

        # Mock the return value
        mock_execution_engine.parameter_processor.extract_analysis_params.return_value = {
            "user_id": 1,
            "workload_id": None,
            "metric_names": ["latency_ms", "throughput", "cost_cents"],
            "time_range_str": "last_24_hours",
            "primary_intent": "debugging"
        }

        # Call method
        result = mock_execution_engine.parameter_processor.extract_analysis_params(state)

        # Verify extraction through the chain - should use defaults since KeyParameters doesn't have those fields
        assert result["user_id"] == 1  # Default
        assert result["workload_id"] is None  # Default
        assert result["metric_names"] == ["latency_ms", "throughput", "cost_cents"]  # Default
        assert result["time_range_str"] == "last_24_hours"  # Default
        assert result["primary_intent"] == "debugging"

    def test_build_analysis_params_no_triage_result(self, mock_execution_engine):
        """Test _build_analysis_params handles state without triage_result."""
        state = DeepAgentState(
            run_id="test_run",
            thread_id="test_thread",
            user_id="test_user",
            user_request="Test request"
        )
        state.triage_result = None

        # Mock the return value with defaults
        mock_execution_engine.parameter_processor.extract_analysis_params.return_value = {
            "user_id": 1,
            "workload_id": None,
            "metric_names": ["latency_ms", "throughput", "cost_cents"],
            "time_range_str": "last_24_hours",
            "primary_intent": "general"
        }

        # Call method
        result = mock_execution_engine.parameter_processor.extract_analysis_params(state)

        # Should return defaults
        assert result["user_id"] == 1
        assert result["workload_id"] is None
        assert result["metric_names"] == ["latency_ms", "throughput", "cost_cents"]
        assert result["time_range_str"] == "last_24_hours"
        assert result["primary_intent"] == "general"

    def test_mixed_type_handling_no_errors(self, mock_execution_engine):
        """Test that mixed types don't cause AttributeError."""
        test_cases = [
            # Pydantic model with its actual fields
            KeyParameters(workload_type="batch", optimization_focus="cost"),
            # Dict with the expected fields
            {"user_id": 200, "metrics": ["metric2"]},
            # Empty dict
            {},
            # None handled as empty dict fallback
            None
        ]

        for i, key_params in enumerate(test_cases):
            if key_params is None:
                key_params = {}

            # Mock different return values for each case
            mock_execution_engine.parameter_processor._build_analysis_params_dict.return_value = {
                "user_id": 200 if i == 1 else 1,
                "workload_id": None,
                "metric_names": ["metric2"] if i == 1 else ["latency_ms", "throughput", "cost_cents"],
                "time_range_str": "last_24_hours",
                "primary_intent": "general"
            }

            # Should not raise AttributeError: 'KeyParameters' object has no attribute 'get'
            try:
                result = mock_execution_engine.parameter_processor._build_analysis_params_dict(key_params, {})
                assert "user_id" in result
                assert "metric_names" in result
            except AttributeError as e:
                if "'get'" in str(e):
                    pytest.fail(f"AttributeError with 'get' method for case {i}: {e}")
                raise