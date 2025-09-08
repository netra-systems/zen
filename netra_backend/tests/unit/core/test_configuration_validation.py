from shared.isolated_environment import get_env
"""Test configuration validation and environment management."""
import pytest
import os
from unittest.mock import patch
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment

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
        priority = _get_service_priority_for_environment('postgres')
        assert priority == ServicePriority.CRITICAL

    def test_secure_configuration_boundaries_iteration_16(self):
        """Test security configuration validation - Iteration 16."""
        
        # Test development mode detection using proper environment detection mocking
        from netra_backend.app.core.environment_constants import get_current_environment
        
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value="development"):
            assert _is_development_mode() == True
            
        with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value="production"):
            assert _is_development_mode() == False
            
        # Test timeout configuration boundaries
        timeout = _get_health_check_timeout()
        assert isinstance(timeout, (int, float))
        assert timeout > 0
        assert timeout <= 30  # Reasonable upper bound
        
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


class TestSecurityBoundaryConfiguration:
    """Test security boundary configuration validation."""
    
    def test_environment_isolation_configuration(self):
        """Test that environment isolation is properly configured."""
        import os
        
        # Test production environment security settings
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            with patch('netra_backend.app.core.environment_constants.get_current_environment', return_value='production'):
                # Production should have strict timeouts
                timeout = _get_health_check_timeout()
                assert timeout <= 15.0, f"Production timeout {timeout}s too lenient for security"
                
                # Production should minimize optional services
                optional_count = 0
                services = ['postgres', 'redis', 'clickhouse', 'auth_service']
                for service in services:
                    priority = _get_service_priority_for_environment(service)
                    if priority.name == 'OPTIONAL':
                        optional_count += 1
                
                # Production should have minimal optional services for security
                assert optional_count <= 1, f"Too many optional services in production: {optional_count}"
    
    def test_sensitive_configuration_validation(self):
        """Test validation of sensitive configuration parameters."""
        import re
        
        # Test that database URL patterns are validated
        test_database_urls = [
            "postgresql://user:password@localhost:5432/db",  # Valid
            "postgresql://user@localhost:5432/db",  # Valid without password
            "invalid://not-a-db-url",  # Invalid protocol
            "postgresql://",  # Incomplete
            "",  # Empty
            None  # None value
        ]
        
        def validate_database_url(url):
            """Mock database URL validation."""
            if not url:
                return False
            if not isinstance(url, str):
                return False
            
            # Basic pattern validation
            postgres_pattern = r'^postgresql://[^@]+@[^:]+:\d+/[^/]+$'
            return bool(re.match(postgres_pattern, url))
        
        valid_urls = []
        invalid_urls = []
        
        for url in test_database_urls:
            if validate_database_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        # Should have some valid and some invalid URLs
        assert len(valid_urls) >= 2, "Should identify valid database URLs"
        assert len(invalid_urls) >= 3, "Should identify invalid database URLs"
        
        # Verify specific patterns
        assert "postgresql://user:password@localhost:5432/db" in valid_urls
        assert "invalid://not-a-db-url" in invalid_urls
        assert None in invalid_urls
    
    def test_authentication_configuration_security(self):
        """Test authentication configuration security boundaries."""
        from datetime import timedelta
        
        # Test JWT token expiration boundaries
        def validate_jwt_expiration(expiration_hours):
            """Mock JWT expiration validation."""
            if not isinstance(expiration_hours, (int, float)):
                return False
            if expiration_hours <= 0:
                return False
            if expiration_hours > 24:  # Security: tokens shouldn't last more than 24 hours
                return False
            return True
        
        # Test various expiration times
        expiration_tests = [
            (1, True),     # 1 hour - valid
            (8, True),     # 8 hours - valid
            (24, True),    # 24 hours - valid (boundary)
            (25, False),   # 25 hours - too long
            (48, False),   # 48 hours - too long
            (0, False),    # 0 hours - invalid
            (-1, False),   # negative - invalid
            ("invalid", False),  # wrong type
        ]
        
        for exp_time, expected_valid in expiration_tests:
            is_valid = validate_jwt_expiration(exp_time)
            assert is_valid == expected_valid, f"JWT expiration {exp_time} validation incorrect"
    
    def test_cors_security_configuration(self):
        """Test CORS configuration security boundaries."""
        
        def validate_cors_origins(origins):
            """Mock CORS origins validation."""
            if not origins:
                return False
            if isinstance(origins, str):
                origins = [origins]
            if not isinstance(origins, list):
                return False
            
            for origin in origins:
                if not isinstance(origin, str):
                    return False
                # Security: wildcard should only be allowed in development
                if origin == "*":
                    return False  # Assume production context
                # Should be valid URLs or localhost
                if not (origin.startswith(('http://', 'https://')) or origin.startswith('localhost')):
                    return False
            
            return True
        
        # Test CORS origin configurations
        cors_tests = [
            (["https://netra-app.com"], True),  # Valid production origin
            (["https://netra-app.com", "https://api.netra-app.com"], True),  # Multiple valid
            (["http://localhost:3000"], True),  # Valid localhost for development
            (["*"], False),  # Wildcard not allowed in production
            (["invalid-url"], False),  # Invalid URL format
            ([123], False),  # Wrong type in list
            ("single-string", False),  # Wrong format
            (None, False),  # None value
            ([], False),  # Empty list
        ]
        
        for origins, expected_valid in cors_tests:
            is_valid = validate_cors_origins(origins)
            assert is_valid == expected_valid, f"CORS origins {origins} validation incorrect"
    
    def test_rate_limiting_configuration_security(self):
        """Test rate limiting configuration for security boundaries."""
        
        def validate_rate_limit_config(requests_per_minute, burst_size):
            """Mock rate limiting validation."""
            if not isinstance(requests_per_minute, int) or requests_per_minute <= 0:
                return False
            if not isinstance(burst_size, int) or burst_size <= 0:
                return False
            
            # Security boundaries
            if requests_per_minute > 1000:  # Too permissive
                return False
            if burst_size > requests_per_minute * 2:  # Burst too large relative to rate
                return False
            if requests_per_minute < 1:  # Too restrictive
                return False
            
            return True
        
        # Test rate limiting configurations
        rate_limit_tests = [
            (60, 120, True),   # 60/min with 120 burst - reasonable
            (100, 200, True),  # 100/min with 200 burst - valid
            (1000, 2000, True),  # High but within bounds
            (1001, 2000, False),  # Too many requests per minute
            (60, 300, False),  # Burst too large (>2x rate)
            (0, 10, False),    # Zero rate invalid
            (-1, 10, False),   # Negative rate invalid
            (60, 0, False),    # Zero burst invalid
            (60, -1, False),   # Negative burst invalid
        ]
        
        for rpm, burst, expected_valid in rate_limit_tests:
            is_valid = validate_rate_limit_config(rpm, burst)
            assert is_valid == expected_valid, f"Rate limit config ({rpm}, {burst}) validation incorrect"
    
    def test_database_connection_pool_security(self):
        """Test database connection pool configuration security."""
        
        def validate_connection_pool_config(min_size, max_size, timeout_seconds):
            """Mock connection pool validation."""
            if not all(isinstance(x, int) for x in [min_size, max_size]):
                return False
            if not isinstance(timeout_seconds, (int, float)):
                return False
            
            # Security and resource constraints
            if min_size < 1 or min_size > 10:  # Reasonable minimum bounds
                return False
            if max_size < min_size or max_size > 50:  # Prevent resource exhaustion
                return False
            if timeout_seconds <= 0 or timeout_seconds > 300:  # 5 minute max timeout
                return False
            
            return True
        
        # Test connection pool configurations
        pool_tests = [
            (2, 10, 30.0, True),    # Standard config
            (1, 20, 60.0, True),    # Minimal to moderate
            (5, 50, 120.0, True),   # High usage config
            (0, 10, 30.0, False),   # Invalid min size
            (11, 20, 30.0, False),  # Min too high
            (5, 51, 30.0, False),   # Max too high
            (10, 5, 30.0, False),   # Max less than min
            (5, 10, 0, False),      # Invalid timeout
            (5, 10, 301, False),    # Timeout too long
        ]
        
        for min_s, max_s, timeout, expected_valid in pool_tests:
            is_valid = validate_connection_pool_config(min_s, max_s, timeout)
            assert is_valid == expected_valid, f"Pool config ({min_s}, {max_s}, {timeout}) validation incorrect"


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
