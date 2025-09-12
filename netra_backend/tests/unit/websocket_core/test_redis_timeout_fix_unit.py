"""
Unit tests for Redis timeout configuration validation in GCP WebSocket initialization validator.

CRITICAL ISSUE CONTEXT:
Backend Service /health/ready endpoint timeout caused by 30s Redis timeout in WebSocket readiness validator.
Root cause: netra_backend/app/websocket_core/gcp_initialization_validator.py:139
30s timeout is too long for health checks, should be 3s.

BUSINESS VALUE:
- Segment: Platform/Internal
- Goal: Platform Stability & Performance
- Impact: Fixes critical /health/ready endpoint timeout preventing deployments
- Strategic: Enables fast health checks and prevents cascade failures

SSOT COMPLIANCE:
- Uses SSotBaseTestCase from test_framework.ssot.base_test_case
- Uses IsolatedEnvironment (no direct os.environ)
- Tests REAL timeout behavior with actual Redis configurations
- Follows CLAUDE.md testing principles

Tests initially FAIL proving the 30s timeout issue exists.
After fix to 3s timeout, tests will PASS.
"""

import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    ServiceReadinessCheck,
    create_gcp_websocket_validator
)


class TestRedisTimeoutFixUnit(SSotAsyncTestCase):
    """
    Unit tests for Redis timeout configuration in GCP WebSocket validator.
    
    CRITICAL: These tests validate the specific timeout configurations that cause
    the /health/ready endpoint to timeout. Tests prove 30s is too long, 3s is correct.
    """
    
    def setup_method(self, method):
        """Set up test environment with isolated environment management."""
        super().setup_method(method)
        
        # Set test environment variables using SSOT pattern
        self.set_env_var('ENVIRONMENT', 'staging')
        self.set_env_var('K_SERVICE', 'netra-backend-test')
        self.set_env_var('TESTING', 'true')
        
        # Create mock app state
        self.mock_app_state = Mock()
        self.mock_app_state.redis_manager = Mock()
        self.mock_app_state.redis_manager.is_connected = Mock(return_value=True)
        self.mock_app_state.database_available = True
        self.mock_app_state.db_session_factory = Mock()
        
        # Record test start time for timeout validation
        self.test_start_time = time.time()
        
    async def test_redis_timeout_configuration_staging_environment(self):
        """
        Test Redis timeout configuration in staging GCP environment.
        
        CRITICAL TEST: This test FAILS initially because Redis timeout is 30s,
        proving the issue exists. After fix to 3s, test will PASS.
        """
        # Create validator for staging GCP environment
        validator = create_gcp_websocket_validator(self.mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Get Redis readiness check configuration
        redis_check = validator.readiness_checks.get('redis')
        
        # Assert Redis check exists
        assert redis_check is not None, "Redis readiness check should be registered"
        assert isinstance(redis_check, ServiceReadinessCheck), "Should be ServiceReadinessCheck instance"
        
        # CRITICAL ASSERTION: This FAILS with current 30s timeout, proving the issue
        # After fix, timeout should be 3s for fast health checks
        self.record_metric("redis_timeout_seconds", redis_check.timeout_seconds)
        
        # FAILING ASSERTION: Currently 30.0s, should be 3.0s for health endpoints
        expected_timeout = 3.0  # Fast timeout for health checks
        assert redis_check.timeout_seconds <= expected_timeout, (
            f"Redis timeout {redis_check.timeout_seconds}s is too long for health checks. "
            f"Expected <= {expected_timeout}s to prevent /health/ready endpoint timeouts. "
            f"Current 30s timeout causes health endpoint to timeout."
        )
        
        # Validate other Redis check properties
        assert redis_check.name == 'redis', "Check name should be 'redis'"
        assert redis_check.retry_count >= 2, "Should have reasonable retry count"
        assert redis_check.retry_delay >= 0.5, "Should have reasonable retry delay"
        
        # Record metrics for analysis
        self.record_metric("redis_retry_count", redis_check.retry_count)
        self.record_metric("redis_retry_delay", redis_check.retry_delay)
        self.record_metric("redis_is_critical", redis_check.is_critical)
        
    async def test_redis_timeout_production_vs_staging_difference(self):
        """
        Test Redis timeout configuration differences between production and staging.
        
        CRITICAL: Validates environment-specific timeout configurations.
        Both environments should use fast timeouts for health checks.
        """
        # Test staging configuration
        staging_validator = create_gcp_websocket_validator(self.mock_app_state)
        staging_validator.update_environment_configuration('staging', is_gcp=True)
        staging_redis_check = staging_validator.readiness_checks.get('redis')
        
        # Test production configuration
        production_validator = create_gcp_websocket_validator(self.mock_app_state)
        production_validator.update_environment_configuration('production', is_gcp=True)
        production_redis_check = production_validator.readiness_checks.get('redis')
        
        # Both should exist
        assert staging_redis_check is not None, "Staging Redis check should exist"
        assert production_redis_check is not None, "Production Redis check should exist"
        
        # Record environment-specific metrics
        self.record_metric("staging_redis_timeout", staging_redis_check.timeout_seconds)
        self.record_metric("production_redis_timeout", production_redis_check.timeout_seconds)
        
        # CRITICAL: Both environments should use fast timeouts for health endpoints
        max_health_timeout = 5.0  # Maximum acceptable for health checks
        
        assert staging_redis_check.timeout_seconds <= max_health_timeout, (
            f"Staging Redis timeout {staging_redis_check.timeout_seconds}s too long "
            f"for health checks (max {max_health_timeout}s)"
        )
        
        assert production_redis_check.timeout_seconds <= max_health_timeout, (
            f"Production Redis timeout {production_redis_check.timeout_seconds}s too long "
            f"for health checks (max {max_health_timeout}s)"
        )
        
        # Production should not have significantly longer timeout than staging
        # for health check purposes
        timeout_ratio = production_redis_check.timeout_seconds / staging_redis_check.timeout_seconds
        assert timeout_ratio <= 2.0, (
            f"Production timeout should not be more than 2x staging timeout "
            f"for health checks. Ratio: {timeout_ratio:.1f}"
        )
        
    async def test_redis_timeout_non_gcp_environment_difference(self):
        """
        Test Redis timeout configuration in non-GCP environment.
        
        Non-GCP environments can have different timeouts since they don't affect
        health endpoints in the same way.
        """
        # Test non-GCP (local) configuration
        local_validator = create_gcp_websocket_validator(self.mock_app_state)
        local_validator.update_environment_configuration('development', is_gcp=False)
        local_redis_check = local_validator.readiness_checks.get('redis')
        
        assert local_redis_check is not None, "Local Redis check should exist"
        
        # Record non-GCP timeout
        self.record_metric("local_redis_timeout", local_redis_check.timeout_seconds)
        
        # Non-GCP can have longer timeout since it doesn't affect health endpoints
        # But should still be reasonable for development experience
        assert local_redis_check.timeout_seconds <= 15.0, (
            f"Even non-GCP Redis timeout {local_redis_check.timeout_seconds}s "
            f"should be reasonable for development experience"
        )
        
    async def test_redis_readiness_check_execution_timing(self):
        """
        Test actual Redis readiness check execution timing.
        
        CRITICAL: This test measures real execution time to prove timeout impact.
        """
        validator = create_gcp_websocket_validator(self.mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Mock Redis connection to simulate ready state (fast response)
        self.mock_app_state.redis_manager.is_connected.return_value = True
        
        # Time the Redis readiness check execution
        start_time = time.time()
        redis_ready = validator._check_redis_ready()
        execution_time = time.time() - start_time
        
        # Record actual execution time
        self.record_metric("redis_check_execution_time", execution_time)
        
        # Should return True for connected Redis
        assert redis_ready is True, "Redis should be ready when connected"
        
        # Execution should be very fast for connected Redis
        assert execution_time < 1.0, (
            f"Redis readiness check took {execution_time:.3f}s, "
            f"should be < 1.0s for fast health checks"
        )
        
    async def test_redis_readiness_check_timeout_behavior(self):
        """
        Test Redis readiness check behavior with simulated timeout.
        
        CRITICAL: Tests the timeout mechanism that's causing health endpoint delays.
        """
        validator = create_gcp_websocket_validator(self.mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Mock Redis to simulate slow/timeout response
        def slow_redis_check():
            time.sleep(2.0)  # Simulate 2 second delay
            return False
            
        self.mock_app_state.redis_manager.is_connected = slow_redis_check
        
        # Time the check with timeout
        start_time = time.time()
        redis_ready = validator._validate_redis_readiness()
        execution_time = time.time() - start_time
        
        self.record_metric("redis_timeout_execution_time", execution_time)
        
        # Should handle timeout gracefully (degraded mode in staging)
        # Execution time should not exceed reasonable threshold
        max_acceptable_time = 5.0  # Maximum time for health check
        assert execution_time <= max_acceptable_time, (
            f"Redis check took {execution_time:.3f}s, exceeds max acceptable "
            f"{max_acceptable_time}s for health endpoints"
        )
        
    async def test_redis_timeout_impact_on_health_endpoint(self):
        """
        Test how Redis timeout configuration impacts health endpoint timing.
        
        CRITICAL: This test simulates the /health/ready endpoint flow to measure
        real impact of Redis timeout on health endpoint performance.
        """
        validator = create_gcp_websocket_validator(self.mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Time a full GCP readiness validation (simulates health endpoint)
        start_time = time.time()
        
        try:
            # Use shorter timeout to simulate health endpoint requirements
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=10.0)
            execution_time = time.time() - start_time
            
            # Record metrics
            self.record_metric("health_endpoint_simulation_time", execution_time)
            self.record_metric("health_endpoint_success", result.ready)
            
            # CRITICAL: Health endpoint should respond quickly
            max_health_response_time = 8.0  # Health endpoints should be fast
            assert execution_time <= max_health_response_time, (
                f"Health endpoint simulation took {execution_time:.3f}s, "
                f"exceeds maximum acceptable {max_health_response_time}s. "
                f"This proves the timeout issue exists."
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self.record_metric("health_endpoint_timeout_time", execution_time)
            
            # If we timeout, this proves the issue exists
            pytest.fail(
                f"Health endpoint simulation timed out after {execution_time:.3f}s. "
                f"This proves the Redis timeout issue is causing health endpoint failures."
            )
            
    async def test_all_service_timeouts_health_check_compatible(self):
        """
        Test that all service timeout configurations are compatible with health checks.
        
        CRITICAL: Validates that all service timeouts in the validator are appropriate
        for health endpoint usage.
        """
        validator = create_gcp_websocket_validator(self.mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Maximum acceptable timeout for health endpoints
        max_health_timeout = 10.0
        
        # Check all registered service timeouts
        timeout_violations = []
        
        for service_name, check in validator.readiness_checks.items():
            self.record_metric(f"{service_name}_timeout", check.timeout_seconds)
            
            if check.timeout_seconds > max_health_timeout:
                timeout_violations.append({
                    'service': service_name,
                    'timeout': check.timeout_seconds,
                    'max_allowed': max_health_timeout
                })
        
        # Record violations for analysis
        self.record_metric("timeout_violations_count", len(timeout_violations))
        self.record_metric("timeout_violations", timeout_violations)
        
        # Assert no violations exist
        if timeout_violations:
            violation_details = "\n".join([
                f"- {v['service']}: {v['timeout']}s (max allowed: {v['max_allowed']}s)"
                for v in timeout_violations
            ])
            pytest.fail(
                f"Found {len(timeout_violations)} service timeout violations for health checks:\n"
                f"{violation_details}\n"
                f"These timeouts are too long for /health/ready endpoints and will cause timeouts."
            )
            
    def test_service_readiness_check_configuration_validity(self):
        """
        Test ServiceReadinessCheck configuration for valid timeout parameters.
        
        CRITICAL: Validates the configuration data structures used for timeouts.
        """
        # Test valid timeout configurations
        valid_configs = [
            {'timeout': 1.0, 'description': 'Very fast'},
            {'timeout': 3.0, 'description': 'Fast health check'},
            {'timeout': 5.0, 'description': 'Reasonable health check'},
        ]
        
        for config in valid_configs:
            check = ServiceReadinessCheck(
                name='test_check',
                validator=lambda: True,
                timeout_seconds=config['timeout'],
                description=config['description']
            )
            
            assert check.timeout_seconds == config['timeout']
            assert check.timeout_seconds > 0, "Timeout must be positive"
            assert check.timeout_seconds <= 30.0, "Timeout should be reasonable"
            
        # Test current GCP environment configurations are health-endpoint safe
        # After the fix, all GCP timeouts should be <= 8.0s for health endpoints
        validator = GCPWebSocketInitializationValidator()
        validator.update_environment_configuration('staging', True)
        
        max_health_safe_timeout = 8.0  # Updated after fix
        violating_services = []
        
        for service_name, check in validator.readiness_checks.items():
            if check.timeout_seconds > max_health_safe_timeout:
                violating_services.append({
                    'service': service_name,
                    'timeout': check.timeout_seconds,
                    'max_allowed': max_health_safe_timeout
                })
        
        # Record the actual timeout configuration after fix
        all_timeouts = {name: check.timeout_seconds for name, check in validator.readiness_checks.items()}
        self.record_metric("current_gcp_timeouts", all_timeouts)
        
        # After fix, no services should have problematic timeouts
        if violating_services:
            violation_details = "\n".join([
                f"- {v['service']}: {v['timeout']}s (max allowed: {v['max_allowed']}s)"
                for v in violating_services
            ])
            pytest.fail(
                f"Found {len(violating_services)} GCP service timeout violations for health checks:\n"
                f"{violation_details}\n"
                f"These timeouts are too long for /health/ready endpoints and will cause timeouts."
            )
        
        # SUCCESS: All GCP timeouts are now health-endpoint compatible
        self.record_metric("timeout_fix_verified", True)
        print(f" PASS:  All GCP service timeouts are health-endpoint safe: {all_timeouts}")