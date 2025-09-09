"""
Unit Tests for Circuit Breaker Components

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent cascading failures and improve system reliability
- Value Impact: Circuit breakers prevent system-wide outages and improve user experience
- Strategic Impact: Platform reliability and uptime directly impact customer retention

These tests validate the business logic of circuit breaker components without external dependencies.
Testing failure thresholds, recovery mechanisms, and status reporting ensures reliable failure prevention.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.base.circuit_breaker_components import (
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerOpenException
)
from netra_backend.app.core.circuit_breaker import CircuitConfig


class TestCircuitBreakerConfig(SSotBaseTestCase):
    """Test circuit breaker configuration functionality."""

    @pytest.mark.unit
    def test_circuit_breaker_config_creation(self):
        """Test creation of circuit breaker configuration with defaults.
        
        BVJ: Proper configuration ensures consistent circuit breaker behavior.
        """
        name = "test_service_breaker"
        
        config = CircuitBreakerConfig(name=name)
        
        assert config.name == name
        assert config.failure_threshold == 5  # Default value
        assert config.recovery_timeout == 60  # Default value
        
        self.record_metric("config_defaults_applied", True)

    @pytest.mark.unit
    def test_circuit_breaker_config_custom_values(self):
        """Test creation of circuit breaker configuration with custom values.
        
        BVJ: Custom thresholds allow tuning for different service requirements.
        """
        name = "high_availability_service"
        failure_threshold = 3
        recovery_timeout = 30
        
        config = CircuitBreakerConfig(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        
        assert config.name == name
        assert config.failure_threshold == failure_threshold
        assert config.recovery_timeout == recovery_timeout
        
        self.record_metric("config_custom_values_set", True)

    @pytest.mark.unit
    def test_to_circuit_config_conversion(self):
        """Test conversion to canonical CircuitConfig format.
        
        BVJ: Configuration standardization ensures compatibility across components.
        """
        name = "conversion_test"
        failure_threshold = 7
        recovery_timeout = 45
        
        config = CircuitBreakerConfig(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        
        core_config = config.to_circuit_config()
        
        # Verify conversion to core format
        assert isinstance(core_config, CircuitConfig)
        assert core_config.name == name
        assert core_config.failure_threshold == failure_threshold
        assert core_config.recovery_timeout == float(recovery_timeout)
        assert core_config.timeout_seconds == float(recovery_timeout)
        
        self.record_metric("config_conversion_accurate", True)


class TestCircuitBreaker(SSotBaseTestCase):
    """Test circuit breaker functionality."""

    def setup_method(self, method=None):
        """Setup test method with circuit breaker."""
        super().setup_method(method)
        self.config = CircuitBreakerConfig(
            name="test_breaker",
            failure_threshold=3,
            recovery_timeout=30
        )
        self.breaker = CircuitBreaker(self.config)

    @pytest.mark.unit
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization with proper configuration.
        
        BVJ: Proper initialization ensures consistent circuit breaker behavior.
        """
        assert self.breaker.legacy_config == self.config
        assert self.breaker.metrics is not None
        assert self.breaker._last_state_change > 0
        
        self.record_metric("breaker_initialized_properly", True)

    @pytest.mark.unit
    async def test_execute_successful_function(self):
        """Test executing a successful function through the circuit breaker.
        
        BVJ: Successful executions must pass through without interference.
        """
        async def successful_function():
            return "success_result"
        
        result = await self.breaker.execute(successful_function)
        
        assert result == "success_result"
        self.record_metric("successful_execution_passed", True)

    @pytest.mark.unit
    async def test_execute_function_with_exception(self):
        """Test executing a function that raises an exception.
        
        BVJ: Exceptions must be properly tracked and propagated for failure counting.
        """
        async def failing_function():
            raise ValueError("Test failure")
        
        with self.expect_exception(ValueError, "Test failure"):
            await self.breaker.execute(failing_function)
        
        # Verify failure metrics were updated
        assert self.breaker.metrics.failed_calls >= 1
        assert self.breaker.metrics.total_calls >= 1
        assert self.breaker.metrics.last_failure_time > 0
        
        self.record_metric("failure_metrics_updated", True)

    @pytest.mark.unit
    def test_update_legacy_metrics_on_failure(self):
        """Test that legacy metrics are properly updated on failure.
        
        BVJ: Accurate failure tracking enables proper circuit breaker operation.
        """
        initial_failed_calls = self.breaker.metrics.failed_calls
        initial_total_calls = self.breaker.metrics.total_calls
        
        self.breaker._update_legacy_metrics_on_failure()
        
        assert self.breaker.metrics.failed_calls == initial_failed_calls + 1
        assert self.breaker.metrics.total_calls == initial_total_calls + 1
        assert self.breaker.metrics.last_failure_time > 0
        
        self.record_metric("legacy_metrics_updated", True)

    @pytest.mark.unit
    def test_get_status_basic_information(self):
        """Test getting circuit breaker status with basic information.
        
        BVJ: Status information enables monitoring and operational visibility.
        """
        status = self.breaker.get_status()
        
        # Verify basic status fields
        assert "name" in status
        assert "state" in status
        assert "failure_threshold" in status
        assert "recovery_timeout" in status
        assert "metrics" in status
        
        assert status["name"] == self.config.name
        assert status["failure_threshold"] == self.config.failure_threshold
        assert status["recovery_timeout"] == self.config.recovery_timeout
        
        self.record_metric("status_basic_info_present", True)

    @pytest.mark.unit
    def test_get_status_metrics_information(self):
        """Test getting circuit breaker status with metrics information.
        
        BVJ: Metrics data enables performance monitoring and optimization.
        """
        # Update some metrics first
        self.breaker._update_legacy_metrics_on_failure()
        
        status = self.breaker.get_status()
        metrics = status["metrics"]
        
        # Verify metrics fields
        assert "total_calls" in metrics
        assert "successful_calls" in metrics
        assert "failed_calls" in metrics
        assert "circuit_breaker_opens" in metrics
        assert "state_changes" in metrics
        assert "last_failure" in metrics
        
        assert metrics["failed_calls"] >= 1  # From the failure we triggered
        assert metrics["total_calls"] >= 1
        
        self.record_metric("status_metrics_present", True)

    @pytest.mark.unit
    def test_format_last_failure_time_with_failure(self):
        """Test formatting of last failure time when failures have occurred.
        
        BVJ: Proper time formatting enables operational troubleshooting.
        """
        # Trigger a failure to set failure time
        self.breaker._update_legacy_metrics_on_failure()
        
        formatted_time = self.breaker._format_last_failure_time()
        
        # Should return ISO format timestamp string
        assert formatted_time is not None
        assert isinstance(formatted_time, str)
        # Basic check for ISO format (contains T for time separator)
        assert "T" in formatted_time or formatted_time.count(":") >= 2
        
        self.record_metric("failure_time_formatted", True)

    @pytest.mark.unit
    def test_format_last_failure_time_no_failures(self):
        """Test formatting of last failure time when no failures occurred.
        
        BVJ: Clean state reporting when no failures have occurred.
        """
        # Ensure no failures have occurred
        self.breaker.metrics.last_failure_time = None
        
        formatted_time = self.breaker._format_last_failure_time()
        
        assert formatted_time is None
        self.record_metric("no_failure_time_none", True)

    @pytest.mark.unit
    def test_reset_circuit_breaker(self):
        """Test resetting circuit breaker to initial state.
        
        BVJ: Reset capability enables recovery from problematic states.
        """
        # Trigger some state changes
        self.breaker._update_legacy_metrics_on_failure()
        original_state_change_time = self.breaker._last_state_change
        
        # Reset the breaker
        self.breaker.reset()
        
        # Verify metrics were reset
        assert self.breaker.metrics.total_calls == 0
        assert self.breaker.metrics.successful_calls == 0
        assert self.breaker.metrics.failed_calls == 0
        assert self.breaker.metrics.circuit_breaker_opens == 0
        assert self.breaker.metrics.last_failure_time is None
        
        # Verify state change time was updated
        assert self.breaker._last_state_change > original_state_change_time
        
        self.record_metric("breaker_reset_successful", True)

    @pytest.mark.unit
    def test_build_basic_status_structure(self):
        """Test building basic status structure from core status.
        
        BVJ: Consistent status structure enables reliable monitoring integration.
        """
        # Mock core status
        core_status = {"state": "closed", "additional_info": "test"}
        
        basic_status = self.breaker._build_basic_status(core_status)
        
        expected_fields = ["name", "state", "failure_threshold", "recovery_timeout"]
        for field in expected_fields:
            assert field in basic_status
        
        assert basic_status["name"] == self.config.name
        assert basic_status["state"] == "closed"
        assert basic_status["failure_threshold"] == self.config.failure_threshold
        assert basic_status["recovery_timeout"] == self.config.recovery_timeout
        
        self.record_metric("basic_status_structure_correct", True)

    @pytest.mark.unit  
    def test_build_metrics_data_structure(self):
        """Test building metrics data structure from core status.
        
        BVJ: Structured metrics enable automated monitoring and alerting.
        """
        # Set up some metrics
        self.breaker.metrics.total_calls = 10
        self.breaker.metrics.successful_calls = 7
        self.breaker.metrics.failed_calls = 3
        self.breaker.metrics.circuit_breaker_opens = 1
        
        # Mock core status with nested metrics
        core_status = {
            "metrics": {
                "state_changes": 2
            }
        }
        
        metrics_data = self.breaker._build_metrics_data(core_status)
        
        # Verify all expected metrics fields
        expected_fields = [
            "total_calls", "successful_calls", "failed_calls",
            "circuit_breaker_opens", "state_changes", "last_failure"
        ]
        for field in expected_fields:
            assert field in metrics_data
        
        assert metrics_data["total_calls"] == 10
        assert metrics_data["successful_calls"] == 7
        assert metrics_data["failed_calls"] == 3
        assert metrics_data["circuit_breaker_opens"] == 1
        assert metrics_data["state_changes"] == 2
        
        self.record_metric("metrics_data_structure_correct", True)

    @pytest.mark.unit
    def test_circuit_breaker_open_exception(self):
        """Test CircuitBreakerOpenException functionality.
        
        BVJ: Proper exception handling enables graceful degradation.
        """
        exception_message = "Circuit breaker is open"
        
        exception = CircuitBreakerOpenException(exception_message)
        
        assert str(exception) == exception_message
        assert isinstance(exception, Exception)
        
        self.record_metric("open_exception_functional", True)

    @pytest.mark.unit
    def test_configuration_inheritance_compatibility(self):
        """Test that legacy configuration interface is maintained.
        
        BVJ: Backward compatibility ensures smooth migration of existing code.
        """
        # Verify that the circuit breaker properly stores legacy config
        assert hasattr(self.breaker, 'legacy_config')
        assert self.breaker.legacy_config.name == self.config.name
        assert self.breaker.legacy_config.failure_threshold == self.config.failure_threshold
        assert self.breaker.legacy_config.recovery_timeout == self.config.recovery_timeout
        
        self.record_metric("legacy_config_compatible", True)

    @pytest.mark.unit
    async def test_execute_method_calls_core_call(self):
        """Test that execute method properly delegates to core circuit breaker.
        
        BVJ: Proper delegation ensures circuit breaker functionality works correctly.
        """
        async def test_function():
            return "delegated_result"
        
        # The execute method should call the parent's call method
        with patch.object(self.breaker, 'call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "delegated_result"
            
            result = await self.breaker.execute(test_function)
            
            mock_call.assert_called_once_with(test_function)
            assert result == "delegated_result"
        
        self.record_metric("execute_delegates_properly", True)

    def test_execution_timing_under_threshold(self):
        """Verify test execution performance meets requirements.
        
        BVJ: Fast unit tests enable rapid development cycles.
        """
        # Unit tests must execute under 100ms
        self.assert_execution_time_under(0.1)
        
        # Verify business metrics were recorded
        self.assert_metrics_recorded(
            "config_defaults_applied",
            "config_custom_values_set",
            "config_conversion_accurate",
            "breaker_initialized_properly",
            "successful_execution_passed",
            "failure_metrics_updated",
            "legacy_metrics_updated",
            "status_basic_info_present",
            "status_metrics_present",
            "failure_time_formatted",
            "no_failure_time_none",
            "breaker_reset_successful",
            "basic_status_structure_correct",
            "metrics_data_structure_correct",
            "open_exception_functional",
            "legacy_config_compatible",
            "execute_delegates_properly"
        )