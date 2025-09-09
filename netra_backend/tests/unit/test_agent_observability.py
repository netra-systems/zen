"""
Unit Tests for Agent Observability

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable system monitoring and performance optimization  
- Value Impact: Observability data enables SLA monitoring and optimization decisions
- Strategic Impact: Platform reliability and performance optimization depend on metrics collection

These tests validate the business logic of agent observability without external dependencies.
Testing metrics collection, result creation, and logging coordination ensures proper monitoring.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.agent_observability import AgentObservabilityMixin
from netra_backend.app.schemas.agent_models import AgentExecutionMetrics
from netra_backend.app.schemas.agent_result_types import TypedAgentResult


class MockAgent(AgentObservabilityMixin):
    """Mock agent class for testing observability mixin."""
    
    def __init__(self, name: str = "test_agent"):
        self.name = name
        self.correlation_id = "test-correlation-123"
        self._subagent_logging_enabled = True
        self._execution_metrics = AgentExecutionMetrics(execution_time_ms=100.0)


class TestAgentObservability(SSotBaseTestCase):
    """Test agent observability functionality."""

    def setup_method(self, method=None):
        """Setup test method with mock agent."""
        super().setup_method(method)
        self.agent = MockAgent("test_optimizer_agent")

    @pytest.mark.unit
    def test_get_execution_metrics_default(self):
        """Test getting default execution metrics when none set.
        
        BVJ: Default metrics ensure observability data is always available.
        """
        # Create agent without preset metrics
        agent = MockAgent()
        del agent._execution_metrics  # Remove preset metrics
        
        metrics = agent.get_execution_metrics()
        
        # Verify default metrics structure
        assert isinstance(metrics, AgentExecutionMetrics)
        assert metrics.execution_time_ms == 0.0
        
        self.record_metric("default_metrics_available", True)

    @pytest.mark.unit
    def test_get_execution_metrics_existing(self):
        """Test getting existing execution metrics.
        
        BVJ: Existing metrics must be preserved for performance analysis.
        """
        test_execution_time = 250.5
        self.agent._execution_metrics = AgentExecutionMetrics(
            execution_time_ms=test_execution_time
        )
        
        metrics = self.agent.get_execution_metrics()
        
        assert isinstance(metrics, AgentExecutionMetrics)
        assert metrics.execution_time_ms == test_execution_time
        
        self.record_metric("existing_metrics_preserved", True)

    @pytest.mark.unit
    def test_create_failure_result_with_metrics(self):
        """Test failure result creation with proper timing calculation.
        
        BVJ: Failure results must include timing data for performance analysis.
        """
        start_time = time.time() - 0.5  # Simulate 500ms execution
        error_message = "Agent execution failed due to validation error"
        
        result = self.agent._create_failure_result(error_message, start_time)
        
        # Verify failure result structure
        assert isinstance(result, TypedAgentResult)
        assert result.success is False
        assert result.agent_name == self.agent.name
        assert result.error_message == error_message
        assert result.execution_time_ms > 0  # Should have positive timing
        assert result.execution_time_ms < 1000  # Should be reasonable (< 1s)
        assert result.metrics is not None
        
        self.record_metric("failure_result_timing_accurate", True)
        self.record_metric("failure_result_structured", True)

    @pytest.mark.unit
    def test_create_success_result_with_metrics(self):
        """Test success result creation with proper timing and data.
        
        BVJ: Success results must include performance data and business results.
        """
        start_time = time.time() - 0.3  # Simulate 300ms execution
        result_data = {"cost_savings": 15000, "optimizations": 5}
        
        result = self.agent._create_success_result(start_time, result_data)
        
        # Verify success result structure
        assert isinstance(result, TypedAgentResult)
        assert result.success is True
        assert result.agent_name == self.agent.name
        assert result.error_message is None
        assert result.result_data == result_data
        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 1000
        assert result.metrics is not None
        
        self.record_metric("success_result_timing_accurate", True)
        self.record_metric("success_result_data_preserved", True)

    @pytest.mark.unit
    @patch('netra_backend.app.agents.agent_observability.log_agent_communication')
    def test_log_agent_start_enabled(self, mock_log_comm):
        """Test agent start logging when logging is enabled.
        
        BVJ: Agent start events enable workflow tracking and debugging.
        """
        run_id = "run-456-789"
        
        self.agent._log_agent_start(run_id)
        
        # Verify logging call was made
        mock_log_comm.assert_called_once_with(
            "system", 
            self.agent.name, 
            self.agent.correlation_id, 
            "agent_start"
        )
        
        self.record_metric("agent_start_logged", True)

    @pytest.mark.unit
    @patch('netra_backend.app.agents.agent_observability.log_agent_communication')
    def test_log_agent_start_disabled(self, mock_log_comm):
        """Test agent start logging when logging is disabled.
        
        BVJ: Logging control enables performance optimization in production.
        """
        self.agent._subagent_logging_enabled = False
        run_id = "run-456-789"
        
        self.agent._log_agent_start(run_id)
        
        # Verify no logging call was made
        mock_log_comm.assert_not_called()
        
        self.record_metric("agent_start_logging_disabled", True)

    @pytest.mark.unit
    @patch('netra_backend.app.agents.agent_observability.log_agent_communication')
    def test_log_agent_completion_success(self, mock_log_comm):
        """Test agent completion logging for successful execution.
        
        BVJ: Completion events enable success rate monitoring and SLA tracking.
        """
        run_id = "run-789-012" 
        status = "success"
        
        self.agent._log_agent_completion(run_id, status)
        
        # Verify logging call was made with correct status
        mock_log_comm.assert_called_once_with(
            self.agent.name,
            "system", 
            self.agent.correlation_id, 
            "agent_success"
        )
        
        self.record_metric("agent_completion_success_logged", True)

    @pytest.mark.unit
    @patch('netra_backend.app.agents.agent_observability.log_agent_communication')
    def test_log_agent_completion_failure(self, mock_log_comm):
        """Test agent completion logging for failed execution.
        
        BVJ: Failure events enable error rate monitoring and alerting.
        """
        run_id = "run-012-345"
        status = "failure"
        
        self.agent._log_agent_completion(run_id, status)
        
        # Verify logging call was made with correct status
        mock_log_comm.assert_called_once_with(
            self.agent.name,
            "system", 
            self.agent.correlation_id, 
            "agent_failure"
        )
        
        self.record_metric("agent_completion_failure_logged", True)

    @pytest.mark.unit
    @patch('netra_backend.app.agents.agent_observability.log_agent_input')
    def test_log_input_from_agent_enabled(self, mock_log_input):
        """Test logging input from another agent.
        
        BVJ: Input logging enables data flow tracking and dependency analysis.
        """
        from_agent = "data_collector_agent"
        data = {"user_data": {"sessions": 50, "costs": 2500}}
        
        self.agent.log_input_from_agent(from_agent, data)
        
        # Verify logging call was made with calculated data size
        mock_log_input.assert_called_once()
        call_args = mock_log_input.call_args[0]
        assert call_args[0] == from_agent
        assert call_args[1] == self.agent.name
        assert call_args[2] > 0  # Data size should be positive
        assert call_args[3] == self.agent.correlation_id
        
        self.record_metric("agent_input_logged", True)

    @pytest.mark.unit
    @patch('netra_backend.app.agents.agent_observability.log_agent_output')
    def test_log_output_to_agent_success(self, mock_log_output):
        """Test logging output to another agent with success status.
        
        BVJ: Output logging enables data flow tracking and success monitoring.
        """
        to_agent = "report_generator_agent"
        data = {"recommendations": ["optimize instance types", "use reserved instances"]}
        status = "success"
        
        self.agent.log_output_to_agent(to_agent, data, status)
        
        # Verify logging call was made
        mock_log_output.assert_called_once()
        call_args = mock_log_output.call_args[0]
        assert call_args[0] == to_agent
        assert call_args[1] == self.agent.name
        assert call_args[2] > 0  # Data size should be positive
        assert call_args[3] == status
        assert call_args[4] == self.agent.correlation_id
        
        self.record_metric("agent_output_success_logged", True)

    @pytest.mark.unit
    def test_calculate_data_size_string(self):
        """Test data size calculation for string data.
        
        BVJ: Accurate data size tracking enables bandwidth and performance monitoring.
        """
        test_string = "This is a test message for size calculation"
        expected_size = len(test_string)
        
        size = self.agent._calculate_data_size(test_string)
        
        assert size == expected_size
        self.record_metric("string_data_size_accurate", True)

    @pytest.mark.unit
    def test_calculate_data_size_dict(self):
        """Test data size calculation for dictionary data.
        
        BVJ: Dictionary size tracking enables complex data monitoring.
        """
        test_dict = {"user_id": "12345", "cost_data": {"monthly": 1500, "daily": 50}}
        
        size = self.agent._calculate_data_size(test_dict)
        
        # Should be positive and reasonable
        assert size > 0
        assert size < 1000  # Should be reasonable for this small dict
        self.record_metric("dict_data_size_calculated", True)

    @pytest.mark.unit
    def test_calculate_data_size_list(self):
        """Test data size calculation for list data.
        
        BVJ: List size tracking enables array data monitoring.
        """
        test_list = ["optimization1", "optimization2", "optimization3"]
        
        size = self.agent._calculate_data_size(test_list)
        
        assert size > 0
        assert size < 1000
        self.record_metric("list_data_size_calculated", True)

    @pytest.mark.unit  
    def test_calculate_data_size_error_handling(self):
        """Test data size calculation with error handling for edge cases.
        
        BVJ: Robust size calculation prevents observability system failures.
        """
        # Create an object that might cause JSON serialization to fail
        class UnserializableObject:
            def __str__(self):
                raise Exception("Cannot convert to string")
        
        problematic_data = UnserializableObject()
        
        # Should not raise exception, should return 0
        size = self.agent._calculate_data_size(problematic_data)
        
        assert size == 0
        self.record_metric("data_size_error_handled", True)

    @pytest.mark.unit
    def test_logging_disabled_no_operations(self):
        """Test that no logging operations occur when disabled.
        
        BVJ: Logging control reduces overhead in performance-critical scenarios.
        """
        self.agent._subagent_logging_enabled = False
        
        with patch('netra_backend.app.agents.agent_observability.log_agent_input') as mock_input, \
             patch('netra_backend.app.agents.agent_observability.log_agent_output') as mock_output:
            
            self.agent.log_input_from_agent("other_agent", {"data": "test"})
            self.agent.log_output_to_agent("other_agent", {"result": "test"})
            
            # Verify no logging calls were made
            mock_input.assert_not_called()
            mock_output.assert_not_called()
        
        self.record_metric("logging_disabled_no_ops", True)

    def test_execution_timing_under_threshold(self):
        """Verify test execution performance meets requirements.
        
        BVJ: Fast unit tests enable rapid development cycles.
        """
        # Unit tests must execute under 100ms
        self.assert_execution_time_under(0.1)
        
        # Verify business metrics were recorded
        self.assert_metrics_recorded(
            "default_metrics_available",
            "existing_metrics_preserved",
            "failure_result_timing_accurate",
            "success_result_timing_accurate", 
            "agent_start_logged",
            "agent_completion_success_logged",
            "agent_input_logged",
            "string_data_size_accurate",
            "data_size_error_handled",
            "logging_disabled_no_ops"
        )