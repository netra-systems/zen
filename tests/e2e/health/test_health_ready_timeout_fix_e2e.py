"""
End-to-End tests for /health/ready endpoint timeout fix validation.

CRITICAL ISSUE CONTEXT:
Backend Service /health/ready endpoint timeout caused by 30s Redis timeout in WebSocket readiness validator.
Root cause: netra_backend/app/websocket_core/gcp_initialization_validator.py:139
E2E tests validate the complete flow from HTTP client to health endpoint.

BUSINESS VALUE:
- Segment: Platform/Internal
- Goal: Platform Stability & Deployment Reliability
- Impact: Prevents deployment failures due to health check timeouts
- Strategic: Ensures production readiness and high availability

SSOT COMPLIANCE:
- Uses SSotAsyncTestCase from test_framework.ssot.base_test_case
- Uses IsolatedEnvironment (no direct os.environ)
- Tests against REAL staging environment with actual HTTP requests
- Uses real authentication as per CLAUDE.md E2E requirements
- NO MOCKS - tests complete end-to-end flow

Tests initially FAIL proving the 30s timeout issue exists in staging.
After fix to 3s timeout, tests will PASS with fast health responses.
"""

import asyncio
import time
import pytest
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestHealthReadyTimeoutFixE2E(SSotAsyncTestCase):
    """
    End-to-end tests for /health/ready endpoint timeout fix validation.
    
    CRITICAL: Tests the complete HTTP request flow to validate that the Redis
    timeout fix resolves health endpoint timeouts in real staging environment.
    """
    
    def setup_method(self, method):
        """Set up E2E test environment with real staging configuration."""
        super().setup_method(method)
        
        # Set staging environment for E2E testing
        self.set_env_var('ENVIRONMENT', 'staging')
        self.set_env_var('TESTING', 'true')
        
        # Staging backend URL (real staging environment)
        self.backend_url = self.get_env_var('BACKEND_URL', 'https://staging-backend.netra.ai')
        if not self.backend_url:
            pytest.skip("BACKEND_URL not configured for E2E testing")
            
        # Health endpoint timing expectations
        self.health_timing_requirements = {
            'fast_response': 3.0,        # Optimal health response time
            'acceptable_response': 10.0,  # Maximum acceptable for health checks
            'timeout_threshold': 30.0,    # Current problematic threshold
        }
        
        # Initialize E2E auth helper for authenticated requests
        self.auth_helper = E2EAuthHelper()
        
        # HTTP client configuration for health endpoint testing
        self.http_timeout = httpx.Timeout(
            connect=10.0,
            read=45.0,     # Allow time to detect timeout issues
            write=10.0,
            pool=10.0
        )
        
        # Record E2E test setup
        self.record_metric("e2e_setup_time", time.time())
        self.record_metric("backend_url", self.backend_url)
        
    async def test_health_ready_endpoint_response_time_staging(self):
        """
        Test /health/ready endpoint response time against staging environment.
        
        CRITICAL TEST: This test FAILS initially because the 30s Redis timeout
        causes the staging health endpoint to timeout or respond very slowly.
        """
        health_url = urljoin(self.backend_url, '/health/ready')
        
        # Test direct health endpoint (no authentication required for health)
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            # Time the health check request
            start_time = time.time()
            
            try:
                response = await client.get(health_url)
                response_time = time.time() - start_time
                
                # Record response metrics
                self.record_metric("staging_health_response_time", response_time)
                self.record_metric("staging_health_status_code", response.status_code)
                self.record_metric("staging_health_response_size", len(response.content))
                
                try:
                    response_data = response.json()
                    self.record_metric("staging_health_response_data", response_data)
                except:
                    self.record_metric("staging_health_response_text", response.text)
                    
                # CRITICAL ASSERTION: This FAILS initially due to slow response
                assert response_time <= self.health_timing_requirements['acceptable_response'], (
                    f"Staging /health/ready endpoint took {response_time:.3f}s, "
                    f"exceeds acceptable threshold {self.health_timing_requirements['acceptable_response']}s. "
                    f"This proves the Redis timeout issue exists in staging."
                )
                
                # Health endpoint should return successful status
                assert response.status_code in [200, 207], (
                    f"Health endpoint returned status {response.status_code}, expected 200 or 207. "
                    f"Response: {response.text[:500]}"
                )
                
                # Optimal performance validation (will fail until fix)
                if response_time <= self.health_timing_requirements['fast_response']:
                    self.record_metric("staging_performance_optimal", True)
                else:
                    self.record_metric("staging_performance_suboptimal", True)
                    self.record_metric("staging_performance_degradation", 
                                     response_time / self.health_timing_requirements['fast_response'])
                    
            except httpx.TimeoutException as e:
                response_time = time.time() - start_time
                self.record_metric("staging_health_timeout", True)
                self.record_metric("staging_health_timeout_time", response_time)
                
                pytest.fail(
                    f"Staging /health/ready endpoint timed out after {response_time:.3f}s. "
                    f"This proves the Redis timeout issue is causing health endpoint failures. "
                    f"Timeout error: {str(e)}"
                )
                
    async def test_health_ready_endpoint_multiple_requests_staging(self):
        """
        Test /health/ready endpoint with multiple sequential requests to detect consistency issues.
        
        CRITICAL: Tests if Redis timeout causes inconsistent response times.
        """
        health_url = urljoin(self.backend_url, '/health/ready')
        request_count = 5
        response_times = []
        status_codes = []
        
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            for i in range(request_count):
                start_time = time.time()
                
                try:
                    response = await client.get(health_url)
                    response_time = time.time() - start_time
                    
                    response_times.append(response_time)
                    status_codes.append(response.status_code)
                    
                    # Small delay between requests
                    await asyncio.sleep(0.5)
                    
                except httpx.TimeoutException:
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    status_codes.append(0)  # Timeout
                    
        # Analyze multiple request performance
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        timeout_count = status_codes.count(0)
        success_count = len([s for s in status_codes if 200 <= s <= 299])
        
        # Record multiple request metrics
        self.record_metric("multi_request_count", request_count)
        self.record_metric("multi_request_avg_time", avg_response_time)
        self.record_metric("multi_request_max_time", max_response_time)
        self.record_metric("multi_request_min_time", min_response_time)
        self.record_metric("multi_request_timeout_count", timeout_count)
        self.record_metric("multi_request_success_count", success_count)
        self.record_metric("multi_request_response_times", response_times)
        self.record_metric("multi_request_status_codes", status_codes)
        
        # Validate multiple request performance
        assert timeout_count == 0, (
            f"Found {timeout_count} timeouts out of {request_count} requests. "
            f"Redis timeout issue is causing health endpoint failures."
        )
        
        assert avg_response_time <= self.health_timing_requirements['acceptable_response'], (
            f"Average response time {avg_response_time:.3f}s exceeds "
            f"acceptable threshold {self.health_timing_requirements['acceptable_response']}s "
            f"across {request_count} requests."
        )
        
        assert max_response_time <= self.health_timing_requirements['acceptable_response'] * 1.5, (
            f"Maximum response time {max_response_time:.3f}s is too high, "
            f"indicating inconsistent performance due to timeout issues."
        )
        
        # Success rate validation
        success_rate = success_count / request_count
        assert success_rate >= 0.9, (
            f"Success rate {success_rate:.1%} is too low ({success_count}/{request_count}). "
            f"Health endpoint should be consistently available."
        )
        
    async def test_health_ready_endpoint_concurrent_requests_staging(self):
        """
        Test /health/ready endpoint with concurrent requests against staging.
        
        CRITICAL: Tests if Redis timeout causes issues under concurrent load.
        """
        health_url = urljoin(self.backend_url, '/health/ready')
        concurrent_count = 3  # Conservative concurrency for staging
        
        async def single_request():
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                start_time = time.time()
                try:
                    response = await client.get(health_url)
                    return {
                        'response_time': time.time() - start_time,
                        'status_code': response.status_code,
                        'success': True
                    }
                except httpx.TimeoutException:
                    return {
                        'response_time': time.time() - start_time,
                        'status_code': 0,
                        'success': False
                    }
                    
        # Execute concurrent requests
        start_time = time.time()
        tasks = [single_request() for _ in range(concurrent_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze concurrent request results
        successful_results = []
        failed_results = []
        exceptions = []
        
        for result in results:
            if isinstance(result, Exception):
                exceptions.append(str(result))
            elif result['success']:
                successful_results.append(result)
            else:
                failed_results.append(result)
                
        # Calculate concurrent performance metrics
        if successful_results:
            response_times = [r['response_time'] for r in successful_results]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = 0
            max_response_time = 0
            
        # Record concurrent performance metrics
        self.record_metric("concurrent_total_time", total_time)
        self.record_metric("concurrent_count", concurrent_count)
        self.record_metric("concurrent_successful", len(successful_results))
        self.record_metric("concurrent_failed", len(failed_results))
        self.record_metric("concurrent_exceptions", len(exceptions))
        self.record_metric("concurrent_avg_response_time", avg_response_time)
        self.record_metric("concurrent_max_response_time", max_response_time)
        
        # Validate concurrent performance
        assert len(exceptions) == 0, (
            f"Found {len(exceptions)} exceptions during concurrent requests: {exceptions}"
        )
        
        assert len(failed_results) == 0, (
            f"Found {len(failed_results)} failed requests during concurrent load. "
            f"Redis timeout may be causing failures under load."
        )
        
        assert avg_response_time <= self.health_timing_requirements['acceptable_response'], (
            f"Concurrent average response time {avg_response_time:.3f}s exceeds "
            f"acceptable threshold {self.health_timing_requirements['acceptable_response']}s"
        )
        
        # Validate concurrent requests don't cause excessive slowdown
        concurrent_slowdown = max_response_time / avg_response_time if avg_response_time > 0 else 1
        max_concurrent_slowdown = 2.0  # Max response shouldn't be more than 2x average
        
        assert concurrent_slowdown <= max_concurrent_slowdown, (
            f"Concurrent request slowdown {concurrent_slowdown:.1f}x exceeds "
            f"maximum acceptable {max_concurrent_slowdown}x. This indicates "
            f"Redis timeout causing performance issues under load."
        )
        
    async def test_health_ready_endpoint_with_authentication_flow(self):
        """
        Test /health/ready endpoint within authenticated session flow.
        
        CRITICAL: Per CLAUDE.md, E2E tests must use authentication.
        Tests health endpoint in context of authenticated user session.
        """
        try:
            # Authenticate using E2E auth helper
            auth_context = await self.auth_helper.create_authenticated_context()
            
            # Record authentication metrics
            self.record_metric("auth_setup_time", auth_context.get('auth_time', 0))
            self.record_metric("auth_user_id", auth_context.get('user_id'))
            
        except Exception as e:
            pytest.skip(f"Authentication setup failed: {e}")
            
        health_url = urljoin(self.backend_url, '/health/ready')
        
        # Make authenticated request to health endpoint
        async with httpx.AsyncClient(
            timeout=self.http_timeout,
            headers=auth_context.get('headers', {})
        ) as client:
            
            start_time = time.time()
            
            try:
                response = await client.get(health_url)
                response_time = time.time() - start_time
                
                # Record authenticated request metrics
                self.record_metric("auth_health_response_time", response_time)
                self.record_metric("auth_health_status_code", response.status_code)
                
                # Validate authenticated health check performance
                assert response_time <= self.health_timing_requirements['acceptable_response'], (
                    f"Authenticated /health/ready request took {response_time:.3f}s, "
                    f"exceeds acceptable threshold {self.health_timing_requirements['acceptable_response']}s"
                )
                
                # Health endpoint should work with or without authentication
                assert response.status_code in [200, 207], (
                    f"Authenticated health request returned status {response.status_code}, "
                    f"expected 200 or 207"
                )
                
                # Authenticated request should not be slower than unauthenticated
                # (This validates auth doesn't add significant overhead to health checks)
                max_auth_overhead = 2.0  # Auth should add < 2s overhead
                assert response_time <= self.health_timing_requirements['fast_response'] + max_auth_overhead, (
                    f"Authenticated health request took {response_time:.3f}s, "
                    f"appears to have excessive authentication overhead"
                )
                
            except httpx.TimeoutException as e:
                response_time = time.time() - start_time
                
                pytest.fail(
                    f"Authenticated /health/ready request timed out after {response_time:.3f}s. "
                    f"This proves Redis timeout affects authenticated sessions."
                )
                
    async def test_health_ready_endpoint_during_simulated_load(self):
        """
        Test /health/ready endpoint during simulated application load.
        
        CRITICAL: Tests health endpoint performance when system is under load,
        validating that Redis timeout doesn't compound under realistic conditions.
        """
        health_url = urljoin(self.backend_url, '/health/ready')
        
        # Simulate background load by making some regular API requests
        background_load_count = 5
        health_check_count = 3
        
        async def background_load():
            """Simulate background API load."""
            api_endpoints = ['/health', '/health/live']  # Safe endpoints for load simulation
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                for _ in range(background_load_count):
                    for endpoint in api_endpoints:
                        try:
                            endpoint_url = urljoin(self.backend_url, endpoint)
                            await client.get(endpoint_url)
                            await asyncio.sleep(0.2)  # Brief delay between requests
                        except:
                            pass  # Ignore background load errors
                            
        async def health_check_during_load():
            """Perform health check during background load."""
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                start_time = time.time()
                try:
                    response = await client.get(health_url)
                    return {
                        'response_time': time.time() - start_time,
                        'status_code': response.status_code,
                        'success': True
                    }
                except httpx.TimeoutException:
                    return {
                        'response_time': time.time() - start_time,
                        'status_code': 0,
                        'success': False
                    }
                    
        # Start background load and health checks concurrently
        background_task = asyncio.create_task(background_load())
        
        # Wait a moment for background load to start
        await asyncio.sleep(1.0)
        
        # Perform health checks during load
        health_tasks = [health_check_during_load() for _ in range(health_check_count)]
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        # Wait for background load to complete
        await background_task
        
        # Analyze health performance during load
        successful_health_checks = []
        failed_health_checks = []
        
        for result in health_results:
            if isinstance(result, Exception):
                failed_health_checks.append(str(result))
            elif result['success']:
                successful_health_checks.append(result)
            else:
                failed_health_checks.append(result)
                
        # Calculate performance under load
        if successful_health_checks:
            response_times = [r['response_time'] for r in successful_health_checks]
            avg_load_response_time = sum(response_times) / len(response_times)
            max_load_response_time = max(response_times)
        else:
            avg_load_response_time = 0
            max_load_response_time = 0
            
        # Record load testing metrics
        self.record_metric("load_health_checks_attempted", health_check_count)
        self.record_metric("load_health_checks_successful", len(successful_health_checks))
        self.record_metric("load_health_checks_failed", len(failed_health_checks))
        self.record_metric("load_avg_response_time", avg_load_response_time)
        self.record_metric("load_max_response_time", max_load_response_time)
        
        # Validate health performance under load
        assert len(failed_health_checks) == 0, (
            f"Found {len(failed_health_checks)} failed health checks during load. "
            f"Redis timeout may be causing failures when system is busy."
        )
        
        assert avg_load_response_time <= self.health_timing_requirements['acceptable_response'], (
            f"Health checks during load averaged {avg_load_response_time:.3f}s, "
            f"exceeds acceptable threshold {self.health_timing_requirements['acceptable_response']}s"
        )
        
        # Health checks should remain responsive even under load
        max_load_degradation = 1.5  # Should not be more than 1.5x slower under load
        baseline_expected = self.health_timing_requirements['fast_response']
        
        assert avg_load_response_time <= baseline_expected * max_load_degradation, (
            f"Health checks under load ({avg_load_response_time:.3f}s) are "
            f"{avg_load_response_time/baseline_expected:.1f}x slower than baseline, "
            f"exceeds maximum acceptable degradation {max_load_degradation}x"
        )
        
    async def test_health_ready_endpoint_error_conditions(self):
        """
        Test /health/ready endpoint behavior under various error conditions.
        
        CRITICAL: Validates that even error conditions don't cause excessive delays
        due to Redis timeout configuration.
        """
        health_url = urljoin(self.backend_url, '/health/ready')
        
        # Test different error-inducing conditions
        error_test_scenarios = [
            {
                'name': 'malformed_request',
                'headers': {'Content-Type': 'invalid/type'},
                'expected_response_time': 5.0
            },
            {
                'name': 'custom_user_agent',
                'headers': {'User-Agent': 'LoadBalancer/HealthCheck'},
                'expected_response_time': 5.0
            },
        ]
        
        scenario_results = {}
        
        for scenario in error_test_scenarios:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                start_time = time.time()
                
                try:
                    response = await client.get(
                        health_url, 
                        headers=scenario.get('headers', {})
                    )
                    response_time = time.time() - start_time
                    
                    scenario_results[scenario['name']] = {
                        'response_time': response_time,
                        'status_code': response.status_code,
                        'success': True,
                        'timeout': False
                    }
                    
                except httpx.TimeoutException:
                    response_time = time.time() - start_time
                    scenario_results[scenario['name']] = {
                        'response_time': response_time,
                        'status_code': 0,
                        'success': False,
                        'timeout': True
                    }
                    
        # Record error condition test results
        self.record_metric("error_scenarios_results", scenario_results)
        
        # Validate error condition performance
        for scenario_name, result in scenario_results.items():
            scenario = next(s for s in error_test_scenarios if s['name'] == scenario_name)
            
            assert not result['timeout'], (
                f"Error scenario '{scenario_name}' timed out after {result['response_time']:.3f}s. "
                f"Even error conditions should not cause Redis timeout issues."
            )
            
            assert result['response_time'] <= scenario['expected_response_time'], (
                f"Error scenario '{scenario_name}' took {result['response_time']:.3f}s, "
                f"exceeds expected {scenario['expected_response_time']}s. "
                f"Error handling should not be delayed by Redis timeout."
            )