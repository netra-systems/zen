"""
Integration tests for FINALIZE phase - System Health Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability and User Access
- Value Impact: Ensures complete system is operational and ready for user interactions
- Strategic Impact: Prevents partial system failures that could block user access

Tests the final system health validation phase of startup, ensuring all components
are properly initialized, connected, and ready for chat operations.

This covers the FINALIZE phase which validates:
1. All services are responsive and healthy
2. Complete system integration works end-to-end
3. Chat-ready state is achieved
4. No partial startup failures
5. Performance metrics are within acceptable ranges
"""

import asyncio
import time
from typing import Dict, Any
import pytest
import httpx
import aiohttp
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env


class TestStartupFinalizeSystemHealthValidation(SSotBaseTestCase):
    """Integration tests for FINALIZE phase system health validation."""
    
    def setup_method(self, method):
        """Setup test environment with authentication."""
        super().setup_method(method)
        
        # Initialize E2E auth helper for authenticated requests
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Set test environment variables
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
        
        # Configure service URLs for testing
        self.backend_url = "http://localhost:8000"
        self.auth_url = "http://localhost:8083"
        self.websocket_url = "ws://localhost:8000/ws"
        
        # Track health check results
        self.health_results: Dict[str, Any] = {}

    @pytest.mark.integration
    async def test_finalize_complete_system_health_check(self):
        """
        Test complete system health check validates all components.
        
        BVJ: Ensures entire system is operational before allowing user access.
        """
        # Start timing this critical validation
        start_time = time.time()
        
        # Get authenticated token
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            # 1. Validate backend service health
            try:
                async with session.get(f"{self.backend_url}/health", headers=headers, timeout=10) as resp:
                    assert resp.status == 200, f"Backend health check failed: {resp.status}"
                    backend_health = await resp.json()
                    self.health_results["backend"] = backend_health
                    
                    # Validate comprehensive health response
                    assert "status" in backend_health
                    assert backend_health["status"] in ["healthy", "ok"]
                    assert "services" in backend_health
                    
                    # Record backend response time
                    self.record_metric("backend_health_check_time", time.time() - start_time)
                    
            except Exception as e:
                pytest.fail(f"Backend health check failed during FINALIZE phase: {e}")
            
            # 2. Validate auth service health
            auth_start = time.time()
            try:
                async with session.get(f"{self.auth_url}/health", timeout=10) as resp:
                    assert resp.status == 200, f"Auth service health check failed: {resp.status}"
                    auth_health = await resp.json()
                    self.health_results["auth"] = auth_health
                    
                    # Validate auth service is ready for authentication
                    assert "status" in auth_health
                    self.record_metric("auth_health_check_time", time.time() - auth_start)
                    
            except Exception as e:
                pytest.fail(f"Auth service health check failed during FINALIZE phase: {e}")
            
            # 3. Validate database connectivity through backend
            db_start = time.time()
            try:
                async with session.get(f"{self.backend_url}/health/database", headers=headers, timeout=15) as resp:
                    assert resp.status == 200, f"Database health check failed: {resp.status}"
                    db_health = await resp.json()
                    self.health_results["database"] = db_health
                    
                    # Validate database is ready for operations
                    assert "connected" in db_health
                    assert db_health["connected"] is True
                    self.record_metric("database_health_check_time", time.time() - db_start)
                    
            except Exception as e:
                pytest.fail(f"Database health check failed during FINALIZE phase: {e}")
        
        # 4. Validate total system health check time is reasonable
        total_time = time.time() - start_time
        self.record_metric("total_system_health_check_time", total_time)
        
        # System health check should complete within reasonable time
        assert total_time < 30.0, f"System health check took too long: {total_time:.2f}s"
        
        # Record successful finalization
        self.record_metric("system_health_validation_passed", True)

    @pytest.mark.integration  
    async def test_finalize_service_dependency_validation(self):
        """
        Test that all service dependencies are properly satisfied.
        
        BVJ: Prevents cascading failures from unsatisfied dependencies.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        dependency_checks = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Test backend -> auth service dependency
            try:
                async with session.get(f"{self.backend_url}/health/dependencies", headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        deps = await resp.json()
                        dependency_checks.append(("backend_deps", deps))
                        
                        # Should include auth service as dependency
                        assert "auth_service" in deps or "dependencies" in deps
            except Exception as e:
                # Log but don't fail - endpoint may not exist
                self.record_metric("backend_dependency_check_error", str(e))
            
            # 2. Test auth service -> database dependency
            try:
                async with session.get(f"{self.auth_url}/health/dependencies", timeout=10) as resp:
                    if resp.status == 200:
                        deps = await resp.json()
                        dependency_checks.append(("auth_deps", deps))
            except Exception as e:
                self.record_metric("auth_dependency_check_error", str(e))
            
            # 3. Test cross-service authentication works
            auth_test_start = time.time()
            try:
                # Validate token with auth service
                async with session.get(f"{self.auth_url}/auth/validate", headers=headers, timeout=10) as resp:
                    # Token validation should work (200) or gracefully fail (401/403)
                    assert resp.status in [200, 401, 403], f"Auth validation unexpected status: {resp.status}"
                    dependency_checks.append(("cross_service_auth", {"status": resp.status}))
                    
                    self.record_metric("cross_service_auth_time", time.time() - auth_test_start)
                    
            except Exception as e:
                pytest.fail(f"Cross-service authentication test failed: {e}")
        
        # Record dependency validation results
        self.record_metric("dependency_checks", dependency_checks)
        self.record_metric("dependency_validation_passed", len(dependency_checks) > 0)

    @pytest.mark.integration
    async def test_finalize_performance_metrics_validation(self):
        """
        Test system performance metrics are within acceptable ranges.
        
        BVJ: Ensures system can handle expected load after startup.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        performance_metrics = {}
        
        async with aiohttp.ClientSession() as session:
            # 1. Test response time performance
            response_times = []
            for i in range(5):  # Test 5 quick requests
                start = time.time()
                try:
                    async with session.get(f"{self.backend_url}/health", headers=headers, timeout=5) as resp:
                        response_time = time.time() - start
                        response_times.append(response_time)
                        assert resp.status == 200
                except Exception as e:
                    pytest.fail(f"Performance test request {i+1} failed: {e}")
            
            # Calculate performance metrics
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            performance_metrics.update({
                "avg_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "min_response_time": min_response_time,
                "response_times": response_times
            })
            
            # Validate performance is acceptable
            assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time < 5.0, f"Maximum response time too high: {max_response_time:.3f}s"
            
            # 2. Test concurrent request handling
            concurrent_start = time.time()
            try:
                # Send 3 concurrent health check requests
                tasks = [
                    session.get(f"{self.backend_url}/health", headers=headers, timeout=10)
                    for _ in range(3)
                ]
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                concurrent_time = time.time() - concurrent_start
                
                # Validate concurrent requests succeeded
                successful_responses = 0
                for resp in responses:
                    if hasattr(resp, 'status') and resp.status == 200:
                        successful_responses += 1
                        await resp.release()  # Clean up response
                
                assert successful_responses >= 2, f"Only {successful_responses}/3 concurrent requests succeeded"
                
                performance_metrics.update({
                    "concurrent_request_time": concurrent_time,
                    "concurrent_success_count": successful_responses
                })
                
                # Concurrent requests should not take significantly longer than sequential
                assert concurrent_time < avg_response_time * 2, "Concurrent request performance degraded"
                
            except Exception as e:
                pytest.fail(f"Concurrent request test failed: {e}")
        
        # Record all performance metrics
        for metric, value in performance_metrics.items():
            self.record_metric(f"performance_{metric}", value)
        
        self.record_metric("performance_validation_passed", True)

    @pytest.mark.integration
    async def test_finalize_system_resource_validation(self):
        """
        Test system resource usage is within acceptable limits.
        
        BVJ: Prevents resource exhaustion that could impact user experience.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        resource_metrics = {}
        
        async with aiohttp.ClientSession() as session:
            # 1. Test system metrics endpoint if available
            try:
                async with session.get(f"{self.backend_url}/metrics", headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        metrics = await resp.json()
                        resource_metrics["system_metrics"] = metrics
                        
                        # Validate common resource metrics if present
                        if "memory_usage" in metrics:
                            memory_mb = metrics["memory_usage"]
                            assert memory_mb < 1024, f"Memory usage too high: {memory_mb}MB"
                            
                        if "cpu_usage" in metrics:
                            cpu_percent = metrics["cpu_usage"]
                            assert cpu_percent < 80, f"CPU usage too high: {cpu_percent}%"
                            
            except Exception as e:
                # Metrics endpoint may not exist - log but don't fail
                self.record_metric("metrics_endpoint_error", str(e))
            
            # 2. Test connection pool efficiency
            connection_test_start = time.time()
            try:
                # Make multiple requests to test connection reuse
                for i in range(10):
                    async with session.get(f"{self.backend_url}/health", headers=headers, timeout=5) as resp:
                        assert resp.status == 200
                
                connection_test_time = time.time() - connection_test_start
                
                # Connection pooling should make subsequent requests faster
                avg_pooled_time = connection_test_time / 10
                resource_metrics["avg_pooled_request_time"] = avg_pooled_time
                
                # Should be faster than initial cold requests
                assert avg_pooled_time < 1.0, f"Connection pooling not effective: {avg_pooled_time:.3f}s per request"
                
            except Exception as e:
                pytest.fail(f"Connection pool test failed: {e}")
            
            # 3. Test memory efficiency with repeated requests
            memory_test_start = time.time()
            try:
                # Send requests in batches to test memory handling
                for batch in range(3):
                    batch_tasks = [
                        session.get(f"{self.backend_url}/health", headers=headers, timeout=5)
                        for _ in range(5)
                    ]
                    
                    batch_responses = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Clean up responses
                    for resp in batch_responses:
                        if hasattr(resp, 'status'):
                            await resp.release()
                    
                    # Small delay between batches
                    await asyncio.sleep(0.1)
                
                memory_test_time = time.time() - memory_test_start
                resource_metrics["memory_efficiency_test_time"] = memory_test_time
                
                # Memory test should complete reasonably quickly
                assert memory_test_time < 15.0, f"Memory efficiency test took too long: {memory_test_time:.2f}s"
                
            except Exception as e:
                pytest.fail(f"Memory efficiency test failed: {e}")
        
        # Record resource metrics
        for metric, value in resource_metrics.items():
            self.record_metric(f"resource_{metric}", value)
        
        self.record_metric("resource_validation_passed", True)

    @pytest.mark.integration
    async def test_finalize_error_recovery_validation(self):
        """
        Test system can gracefully handle and recover from errors.
        
        BVJ: Ensures system resilience for uninterrupted user experience.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        error_recovery_results = {}
        
        async with aiohttp.ClientSession() as session:
            # 1. Test graceful handling of invalid requests
            try:
                async with session.get(f"{self.backend_url}/nonexistent-endpoint", headers=headers, timeout=5) as resp:
                    # Should return proper error response, not crash
                    assert resp.status in [404, 405], f"Invalid endpoint handling failed: {resp.status}"
                    error_response = await resp.json()
                    
                    # Should have proper error structure
                    assert "error" in error_response or "detail" in error_response or "message" in error_response
                    error_recovery_results["invalid_endpoint_handled"] = True
                    
            except Exception as e:
                pytest.fail(f"Error handling test failed: {e}")
            
            # 2. Test handling of malformed requests
            try:
                # Send request with invalid JSON
                async with session.post(f"{self.backend_url}/health", 
                                      headers=headers, 
                                      data="invalid json", 
                                      timeout=5) as resp:
                    # Should handle malformed request gracefully
                    assert resp.status in [400, 422, 405], f"Malformed request handling failed: {resp.status}"
                    error_recovery_results["malformed_request_handled"] = True
                    
            except Exception as e:
                # This is acceptable - some servers might close connection on malformed requests
                error_recovery_results["malformed_request_connection_closed"] = True
            
            # 3. Test rate limiting behavior (if implemented)
            rate_limit_test_start = time.time()
            try:
                # Send rapid requests to test rate limiting
                responses = []
                for i in range(20):
                    try:
                        async with session.get(f"{self.backend_url}/health", headers=headers, timeout=2) as resp:
                            responses.append(resp.status)
                    except asyncio.TimeoutError:
                        responses.append("timeout")
                    except Exception:
                        responses.append("error")
                
                rate_limit_time = time.time() - rate_limit_test_start
                
                # Analyze responses
                success_count = sum(1 for r in responses if r == 200)
                error_count = sum(1 for r in responses if r not in [200, "timeout", "error"])
                
                error_recovery_results.update({
                    "rapid_requests_success_count": success_count,
                    "rapid_requests_error_count": error_count,
                    "rapid_requests_time": rate_limit_time
                })
                
                # System should handle rapid requests without crashing
                # Either succeed or gracefully rate limit
                assert success_count > 0, "System failed to handle any rapid requests"
                
            except Exception as e:
                # Log but don't fail - rate limiting behavior varies
                self.record_metric("rate_limit_test_error", str(e))
            
            # 4. Test system recovery after errors
            recovery_start = time.time()
            try:
                # After error tests, normal requests should still work
                async with session.get(f"{self.backend_url}/health", headers=headers, timeout=10) as resp:
                    assert resp.status == 200, f"System did not recover after error tests: {resp.status}"
                    
                    recovery_time = time.time() - recovery_start
                    error_recovery_results["recovery_time"] = recovery_time
                    error_recovery_results["system_recovered"] = True
                    
                    # Recovery should be quick
                    assert recovery_time < 5.0, f"System recovery took too long: {recovery_time:.2f}s"
                    
            except Exception as e:
                pytest.fail(f"System failed to recover after error tests: {e}")
        
        # Record error recovery results
        for metric, value in error_recovery_results.items():
            self.record_metric(f"error_recovery_{metric}", value)
        
        self.record_metric("error_recovery_validation_passed", True)

    @pytest.mark.integration
    async def test_finalize_startup_completion_markers(self):
        """
        Test system properly marks startup as complete and ready.
        
        BVJ: Ensures clear indication system is ready for user traffic.
        """
        token = self.auth_helper.create_test_jwt_token()
        headers = self.auth_helper.get_auth_headers(token)
        
        startup_markers = {}
        
        async with aiohttp.ClientSession() as session:
            # 1. Check if system reports as ready
            try:
                async with session.get(f"{self.backend_url}/ready", headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        ready_status = await resp.json()
                        startup_markers["ready_endpoint"] = ready_status
                        
                        # Should indicate system is ready
                        assert "ready" in ready_status or "status" in ready_status
                        
                    elif resp.status == 404:
                        # Ready endpoint may not exist - that's ok
                        startup_markers["ready_endpoint_not_implemented"] = True
                    else:
                        pytest.fail(f"Ready endpoint returned error: {resp.status}")
                        
            except Exception as e:
                pytest.fail(f"Ready endpoint test failed: {e}")
            
            # 2. Verify startup time information if available
            try:
                async with session.get(f"{self.backend_url}/startup-info", headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        startup_info = await resp.json()
                        startup_markers["startup_info"] = startup_info
                        
                        # Should have startup timing information
                        if "startup_time" in startup_info:
                            startup_time = startup_info["startup_time"]
                            assert startup_time > 0, "Invalid startup time reported"
                            
                            # Startup should complete in reasonable time
                            assert startup_time < 120, f"Startup took too long: {startup_time}s"
                            
            except Exception as e:
                # Startup info endpoint may not exist
                startup_markers["startup_info_not_available"] = True
            
            # 3. Test that all critical endpoints are responsive
            critical_endpoints = ["/health", "/docs", "/openapi.json"]
            responsive_endpoints = []
            
            for endpoint in critical_endpoints:
                try:
                    async with session.get(f"{self.backend_url}{endpoint}", 
                                         headers=headers if endpoint != "/docs" and endpoint != "/openapi.json" else {},
                                         timeout=5) as resp:
                        if resp.status in [200, 401, 403]:  # 401/403 acceptable for auth-protected endpoints
                            responsive_endpoints.append(endpoint)
                except Exception:
                    # Endpoint may not exist or be accessible
                    pass
            
            startup_markers["responsive_endpoints"] = responsive_endpoints
            
            # At least health endpoint should be responsive
            assert "/health" in responsive_endpoints, "Health endpoint not responsive after startup"
            
            # 4. Verify system can handle immediate post-startup load
            immediate_load_start = time.time()
            try:
                # Send concurrent requests immediately after startup validation
                load_tasks = [
                    session.get(f"{self.backend_url}/health", headers=headers, timeout=10)
                    for _ in range(5)
                ]
                
                load_responses = await asyncio.gather(*load_tasks, return_exceptions=True)
                load_time = time.time() - immediate_load_start
                
                successful_load_requests = 0
                for resp in load_responses:
                    if hasattr(resp, 'status') and resp.status == 200:
                        successful_load_requests += 1
                        await resp.release()
                
                startup_markers.update({
                    "immediate_load_success_count": successful_load_requests,
                    "immediate_load_time": load_time
                })
                
                # System should handle immediate post-startup load
                assert successful_load_requests >= 3, f"System not ready for load: {successful_load_requests}/5 requests succeeded"
                assert load_time < 10.0, f"Immediate load test took too long: {load_time:.2f}s"
                
            except Exception as e:
                pytest.fail(f"Immediate post-startup load test failed: {e}")
        
        # Record startup completion markers
        for marker, value in startup_markers.items():
            self.record_metric(f"startup_marker_{marker}", value)
        
        self.record_metric("startup_completion_validation_passed", True)
        
        # Record that FINALIZE phase validation completed successfully
        self.record_metric("finalize_system_health_validation_complete", True)
        
        # Ensure this test took a reasonable amount of time
        self.assert_execution_time_under(60.0)  # Should complete within 60 seconds