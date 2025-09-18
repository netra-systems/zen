"""
Circuit Breaker Configuration Validation Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability and Configuration Correctness
- Value Impact: Ensures circuit breaker configurations are valid and prevent system failures
- Strategic Impact: Protects $500K+ ARR by preventing misconfigured circuit breakers

This module tests circuit breaker configuration validation including:
- Valid configuration parameter validation
- Invalid parameter rejection
- Default configuration values
- Configuration edge cases
- Performance impact of configuration
"""

import pytest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerState
)


class CircuitBreakerConfigValidationTests(SSotBaseTestCase):
    """Unit tests for circuit breaker configuration validation."""

    def test_default_config_values(self):
        """Test that default configuration values are correct."""
        config = CircuitBreakerConfig()
        
        # Test default values match the implementation
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_threshold == 30.0
        assert config.recovery_timeout == 60.0
        assert config.half_open_max_requests == 5
        assert config.monitoring_window == 300.0
        assert config.failure_rate_threshold == 0.5
        assert config.minimum_requests == 10
        assert config.slow_call_threshold == 10.0
        assert config.slow_call_rate_threshold == 0.8
        assert config.enable_fallback is True
        assert config.fallback_cache_ttl == 300.0
        assert config.enable_graceful_degradation is True
        assert config.enable_metrics is True
        assert config.enable_alerts is True
        assert config.alert_on_state_change is True
        assert config.performance_tracking is True

    def test_valid_config_parameters(self):
        """Test that valid configuration parameters are accepted."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            timeout_threshold=60.0,
            recovery_timeout=120.0,
            half_open_max_requests=3,
            monitoring_window=600.0,
            failure_rate_threshold=0.7,
            minimum_requests=20,
            slow_call_threshold=15.0,
            slow_call_rate_threshold=0.9,
            enable_fallback=False,
            fallback_cache_ttl=600.0,
            enable_graceful_degradation=False,
            enable_metrics=False,
            enable_alerts=False,
            alert_on_state_change=False,
            performance_tracking=False
        )
        
        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.timeout_threshold == 60.0
        assert config.recovery_timeout == 120.0
        assert config.half_open_max_requests == 3
        assert config.monitoring_window == 600.0
        assert config.failure_rate_threshold == 0.7
        assert config.minimum_requests == 20
        assert config.slow_call_threshold == 15.0
        assert config.slow_call_rate_threshold == 0.9
        assert config.enable_fallback is False
        assert config.fallback_cache_ttl == 600.0
        assert config.enable_graceful_degradation is False
        assert config.enable_metrics is False
        assert config.enable_alerts is False
        assert config.alert_on_state_change is False
        assert config.performance_tracking is False

    def test_invalid_parameters_rejected(self):
        """Test that invalid parameters are properly rejected."""
        # Test that retry_after parameter is rejected (the main issue from task)
        with pytest.raises(TypeError, match="unexpected keyword argument 'retry_after'"):
            CircuitBreakerConfig(retry_after=60)
        
        # Test other invalid parameters
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            CircuitBreakerConfig(invalid_param=123)
        
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            CircuitBreakerConfig(retry_interval=30)

    def test_config_validation_with_circuit_breaker(self):
        """Test that configuration works correctly with CircuitBreaker."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            enable_metrics=True
        )
        
        breaker = CircuitBreaker("test_service", config)
        
        assert breaker.config.failure_threshold == 3
        assert breaker.config.recovery_timeout == 30.0
        assert breaker.config.enable_metrics is True
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_config_edge_cases(self):
        """Test configuration edge cases."""
        # Test minimum values
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            timeout_threshold=0.1,
            recovery_timeout=0.1,
            half_open_max_requests=1,
            monitoring_window=1.0,
            failure_rate_threshold=0.0,
            minimum_requests=1,
            slow_call_threshold=0.1,
            slow_call_rate_threshold=0.0,
            fallback_cache_ttl=1.0
        )
        
        assert config.failure_threshold == 1
        assert config.success_threshold == 1
        assert config.timeout_threshold == 0.1
        assert config.recovery_timeout == 0.1
        assert config.half_open_max_requests == 1
        assert config.monitoring_window == 1.0
        assert config.failure_rate_threshold == 0.0
        assert config.minimum_requests == 1
        assert config.slow_call_threshold == 0.1
        assert config.slow_call_rate_threshold == 0.0
        assert config.fallback_cache_ttl == 1.0

    def test_config_maximum_values(self):
        """Test configuration with maximum values."""
        config = CircuitBreakerConfig(
            failure_threshold=1000,
            success_threshold=1000,
            timeout_threshold=3600.0,
            recovery_timeout=3600.0,
            half_open_max_requests=100,
            monitoring_window=86400.0,
            failure_rate_threshold=1.0,
            minimum_requests=10000,
            slow_call_threshold=3600.0,
            slow_call_rate_threshold=1.0,
            fallback_cache_ttl=86400.0
        )
        
        assert config.failure_threshold == 1000
        assert config.success_threshold == 1000
        assert config.timeout_threshold == 3600.0
        assert config.recovery_timeout == 3600.0
        assert config.half_open_max_requests == 100
        assert config.monitoring_window == 86400.0
        assert config.failure_rate_threshold == 1.0
        assert config.minimum_requests == 10000
        assert config.slow_call_threshold == 3600.0
        assert config.slow_call_rate_threshold == 1.0
        assert config.fallback_cache_ttl == 86400.0

    def test_config_mutability(self):
        """Test that configuration can be modified after creation (dataclass is not frozen)."""
        config = CircuitBreakerConfig(failure_threshold=5)
        
        # Dataclass is not frozen, so modification should work
        config.failure_threshold = 10
        assert config.failure_threshold == 10

    def test_config_string_representation(self):
        """Test that configuration has meaningful string representation."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            enable_metrics=False
        )
        
        config_str = str(config)
        assert "failure_threshold=3" in config_str
        assert "enable_metrics=False" in config_str

    def test_config_equality(self):
        """Test configuration equality comparison."""
        config1 = CircuitBreakerConfig(failure_threshold=5, enable_metrics=True)
        config2 = CircuitBreakerConfig(failure_threshold=5, enable_metrics=True)
        config3 = CircuitBreakerConfig(failure_threshold=3, enable_metrics=True)
        
        assert config1 == config2
        assert config1 != config3

    def test_legacy_parameter_migration(self):
        """Test that old parameter names are not supported."""
        # These should all fail as they're not valid parameters
        invalid_params = [
            'retry_after',
            'retry_interval', 
            'circuit_timeout',
            'max_failures',
            'recovery_period',
            'open_timeout'
        ]
        
        for param in invalid_params:
            with pytest.raises(TypeError, match="unexpected keyword argument"):
                CircuitBreakerConfig(**{param: 60})