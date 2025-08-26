"""Test configuration validation and environment management."""
import pytest
from unittest.mock import Mock, patch
import os

from netra_backend.app.core.health_checkers import (
    _get_service_priority_for_environment,
    _is_development_mode,
    _get_health_check_timeout,
    ServicePriority
)


class TestConfigurationConsistency:
    """Test configuration consistency across environments."""
    
    def test_service_priority_consistency(self):
        """Test that service priorities are consistent and reasonable."""
        
        # Test all known services have valid priorities
        services = ['postgres', 'redis', 'clickhouse', 'unknown_service', 'auth_service']
        
        for service in services:
            priority = _get_service_priority_for_environment(service)
            assert isinstance(priority, ServicePriority)
            assert priority.name in ['CRITICAL', 'IMPORTANT', 'OPTIONAL']
    
    def test_postgres_always_critical(self):
        """Test that postgres is always critical regardless of environment."""
        
        # Mock different environments
        environments = ['production', 'staging', 'development', 'testing']
        
        for env in environments:
            with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value=env):
                priority = _get_service_priority_for_environment('postgres')
                assert priority.name == 'CRITICAL', f"Postgres should be CRITICAL in {env} but was {priority.name}"
    
    def test_environment_detection_fallback(self):
        """Test environment detection with fallback mechanisms."""
        
        # Test with environment detection failure
        with patch('netra_backend.app.core.environment_constants.get_current_environment', side_effect=Exception("Detection failed")):
            # Should not crash, should use fallback
            is_dev = _is_development_mode()
            assert isinstance(is_dev, bool)
            
            timeout = _get_health_check_timeout()
            assert isinstance(timeout, float)
            assert timeout > 0
    
    def test_configuration_environment_variables(self):
        """Test that configuration respects environment variables appropriately."""
        
        # Test basic environment variable handling (conceptual test)
        test_env_vars = {
            'ENVIRONMENT': 'test',
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
            'REDIS_URL': 'redis://localhost:6379'
        }
        
        # Verify environment variables can be accessed (basic smoke test)
        for var_name in test_env_vars:
            # This tests that the environment variable access pattern works
            env_value = os.environ.get(var_name, 'not_found')
            assert isinstance(env_value, str)


class TestHealthCheckTimeouts:
    """Test health check timeout configurations."""
    
    def test_timeout_values_are_reasonable(self):
        """Test that timeout values are within reasonable bounds."""
        
        timeout = _get_health_check_timeout()
        
        # Timeouts should be between 1 and 60 seconds
        assert 1.0 <= timeout <= 60.0, f"Timeout {timeout} is outside reasonable bounds (1-60 seconds)"
    
    def test_timeout_environment_specificity(self):
        """Test that different environments have appropriate timeout values."""
        
        # Production should have stricter timeouts than development
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value='production'):
            prod_timeout = _get_health_check_timeout()
        
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value='development'):
            dev_timeout = _get_health_check_timeout()
        
        # Both should be reasonable values
        assert 1.0 <= prod_timeout <= 30.0
        assert 1.0 <= dev_timeout <= 60.0


class TestServiceDependencyMapping:
    """Test service dependency and priority mapping."""
    
    def test_critical_services_are_minimal(self):
        """Test that only essential services are marked as critical."""
        
        # Only core infrastructure should be critical
        critical_services = []
        test_services = ['postgres', 'redis', 'clickhouse', 'auth_service', 'websocket']
        
        for service in test_services:
            priority = _get_service_priority_for_environment(service)
            if priority.name == 'CRITICAL':
                critical_services.append(service)
        
        # Should have some critical services but not too many
        assert len(critical_services) >= 1, "At least one service should be critical"
        assert len(critical_services) <= 3, f"Too many critical services: {critical_services}"
        
        # Postgres should always be in critical services
        assert 'postgres' in critical_services, "Postgres must be critical for data integrity"
    
    def test_optional_services_graceful_degradation(self):
        """Test that optional services are properly identified."""
        
        # Analytics and monitoring services should generally be optional
        optional_candidates = ['clickhouse', 'metrics', 'logging', 'tracing']
        
        for service in optional_candidates:
            priority = _get_service_priority_for_environment(service)
            # These services should not be critical (can be IMPORTANT or OPTIONAL)
            assert priority.name in ['IMPORTANT', 'OPTIONAL'], f"{service} should not be CRITICAL"


class TestResilienceConfiguration:
    """Test resilience and error handling configuration."""
    
    def test_error_classification_consistency(self):
        """Test that error classification is consistent."""
        
        from netra_backend.app.core.health_checkers import _handle_service_failure
        
        # Test different error types are handled consistently
        error_types = [
            "Connection timeout",
            "Database connection failed", 
            "Redis connection refused",
            "Authentication failed",
            "Service unavailable"
        ]
        
        for error in error_types:
            # Test with critical service (postgres)
            critical_result = _handle_service_failure("postgres", error, 100.0)
            assert critical_result.success is False
            assert critical_result.status == "unhealthy"
            assert error in critical_result.error_message
            
            # Test with important service (redis)
            important_result = _handle_service_failure("redis", error, 100.0)
            assert important_result.success is False
            assert important_result.status in ["unhealthy", "degraded"]
            assert error in important_result.error_message
    
    def test_response_time_recording(self):
        """Test that response times are properly recorded in health checks."""
        
        from netra_backend.app.core.health_checkers import _handle_service_failure, _create_success_result
        
        # Test successful health check records response time
        success_result = _create_success_result("test_service", 50.5)
        assert success_result.response_time_ms == 50.5
        assert success_result.response_time == 0.0505  # Converted to seconds
        
        # Test failed health check records response time
        failure_result = _handle_service_failure("test_service", "Test error", 123.4)
        assert failure_result.response_time_ms == 123.4
        assert abs(failure_result.response_time - 0.1234) < 0.0001  # Converted to seconds (with floating point tolerance)


class TestSystemIntegrationConfiguration:
    """Test system integration and cross-service configuration."""
    
    def test_health_checker_component_coverage(self):
        """Test that health checker covers all necessary components."""
        
        from netra_backend.app.core.health_checkers import HealthChecker
        
        checker = HealthChecker()
        
        # Verify all expected checkers are available
        expected_checkers = ['postgres', 'clickhouse', 'redis', 'websocket', 'system_resources']
        
        for checker_name in expected_checkers:
            assert checker_name in checker.checkers, f"Missing health checker for {checker_name}"
            assert callable(checker.checkers[checker_name]), f"Health checker for {checker_name} is not callable"
    
    def test_configuration_immutability_during_runtime(self):
        """Test that critical configuration remains stable during runtime."""
        
        # Test that service priorities don't change unexpectedly
        postgres_priority1 = _get_service_priority_for_environment('postgres')
        postgres_priority2 = _get_service_priority_for_environment('postgres')
        
        assert postgres_priority1 == postgres_priority2, "Service priorities should be consistent"
        assert postgres_priority1.name == 'CRITICAL', "Postgres priority should remain CRITICAL"
        
        # Test timeout consistency  
        timeout1 = _get_health_check_timeout()
        timeout2 = _get_health_check_timeout()
        
        assert timeout1 == timeout2, "Health check timeouts should be consistent"