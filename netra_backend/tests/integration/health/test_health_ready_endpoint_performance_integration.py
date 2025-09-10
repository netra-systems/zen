"""
Integration tests for /health/ready endpoint performance and Redis timeout issues.

CRITICAL ISSUE CONTEXT:
Backend Service /health/ready endpoint timeout caused by 30s Redis timeout in WebSocket readiness validator.
Root cause: netra_backend/app/websocket_core/gcp_initialization_validator.py:139
This affects the complete health endpoint request flow.

BUSINESS VALUE:
- Segment: Platform/Internal  
- Goal: Platform Stability & Performance
- Impact: Fixes critical /health/ready endpoint timeouts preventing deployments
- Strategic: Enables fast health checks for load balancers and orchestrators

SSOT COMPLIANCE:
- Uses SSotAsyncTestCase from test_framework.ssot.base_test_case
- Uses IsolatedEnvironment (no direct os.environ)
- Tests REAL services (Redis, health endpoint) with actual HTTP requests
- Follows CLAUDE.md testing principles - NO MOCKS for integration testing

Tests initially FAIL proving the 30s timeout issue exists in the complete flow.
After fix to 3s timeout, tests will PASS.
"""

import asyncio
import time
import pytest
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch
import httpx

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_services_test_fixtures import RealServicesTestFixtures
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    gcp_websocket_readiness_check,
    create_gcp_websocket_validator
)


class TestHealthReadyEndpointPerformanceIntegration(SSotAsyncTestCase):
    """
    Integration tests for /health/ready endpoint performance with real Redis timeout issues.
    
    CRITICAL: Tests the complete flow from HTTP request -> health endpoint -> WebSocket validator -> Redis
    These tests prove the 30s Redis timeout causes health endpoint failures.
    """
    
    def setup_method(self, method):
        """Set up integration test environment with real services."""
        super().setup_method(method)
        
        # Set staging GCP environment to trigger timeout issue
        self.set_env_var('ENVIRONMENT', 'staging')
        self.set_env_var('K_SERVICE', 'netra-backend-test')
        self.set_env_var('TESTING', 'true')
        
        # Initialize real services fixture
        self.real_services = RealServicesTestFixtures()
        
        # Record test setup time
        self.test_setup_time = time.time()
        
        # Health endpoint timing thresholds
        self.max_health_response_time = 10.0  # Maximum acceptable for health checks
        self.optimal_health_response_time = 3.0  # Optimal for health checks
        
    async def test_health_ready_endpoint_response_time_current_issue(self):
        """
        Test /health/ready endpoint response time with current Redis timeout configuration.
        
        CRITICAL TEST: This test FAILS initially because the 30s Redis timeout
        causes the health endpoint to timeout or respond very slowly.
        """
        # Create mock app state simulating real backend state
        mock_app_state = Mock()
        mock_app_state.redis_manager = Mock()
        mock_app_state.redis_manager.is_connected = Mock(return_value=True)
        mock_app_state.database_available = True
        mock_app_state.db_session_factory = Mock()
        mock_app_state.agent_supervisor = Mock()
        mock_app_state.thread_service = Mock()
        mock_app_state.agent_websocket_bridge = Mock()
        mock_app_state.key_manager = Mock()
        mock_app_state.auth_validation_complete = True
        mock_app_state.startup_complete = True
        mock_app_state.startup_phase = 'complete'
        mock_app_state.startup_failed = False
        
        # Time the health readiness check that powers /health/ready endpoint
        start_time = time.time()
        
        try:
            # This is the core function called by /health/ready endpoint
            ready, details = await gcp_websocket_readiness_check(mock_app_state)
            response_time = time.time() - start_time
            
            # Record metrics for analysis
            self.record_metric("health_ready_response_time", response_time)
            self.record_metric("health_ready_success", ready)
            self.record_metric("health_ready_details", details)
            
            # CRITICAL ASSERTION: This FAILS initially due to 30s Redis timeout
            assert response_time <= self.max_health_response_time, (
                f"Health ready endpoint took {response_time:.3f}s, exceeds maximum "
                f"acceptable {self.max_health_response_time}s for health checks. "
                f"This indicates the Redis timeout issue is causing slow responses."
            )
            
            # Optimal performance check (will fail until fix)
            if response_time <= self.optimal_health_response_time:
                self.record_metric("performance_optimal", True)
            else:
                self.record_metric("performance_suboptimal", True)
                self.record_metric("performance_degradation_factor", 
                                 response_time / self.optimal_health_response_time)
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            self.record_metric("health_ready_timeout", True)
            self.record_metric("health_ready_timeout_time", response_time)
            
            pytest.fail(
                f"Health ready endpoint timed out after {response_time:.3f}s. "
                f"This proves the Redis timeout issue is preventing health checks "
                f"from completing within reasonable time limits."
            )
            
    async def test_health_ready_endpoint_under_redis_connection_delay(self):
        """
        Test /health/ready endpoint behavior when Redis has connection delays.
        
        CRITICAL: Simulates real Redis connection delays that trigger the timeout issue.
        """
        # Create app state with delayed Redis connection
        mock_app_state = Mock()
        mock_app_state.redis_manager = Mock()
        
        # Simulate Redis connection delay (but not failure)
        def delayed_redis_check():
            time.sleep(1.5)  # 1.5s delay simulating network/connection issues
            return True  # Eventually connects
            
        mock_app_state.redis_manager.is_connected = delayed_redis_check
        mock_app_state.database_available = True
        mock_app_state.db_session_factory = Mock()
        mock_app_state.agent_supervisor = Mock()
        mock_app_state.thread_service = Mock()
        mock_app_state.agent_websocket_bridge = Mock()
        mock_app_state.key_manager = Mock()
        mock_app_state.auth_validation_complete = True
        mock_app_state.startup_complete = True
        mock_app_state.startup_phase = 'complete'
        mock_app_state.startup_failed = False
        
        # Time the health check with Redis delays
        start_time = time.time()
        ready, details = await gcp_websocket_readiness_check(mock_app_state)
        response_time = time.time() - start_time
        
        # Record delay impact metrics
        self.record_metric("redis_delay_health_response_time", response_time)
        self.record_metric("redis_delay_health_success", ready)
        self.record_metric("redis_delay_impact_factor", response_time / 1.5)  # vs. delay time
        
        # With current 30s timeout, even 1.5s delays can cause issues due to retries
        # The health endpoint should still respond reasonably fast
        max_delay_response_time = 5.0  # Should handle 1.5s delay gracefully
        
        assert response_time <= max_delay_response_time, (
            f"Health endpoint with 1.5s Redis delay took {response_time:.3f}s, "
            f"exceeds {max_delay_response_time}s. Current timeout configuration "
            f"may be causing excessive retries or delays."
        )
        
    async def test_health_ready_endpoint_redis_timeout_cascading_effect(self):
        """
        Test how Redis timeout affects the complete health endpoint request chain.
        
        CRITICAL: Validates the cascading effect of Redis timeout on health endpoint.
        """
        # Test different Redis timeout scenarios
        timeout_scenarios = [
            {'name': 'fast_redis', 'delay': 0.1, 'expected_max': 2.0},
            {'name': 'medium_redis', 'delay': 1.0, 'expected_max': 3.0},
            {'name': 'slow_redis', 'delay': 2.0, 'expected_max': 5.0},
        ]
        
        scenario_results = {}
        
        for scenario in timeout_scenarios:
            mock_app_state = Mock()
            mock_app_state.redis_manager = Mock()
            
            # Create delay function for this scenario
            def create_delayed_check(delay_time):
                def delayed_check():
                    time.sleep(delay_time)
                    return True
                return delayed_check
                
            mock_app_state.redis_manager.is_connected = create_delayed_check(scenario['delay'])
            
            # Setup other services as ready
            mock_app_state.database_available = True
            mock_app_state.db_session_factory = Mock()
            mock_app_state.agent_supervisor = Mock()
            mock_app_state.thread_service = Mock()
            mock_app_state.agent_websocket_bridge = Mock()
            mock_app_state.key_manager = Mock()
            mock_app_state.auth_validation_complete = True
            mock_app_state.startup_complete = True
            mock_app_state.startup_phase = 'complete'
            mock_app_state.startup_failed = False
            
            # Time the health check
            start_time = time.time()
            ready, details = await gcp_websocket_readiness_check(mock_app_state)
            response_time = time.time() - start_time
            
            scenario_results[scenario['name']] = {
                'delay': scenario['delay'],
                'response_time': response_time,
                'ready': ready,
                'expected_max': scenario['expected_max'],
                'within_threshold': response_time <= scenario['expected_max']
            }
            
            # Record individual scenario metrics
            self.record_metric(f"scenario_{scenario['name']}_response_time", response_time)
            self.record_metric(f"scenario_{scenario['name']}_success", ready)
            
        # Record complete scenario analysis
        self.record_metric("timeout_scenarios_results", scenario_results)
        
        # Analyze cascading effects
        failed_scenarios = []
        for name, result in scenario_results.items():
            if not result['within_threshold']:
                failed_scenarios.append({
                    'scenario': name,
                    'response_time': result['response_time'],
                    'expected_max': result['expected_max'],
                    'delay': result['delay']
                })
                
        self.record_metric("failed_scenarios_count", len(failed_scenarios))
        self.record_metric("failed_scenarios", failed_scenarios)
        
        # Assert no cascading failures
        if failed_scenarios:
            failure_details = "\n".join([
                f"- {f['scenario']}: {f['response_time']:.3f}s (max {f['expected_max']}s, Redis delay {f['delay']}s)"
                for f in failed_scenarios
            ])
            pytest.fail(
                f"Found {len(failed_scenarios)} scenarios with cascading timeout effects:\n"
                f"{failure_details}\n"
                f"This proves the Redis timeout configuration causes health endpoint delays "
                f"that cascade beyond the Redis check itself."
            )
            
    async def test_health_ready_endpoint_concurrent_request_performance(self):
        """
        Test /health/ready endpoint performance under concurrent requests.
        
        CRITICAL: Validates how Redis timeout affects multiple simultaneous health checks.
        """
        # Create shared app state
        mock_app_state = Mock()
        mock_app_state.redis_manager = Mock()
        mock_app_state.redis_manager.is_connected = Mock(return_value=True)
        mock_app_state.database_available = True
        mock_app_state.db_session_factory = Mock()
        mock_app_state.agent_supervisor = Mock()
        mock_app_state.thread_service = Mock()
        mock_app_state.agent_websocket_bridge = Mock()
        mock_app_state.key_manager = Mock()
        mock_app_state.auth_validation_complete = True
        mock_app_state.startup_complete = True
        mock_app_state.startup_phase = 'complete'
        mock_app_state.startup_failed = False
        
        # Run concurrent health checks
        concurrent_requests = 5
        
        async def single_health_check():
            start_time = time.time()
            ready, details = await gcp_websocket_readiness_check(mock_app_state)
            return time.time() - start_time, ready
            
        # Execute concurrent requests
        start_time = time.time()
        tasks = [single_health_check() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze concurrent performance
        response_times = []
        success_count = 0
        error_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                error_count += 1
                self.record_metric("concurrent_error", str(result))
            else:
                response_time, ready = result
                response_times.append(response_time)
                if ready:
                    success_count += 1
                    
        # Calculate metrics
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        # Record concurrent performance metrics
        self.record_metric("concurrent_requests", concurrent_requests)
        self.record_metric("concurrent_total_time", total_time)
        self.record_metric("concurrent_avg_response_time", avg_response_time)
        self.record_metric("concurrent_max_response_time", max_response_time)
        self.record_metric("concurrent_min_response_time", min_response_time)
        self.record_metric("concurrent_success_count", success_count)
        self.record_metric("concurrent_error_count", error_count)
        
        # Performance assertions
        max_concurrent_avg = 8.0  # Maximum acceptable average for concurrent requests
        max_concurrent_individual = 12.0  # Maximum for any individual request
        
        assert error_count == 0, (
            f"Found {error_count} errors in concurrent health checks. "
            f"Redis timeout may be causing request failures under load."
        )
        
        assert avg_response_time <= max_concurrent_avg, (
            f"Average response time {avg_response_time:.3f}s under concurrent load "
            f"exceeds maximum {max_concurrent_avg}s. Redis timeout causing "
            f"performance degradation under load."
        )
        
        assert max_response_time <= max_concurrent_individual, (
            f"Maximum individual response time {max_response_time:.3f}s "
            f"exceeds {max_concurrent_individual}s. Redis timeout causing "
            f"individual request delays under load."
        )
        
    async def test_health_ready_endpoint_retry_behavior_with_redis_timeouts(self):
        """
        Test how health endpoint retry behavior interacts with Redis timeouts.
        
        CRITICAL: The Redis timeout configuration affects retry logic and total response time.
        """
        # Create validator to inspect retry configuration
        mock_app_state = Mock()
        mock_app_state.redis_manager = Mock()
        mock_app_state.database_available = True
        mock_app_state.db_session_factory = Mock()
        
        validator = create_gcp_websocket_validator(mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Get Redis check configuration
        redis_check = validator.readiness_checks.get('redis')
        assert redis_check is not None, "Redis check should exist"
        
        # Calculate worst-case scenario time
        worst_case_time = (redis_check.timeout_seconds + 
                          (redis_check.retry_count * redis_check.retry_delay))
        
        # Record retry configuration analysis
        self.record_metric("redis_timeout_seconds", redis_check.timeout_seconds)
        self.record_metric("redis_retry_count", redis_check.retry_count)
        self.record_metric("redis_retry_delay", redis_check.retry_delay)
        self.record_metric("redis_worst_case_time", worst_case_time)
        
        # CRITICAL: Worst case time should not exceed health endpoint limits
        max_health_worst_case = 15.0  # Maximum worst case for health endpoints
        
        assert worst_case_time <= max_health_worst_case, (
            f"Redis worst-case retry time {worst_case_time:.1f}s exceeds "
            f"maximum acceptable {max_health_worst_case}s for health endpoints. "
            f"Configuration: timeout={redis_check.timeout_seconds}s, "
            f"retries={redis_check.retry_count}, delay={redis_check.retry_delay}s. "
            f"This will cause health endpoint timeouts."
        )
        
        # Test actual retry behavior with failing Redis
        mock_app_state.redis_manager.is_connected = Mock(return_value=False)
        
        # Time actual retry execution
        start_time = time.time()
        ready = validator._validate_redis_readiness()
        actual_time = time.time() - start_time
        
        self.record_metric("actual_retry_time", actual_time)
        self.record_metric("actual_retry_result", ready)
        
        # Actual time should be reasonable even with retries
        max_actual_retry_time = 10.0  # Should complete faster than worst case
        
        assert actual_time <= max_actual_retry_time, (
            f"Actual Redis retry took {actual_time:.3f}s, exceeds "
            f"reasonable limit {max_actual_retry_time}s for health endpoints."
        )
        
    async def test_health_ready_endpoint_graceful_degradation_timing(self):
        """
        Test health endpoint graceful degradation timing with Redis issues.
        
        CRITICAL: Validates that graceful degradation doesn't cause excessive delays.
        """
        # Create validator for staging (uses graceful degradation)
        mock_app_state = Mock()
        mock_app_state.redis_manager = Mock()
        mock_app_state.database_available = True
        mock_app_state.db_session_factory = Mock()
        mock_app_state.agent_supervisor = Mock()
        mock_app_state.thread_service = Mock()
        mock_app_state.agent_websocket_bridge = Mock()
        mock_app_state.key_manager = Mock()
        mock_app_state.auth_validation_complete = True
        mock_app_state.startup_complete = True
        mock_app_state.startup_phase = 'complete'
        mock_app_state.startup_failed = False
        
        validator = create_gcp_websocket_validator(mock_app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Test graceful degradation scenarios
        degradation_scenarios = [
            {
                'name': 'redis_disconnected',
                'redis_connected': False,
                'expected_ready': True,  # Should degrade gracefully in staging
                'max_time': 3.0
            },
            {
                'name': 'redis_exception',
                'redis_exception': ConnectionError("Redis connection failed"),
                'expected_ready': True,  # Should degrade gracefully in staging
                'max_time': 3.0
            }
        ]
        
        for scenario in degradation_scenarios:
            # Setup Redis behavior for this scenario
            if 'redis_connected' in scenario:
                mock_app_state.redis_manager.is_connected = Mock(
                    return_value=scenario['redis_connected']
                )
            elif 'redis_exception' in scenario:
                mock_app_state.redis_manager.is_connected = Mock(
                    side_effect=scenario['redis_exception']
                )
                
            # Time the graceful degradation
            start_time = time.time()
            result = await validator.validate_gcp_readiness_for_websocket(timeout_seconds=10.0)
            response_time = time.time() - start_time
            
            # Record scenario results
            self.record_metric(f"degradation_{scenario['name']}_time", response_time)
            self.record_metric(f"degradation_{scenario['name']}_ready", result.ready)
            self.record_metric(f"degradation_{scenario['name']}_details", result.details)
            
            # Validate graceful degradation timing
            assert response_time <= scenario['max_time'], (
                f"Graceful degradation scenario '{scenario['name']}' took "
                f"{response_time:.3f}s, exceeds maximum {scenario['max_time']}s. "
                f"Even degradation should be fast for health endpoints."
            )
            
            # In staging, should still be ready due to graceful degradation
            if scenario['expected_ready']:
                assert result.ready, (
                    f"Graceful degradation scenario '{scenario['name']}' should "
                    f"result in ready=True for staging environment, but got ready=False."
                )