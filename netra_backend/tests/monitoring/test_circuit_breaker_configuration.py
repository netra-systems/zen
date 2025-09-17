"""
Test Circuit Breaker Configuration Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure circuit breakers protect system reliability
- Value Impact: Prevents cascade failures that could cost $100K+ ARR
- Strategic Impact: Core platform resilience

This test file validates proper configuration setup and compatibility for circuit breakers,
following the comprehensive test strategy for Issue #941.

Phase 2: Configuration Validation Tests
"""

import pytest
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitConfig,
    UnifiedCircuitBreaker,
    UnifiedCircuitBreakerManager,
    get_unified_circuit_breaker_manager
)


class TestUnifiedCircuitConfigValidation:
    """Test proper circuit breaker configuration."""

    def test_unified_config_creation_with_all_parameters(self):
        """Test creating UnifiedCircuitConfig with all valid parameters."""
        config = UnifiedCircuitConfig(
            name="test_service",
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=30,
            timeout_seconds=5.0,
            slow_call_threshold=2.0,
            adaptive_threshold=False,
            exponential_backoff=True,
            expected_exception=ConnectionError
        )
        assert config.name == "test_service"
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.recovery_timeout == 30
        assert config.timeout_seconds == 5.0
        assert config.slow_call_threshold == 2.0
        assert config.adaptive_threshold is False
        assert config.exponential_backoff is True
        assert config.expected_exception == ConnectionError

    def test_unified_config_defaults(self):
        """Test UnifiedCircuitConfig with default values."""
        config = UnifiedCircuitConfig(name="default_service")
        assert config.name == "default_service"
        assert config.failure_threshold == 5  # Default
        assert config.success_threshold == 2  # Default
        assert config.recovery_timeout == 60  # Default
        assert config.timeout_seconds == 30.0  # Default
        assert config.slow_call_threshold == 5.0  # Default
        assert config.adaptive_threshold is False  # Default
        assert config.exponential_backoff is True  # Default
        assert config.expected_exception is None  # Default

    def test_unified_config_minimal_parameters(self):
        """Test UnifiedCircuitConfig with minimal required parameters."""
        config = UnifiedCircuitConfig(name="minimal_service")
        assert config.name == "minimal_service"
        # All other parameters should have sensible defaults
        assert isinstance(config.failure_threshold, int)
        assert isinstance(config.recovery_timeout, int)
        assert isinstance(config.timeout_seconds, float)

    def test_invalid_config_parameters(self):
        """Test validation of invalid configuration parameters."""
        # Test negative failure_threshold
        with pytest.raises((ValueError, TypeError)):
            UnifiedCircuitConfig(name="invalid", failure_threshold=-1)

        # Test zero recovery_timeout
        with pytest.raises((ValueError, TypeError)):
            UnifiedCircuitConfig(name="invalid", recovery_timeout=0)

        # Test negative timeout_seconds
        with pytest.raises((ValueError, TypeError)):
            UnifiedCircuitConfig(name="invalid", timeout_seconds=-1.0)

        # Test zero success_threshold
        with pytest.raises((ValueError, TypeError)):
            UnifiedCircuitConfig(name="invalid", success_threshold=0)

    def test_circuit_breaker_creation_via_manager(self):
        """Test creating circuit breaker through manager."""
        config = UnifiedCircuitConfig(
            name="managed_service",
            failure_threshold=2,
            recovery_timeout=15
        )

        manager = get_unified_circuit_breaker_manager()
        breaker = manager.create_circuit_breaker("managed_service", config)

        assert breaker is not None
        assert isinstance(breaker, UnifiedCircuitBreaker)
        assert breaker.config.name == "managed_service"
        assert breaker.config.failure_threshold == 2
        assert breaker.config.recovery_timeout == 15

    def test_circuit_breaker_manager_get_or_create(self):
        """Test manager's get_breaker method creates circuit breaker with defaults."""
        manager = get_unified_circuit_breaker_manager()
        breaker = manager.get_breaker("auto_created_service")

        assert breaker is not None
        assert isinstance(breaker, UnifiedCircuitBreaker)
        # Should use default configuration
        assert breaker.config.failure_threshold == 5  # Default
        assert breaker.config.recovery_timeout == 60  # Default


class TestLegacyConfigurationHandling:
    """Test handling of legacy configuration formats for backward compatibility."""

    def test_legacy_config_conversion(self):
        """Test conversion from legacy config objects to UnifiedCircuitConfig."""
        from unittest.mock import MagicMock

        # Mock legacy configuration object
        legacy_config = MagicMock()
        legacy_config.failure_threshold = 3
        legacy_config.recovery_timeout = 45.0
        legacy_config.timeout_seconds = 10.0

        # Create UnifiedCircuitConfig with legacy data
        config = UnifiedCircuitConfig(
            name="legacy_service",
            failure_threshold=legacy_config.failure_threshold,
            recovery_timeout=int(legacy_config.recovery_timeout),
            timeout_seconds=legacy_config.timeout_seconds
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout == 45
        assert config.timeout_seconds == 10.0

    def test_legacy_config_with_missing_attributes(self):
        """Test handling legacy config objects with missing attributes."""
        from unittest.mock import MagicMock

        legacy_config = MagicMock()
        legacy_config.failure_threshold = 2
        # Missing recovery_timeout and timeout_seconds

        # Should use defaults for missing attributes
        config = UnifiedCircuitConfig(
            name="partial_legacy",
            failure_threshold=getattr(legacy_config, 'failure_threshold', 5),
            recovery_timeout=getattr(legacy_config, 'recovery_timeout', 60),
            timeout_seconds=getattr(legacy_config, 'timeout_seconds', 30.0)
        )

        assert config.failure_threshold == 2
        assert config.recovery_timeout == 60  # Default
        assert config.timeout_seconds == 30.0  # Default


class TestConfigurationValidation:
    """Test configuration validation and error handling."""

    def test_config_name_validation(self):
        """Test that configuration name is properly validated."""
        # Empty name should be handled
        config = UnifiedCircuitConfig(name="")
        assert config.name == ""  # Should accept empty string

        # None name should be handled
        with pytest.raises(TypeError):
            UnifiedCircuitConfig(name=None)

    def test_config_parameter_types(self):
        """Test that configuration parameters accept correct types."""
        config = UnifiedCircuitConfig(
            name="type_test",
            failure_threshold=3,  # int
            success_threshold=2,  # int
            recovery_timeout=30,  # int
            timeout_seconds=5.0,  # float
            slow_call_threshold=2.5,  # float
            adaptive_threshold=True,  # bool
            exponential_backoff=False  # bool
        )

        assert isinstance(config.failure_threshold, int)
        assert isinstance(config.success_threshold, int)
        assert isinstance(config.recovery_timeout, int)
        assert isinstance(config.timeout_seconds, float)
        assert isinstance(config.slow_call_threshold, float)
        assert isinstance(config.adaptive_threshold, bool)
        assert isinstance(config.exponential_backoff, bool)

    def test_config_boundary_values(self):
        """Test configuration with boundary values."""
        # Minimum valid values
        config_min = UnifiedCircuitConfig(
            name="boundary_min",
            failure_threshold=1,
            success_threshold=1,
            recovery_timeout=1,
            timeout_seconds=0.1
        )
        assert config_min.failure_threshold == 1
        assert config_min.success_threshold == 1
        assert config_min.recovery_timeout == 1
        assert config_min.timeout_seconds == 0.1

        # Maximum reasonable values
        config_max = UnifiedCircuitConfig(
            name="boundary_max",
            failure_threshold=100,
            success_threshold=50,
            recovery_timeout=3600,  # 1 hour
            timeout_seconds=300.0   # 5 minutes
        )
        assert config_max.failure_threshold == 100
        assert config_max.success_threshold == 50
        assert config_max.recovery_timeout == 3600
        assert config_max.timeout_seconds == 300.0


class TestManagerCircuitBreakerCreation:
    """Test circuit breaker creation through the manager interface."""

    def test_manager_singleton_behavior(self):
        """Test that get_unified_circuit_breaker_manager returns same instance."""
        manager1 = get_unified_circuit_breaker_manager()
        manager2 = get_unified_circuit_breaker_manager()
        assert manager1 is manager2

    def test_manager_creates_unique_breakers(self):
        """Test that manager creates unique circuit breakers for different names."""
        manager = get_unified_circuit_breaker_manager()

        config1 = UnifiedCircuitConfig(name="service1", failure_threshold=3)
        config2 = UnifiedCircuitConfig(name="service2", failure_threshold=5)

        breaker1 = manager.create_circuit_breaker("service1", config1)
        breaker2 = manager.create_circuit_breaker("service2", config2)

        assert breaker1 is not breaker2
        assert breaker1.config.name == "service1"
        assert breaker2.config.name == "service2"
        assert breaker1.config.failure_threshold == 3
        assert breaker2.config.failure_threshold == 5

    def test_manager_reuses_existing_breakers(self):
        """Test that manager can reuse existing circuit breakers."""
        manager = get_unified_circuit_breaker_manager()

        config = UnifiedCircuitConfig(name="reused_service", failure_threshold=2)

        # Create first breaker
        breaker1 = manager.create_circuit_breaker("reused_service", config)

        # Get the same breaker again
        breaker2 = manager.get_breaker("reused_service")

        # Should get the same instance
        assert breaker1 is breaker2

    def test_manager_create_breaker_method_compatibility(self):
        """Test backward compatibility of manager methods."""
        manager = get_unified_circuit_breaker_manager()

        config = UnifiedCircuitConfig(name="compat_test", failure_threshold=4)

        # Test create_breaker method
        breaker1 = manager.create_breaker("compat_test1", config)
        assert breaker1 is not None

        # Test create_circuit_breaker method (alias)
        breaker2 = manager.create_circuit_breaker("compat_test2", config)
        assert breaker2 is not None

        # Both should work and create valid breakers
        assert isinstance(breaker1, UnifiedCircuitBreaker)
        assert isinstance(breaker2, UnifiedCircuitBreaker)


class TestConfigurationErrorHandling:
    """Test error handling and edge cases in configuration."""

    def test_config_with_none_values(self):
        """Test configuration handling of None values."""
        # Test with expected_exception as None (should be acceptable)
        config = UnifiedCircuitConfig(
            name="none_test",
            expected_exception=None
        )
        assert config.expected_exception is None

    def test_config_string_conversion(self):
        """Test configuration string representation."""
        config = UnifiedCircuitConfig(
            name="string_test",
            failure_threshold=3,
            recovery_timeout=30
        )

        # Config should have string representation
        config_str = str(config)
        assert "string_test" in config_str
        assert isinstance(config_str, str)

    def test_circuit_breaker_initialization_with_config(self):
        """Test circuit breaker initialization with valid config."""
        config = UnifiedCircuitConfig(
            name="init_test",
            failure_threshold=2,
            recovery_timeout=15,
            timeout_seconds=10.0
        )

        breaker = UnifiedCircuitBreaker(config)

        assert breaker is not None
        assert breaker.config is config
        assert breaker.config.name == "init_test"
        assert breaker.config.failure_threshold == 2
        assert breaker.config.recovery_timeout == 15
        assert breaker.config.timeout_seconds == 10.0

        # Test initial state
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreakerState
        assert breaker.state == UnifiedCircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0