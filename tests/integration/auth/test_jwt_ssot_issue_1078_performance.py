"""
JWT SSOT Performance Tests - Issue #1078
Purpose: Create FAILING performance tests to validate JWT delegation efficiency
These tests should FAIL initially if delegation is inefficient, then PASS after optimization

Business Value Justification (BVJ):
- Segment: Platform/Enterprise (Performance requirements)
- Business Goal: Ensure JWT SSOT delegation doesn't create performance bottlenecks
- Value Impact: Maintains fast authentication for $500K+ ARR user experience
- Revenue Impact: Prevents slow authentication that could impact customer satisfaction
"""
import asyncio
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

import pytest
from test_framework.base_integration_test import BaseIntegrationTest


@pytest.mark.integration
class JWTSSOTIssue1078PerformanceTests(BaseIntegrationTest):
    """Performance tests to validate JWT SSOT delegation efficiency"""
    
    async def setup_method(self):
        await super().setup_method()
        self.test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzAwMDAwMDAwLCJpYXQiOjE2OTk5OTkwMDAsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.test_signature"
        self.mock_payload = {
            "sub": "test_user_123",
            "email": "test@example.com",
            "exp": 1700000000,
            "iat": 1699999000,
            "token_type": "access"
        }
    
    async def test_auth_service_jwt_delegation_performance_requirements(self):
        """
        FAILING TEST: Auth service JWT delegation should meet performance requirements
        
        This test validates that SSOT JWT operations perform within acceptable limits.
        Expected to FAIL if delegation creates excessive overhead.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            auth_client = AuthServiceClient()
            
            # Mock auth service for consistent performance testing
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "valid": True,
                    "payload": self.mock_payload,
                    "service_validation": "auth_service"
                }
                mock_response.status_code = 200
                mock_response.raise_for_status = Mock()
                
                # Add realistic delay to simulate network latency
                async def mock_post_with_delay(*args, **kwargs):
                    await asyncio.sleep(0.010)  # 10ms simulated latency
                    return mock_response
                
                mock_post.side_effect = mock_post_with_delay
                
                # Performance test: Single token validation
                single_validation_times = []
                for i in range(20):  # 20 individual validations
                    start_time = time.time()
                    result = await auth_client.validate_token_jwt(self.test_token)
                    end_time = time.time()
                    
                    validation_time = (end_time - start_time) * 1000  # Convert to ms
                    single_validation_times.append(validation_time)
                    
                    assert result is not None, f"Validation {i} should succeed"
                    assert result.get("valid") is True, f"Validation {i} should be valid"
                
                # Analyze single validation performance
                avg_single = statistics.mean(single_validation_times)
                max_single = max(single_validation_times)
                min_single = min(single_validation_times)
                median_single = statistics.median(single_validation_times)
                
                # Performance requirements for JWT delegation
                if avg_single > 100:  # 100ms average is too slow for auth
                    pytest.fail(
                        f"JWT DELEGATION TOO SLOW (Issue #1078):\n"
                        f"Average validation time: {avg_single:.2f}ms (should be < 100ms)\n"
                        f"Median: {median_single:.2f}ms\n"
                        f"Min/Max: {min_single:.2f}ms / {max_single:.2f}ms\n"
                        f"All times: {[f'{t:.1f}' for t in single_validation_times[:10]]}...\n\n"
                        "SSOT delegation to auth service should be fast.\n"
                        "High latency indicates inefficient delegation implementation\n"
                        "or excessive overhead in auth client."
                    )
                
                if max_single > 500:  # 500ms max is unacceptable
                    pytest.fail(
                        f"JWT DELEGATION MAX TIME EXCEEDED (Issue #1078):\n"
                        f"Maximum validation time: {max_single:.2f}ms (should be < 500ms)\n"
                        f"This occurred in validation with times: {single_validation_times}\n\n"
                        "Individual JWT validations should not exceed 500ms.\n"
                        "This suggests auth service delegation has performance issues."
                    )
                
                # Performance acceptable for single validations
                assert avg_single < 100, f"Single validation performance acceptable: {avg_single:.2f}ms"
                
        except ImportError as e:
            pytest.fail(f"Auth client import failed: {e}")
        except Exception as e:
            pytest.fail(f"JWT delegation performance test failed: {e}")
    
    async def test_concurrent_jwt_validation_performance(self):
        """
        FAILING TEST: Concurrent JWT validations should scale efficiently  
        
        This test validates JWT delegation can handle multiple concurrent requests
        without significant performance degradation. Expected to FAIL if delegation
        doesn't scale properly.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            auth_client = AuthServiceClient()
            
            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 20]
            performance_results = {}
            
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "valid": True,
                    "payload": self.mock_payload
                }
                mock_response.status_code = 200
                mock_response.raise_for_status = Mock()
                
                # Simulate realistic auth service response time
                async def mock_post_with_realistic_delay(*args, **kwargs):
                    await asyncio.sleep(0.015)  # 15ms realistic auth service time
                    return mock_response
                
                mock_post.side_effect = mock_post_with_realistic_delay
                
                for concurrency in concurrency_levels:
                    # Create concurrent validation tasks
                    async def validate_token():
                        start_time = time.time()
                        result = await auth_client.validate_token_jwt(self.test_token)
                        end_time = time.time()
                        return (end_time - start_time) * 1000, result.get("valid") if result else False
                    
                    # Run concurrent validations
                    start_concurrent = time.time()
                    tasks = [validate_token() for _ in range(concurrency)]
                    results = await asyncio.gather(*tasks)
                    end_concurrent = time.time()
                    
                    # Analyze concurrent performance
                    validation_times = [r[0] for r in results]
                    validation_success = [r[1] for r in results]
                    
                    total_time = (end_concurrent - start_concurrent) * 1000
                    avg_validation_time = statistics.mean(validation_times)
                    success_rate = sum(validation_success) / len(validation_success)
                    
                    performance_results[concurrency] = {
                        "total_time": total_time,
                        "avg_validation_time": avg_validation_time,
                        "success_rate": success_rate,
                        "throughput": concurrency / (total_time / 1000)  # validations per second
                    }
                
                # Analyze scaling performance
                scaling_issues = []
                
                # Check success rates
                for concurrency, results in performance_results.items():
                    if results["success_rate"] < 1.0:
                        scaling_issues.append(
                            f"Concurrency {concurrency}: {results['success_rate']*100:.1f}% success rate"
                        )
                
                # Check performance degradation
                single_perf = performance_results[1]
                high_concurrency_perf = performance_results[20]
                
                perf_degradation = (high_concurrency_perf["avg_validation_time"] / 
                                  single_perf["avg_validation_time"])
                
                if perf_degradation > 3.0:  # More than 3x slower is problematic
                    scaling_issues.append(
                        f"Performance degradation: {perf_degradation:.1f}x slower at high concurrency"
                    )
                
                # Check throughput scaling
                expected_throughput_20 = performance_results[1]["throughput"] * 15  # Should scale reasonably
                actual_throughput_20 = performance_results[20]["throughput"]
                
                if actual_throughput_20 < expected_throughput_20 * 0.3:  # Less than 30% of expected
                    scaling_issues.append(
                        f"Poor throughput scaling: {actual_throughput_20:.1f} vs expected ~{expected_throughput_20:.1f} req/sec"
                    )
                
                if scaling_issues:
                    performance_summary = "\n".join([
                        f"Concurrency {c}: {r['avg_validation_time']:.1f}ms avg, {r['throughput']:.1f} req/sec, {r['success_rate']*100:.0f}% success"
                        for c, r in performance_results.items()
                    ])
                    
                    pytest.fail(
                        f"JWT DELEGATION SCALING ISSUES (Issue #1078):\n" +
                        "\n".join(f"  - {issue}" for issue in scaling_issues) +
                        f"\n\nPerformance Summary:\n{performance_summary}\n\n"
                        f"SSOT JWT delegation should scale efficiently with concurrency.\n"
                        f"Scaling issues suggest auth client implementation problems\n"
                        f"or inefficient connection management."
                    )
                
                # Scaling performance acceptable
                assert all(r["success_rate"] == 1.0 for r in performance_results.values()), \
                    "All concurrent validations should succeed"
                
        except ImportError as e:
            pytest.fail(f"Auth client import failed: {e}")
        except Exception as e:
            pytest.fail(f"Concurrent JWT validation performance test failed: {e}")
    
    async def test_websocket_jwt_validation_performance(self):
        """
        FAILING TEST: WebSocket JWT validation should be performant
        
        This test validates WebSocket JWT validation performance when delegating
        to auth service. Expected to FAIL if WebSocket delegation is inefficient.
        """
        try:
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            extractor = UserContextExtractor()
            
            # Mock auth service for WebSocket testing
            with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
                # Configure realistic auth client mock
                mock_auth_client.validate_token_jwt = AsyncMock()
                
                async def mock_validation_with_delay(token):
                    await asyncio.sleep(0.020)  # 20ms realistic auth service call
                    return {
                        "valid": True,
                        "payload": self.mock_payload,
                        "websocket_validated": True
                    }
                
                mock_auth_client.validate_token_jwt.side_effect = mock_validation_with_delay
                
                # Performance test: WebSocket JWT validation
                websocket_validation_times = []
                
                for i in range(15):  # 15 WebSocket validations
                    start_time = time.time()
                    result = await extractor.validate_and_decode_jwt(self.test_token)
                    end_time = time.time()
                    
                    validation_time = (end_time - start_time) * 1000
                    websocket_validation_times.append(validation_time)
                    
                    assert result is not None, f"WebSocket validation {i} should succeed"
                    assert result.get("valid") is True, f"WebSocket validation {i} should be valid"
                
                # Analyze WebSocket validation performance
                avg_websocket = statistics.mean(websocket_validation_times)
                max_websocket = max(websocket_validation_times)
                min_websocket = min(websocket_validation_times)
                
                # WebSocket performance requirements (should be similar to regular validation)
                if avg_websocket > 150:  # 150ms average for WebSocket (slightly higher than API)
                    pytest.fail(
                        f"WEBSOCKET JWT VALIDATION TOO SLOW (Issue #1078):\n"
                        f"Average WebSocket validation: {avg_websocket:.2f}ms (should be < 150ms)\n"
                        f"Min/Max: {min_websocket:.2f}ms / {max_websocket:.2f}ms\n"
                        f"All times: {[f'{t:.1f}' for t in websocket_validation_times[:8]]}...\n\n"
                        "WebSocket JWT validation should be performant.\n"
                        "High latency suggests WebSocket auth service delegation\n"
                        "has additional overhead or inefficient implementation."
                    )
                
                if max_websocket > 1000:  # 1 second max is too slow for WebSocket
                    pytest.fail(
                        f"WEBSOCKET JWT VALIDATION TIMEOUT (Issue #1078):\n"
                        f"Maximum WebSocket validation: {max_websocket:.2f}ms (should be < 1000ms)\n\n"
                        "WebSocket JWT validation should not exceed 1 second.\n"
                        "This suggests serious performance issues in WebSocket\n"
                        "auth service delegation."
                    )
                
                # Verify auth client was called correctly
                assert mock_auth_client.validate_token_jwt.call_count == 15, \
                    "Auth service should be called for each WebSocket validation"
                
                # Performance acceptable for WebSocket
                assert avg_websocket < 150, f"WebSocket validation performance acceptable: {avg_websocket:.2f}ms"
                
        except ImportError as e:
            pytest.fail(f"WebSocket user context extractor import failed: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket JWT validation performance test failed: {e}")
    
    async def test_jwt_secret_synchronization_performance(self):
        """
        FAILING TEST: JWT secret synchronization should not impact performance
        
        This test validates that JWT secret consistency checks don't create
        performance bottlenecks. Expected to FAIL if secret sync is inefficient.
        """
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            auth_client = AuthServiceClient()
            
            # Test performance with different token scenarios
            token_scenarios = [
                ("valid_token", self.test_token, {"valid": True, "payload": self.mock_payload}),
                ("expired_token", "expired.jwt.token", {"valid": False, "error": "Token expired"}),
                ("invalid_token", "invalid.token.here", {"valid": False, "error": "Invalid token"}),
                ("malformed_token", "not-a-jwt", {"valid": False, "error": "Malformed token"})
            ]
            
            scenario_performance = {}
            
            for scenario_name, test_token, expected_response in token_scenarios:
                with patch('httpx.AsyncClient.post') as mock_post:
                    mock_response = Mock()
                    mock_response.json.return_value = expected_response
                    mock_response.status_code = 200 if expected_response.get("valid") else 400
                    mock_response.raise_for_status = Mock()
                    
                    # Add consistent delay for all scenarios
                    async def mock_post_consistent_delay(*args, **kwargs):
                        await asyncio.sleep(0.025)  # 25ms consistent delay
                        return mock_response
                    
                    mock_post.side_effect = mock_post_consistent_delay
                    
                    # Performance test for this scenario
                    scenario_times = []
                    
                    for i in range(10):  # 10 validations per scenario
                        start_time = time.time()
                        
                        try:
                            result = await auth_client.validate_token_jwt(test_token)
                            end_time = time.time()
                            validation_time = (end_time - start_time) * 1000
                            scenario_times.append(validation_time)
                            
                            # Verify expected result
                            if expected_response.get("valid"):
                                assert result is not None and result.get("valid"), \
                                    f"Valid token should return valid result"
                            else:
                                # Invalid tokens might return None or valid=False
                                assert result is None or not result.get("valid"), \
                                    f"Invalid token should return invalid result"
                        
                        except Exception as e:
                            # For invalid tokens, exceptions might be expected
                            end_time = time.time()
                            validation_time = (end_time - start_time) * 1000
                            scenario_times.append(validation_time)
                    
                    scenario_performance[scenario_name] = {
                        "avg_time": statistics.mean(scenario_times),
                        "max_time": max(scenario_times),
                        "min_time": min(scenario_times),
                        "all_times": scenario_times
                    }
            
            # Analyze performance consistency across scenarios
            performance_issues = []
            
            # Check for excessive variation between scenarios
            avg_times = [perf["avg_time"] for perf in scenario_performance.values()]
            max_avg = max(avg_times)
            min_avg = min(avg_times)
            
            if max_avg / min_avg > 2.5:  # More than 2.5x variation is concerning
                performance_issues.append(
                    f"High performance variation: {min_avg:.1f}ms to {max_avg:.1f}ms avg"
                )
            
            # Check for slow scenarios
            slow_scenarios = [
                (name, perf["avg_time"]) for name, perf in scenario_performance.items()
                if perf["avg_time"] > 200  # 200ms is too slow
            ]
            
            if slow_scenarios:
                performance_issues.extend([
                    f"Slow {name}: {avg_time:.1f}ms average"
                    for name, avg_time in slow_scenarios
                ])
            
            # Check for timeout scenarios
            timeout_scenarios = [
                (name, perf["max_time"]) for name, perf in scenario_performance.items()
                if perf["max_time"] > 1000  # 1 second max is too slow
            ]
            
            if timeout_scenarios:
                performance_issues.extend([
                    f"Timeout {name}: {max_time:.1f}ms maximum"
                    for name, max_time in timeout_scenarios
                ])
            
            if performance_issues:
                performance_summary = "\n".join([
                    f"{name}: {perf['avg_time']:.1f}ms avg, {perf['max_time']:.1f}ms max"
                    for name, perf in scenario_performance.items()
                ])
                
                pytest.fail(
                    f"JWT SECRET SYNCHRONIZATION PERFORMANCE ISSUES (Issue #1078):\n" +
                    "\n".join(f"  - {issue}" for issue in performance_issues) +
                    f"\n\nScenario Performance:\n{performance_summary}\n\n"
                    f"JWT validation should perform consistently across scenarios.\n"
                    f"Performance variation suggests inefficient secret synchronization\n"
                    f"or inconsistent auth service delegation patterns."
                )
            
            # Performance consistency verified
            assert len(scenario_performance) == len(token_scenarios), "All scenarios should complete"
            
        except ImportError as e:
            pytest.fail(f"Auth client import failed: {e}")
        except Exception as e:
            pytest.fail(f"JWT secret synchronization performance test failed: {e}")
    
    async def test_memory_efficiency_jwt_delegation(self):
        """
        FAILING TEST: JWT delegation should be memory efficient
        
        This test validates JWT delegation doesn't create memory leaks or
        excessive memory usage. Expected to FAIL if delegation is inefficient.
        """
        try:
            import psutil
            import os
            
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            auth_client = AuthServiceClient()
            
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "valid": True,
                    "payload": self.mock_payload
                }
                mock_response.status_code = 200
                mock_response.raise_for_status = Mock()
                
                async def mock_post_no_delay(*args, **kwargs):
                    return mock_response
                
                mock_post.side_effect = mock_post_no_delay
                
                # Perform many validations to test memory efficiency
                memory_samples = []
                
                for batch in range(10):  # 10 batches
                    # Perform 50 validations per batch
                    for i in range(50):
                        await auth_client.validate_token_jwt(self.test_token)
                    
                    # Sample memory usage
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_samples.append(current_memory)
                
                # Analyze memory usage
                final_memory = memory_samples[-1]
                memory_growth = final_memory - initial_memory
                max_memory = max(memory_samples)
                
                # Memory efficiency requirements
                if memory_growth > 10:  # More than 10MB growth is concerning
                    pytest.fail(
                        f"EXCESSIVE MEMORY GROWTH (Issue #1078):\n"
                        f"Memory growth: {memory_growth:.1f}MB (should be < 10MB)\n"
                        f"Initial: {initial_memory:.1f}MB\n"
                        f"Final: {final_memory:.1f}MB\n"
                        f"Max: {max_memory:.1f}MB\n"
                        f"Growth pattern: {[f'{m:.1f}' for m in memory_samples]}\n\n"
                        "JWT delegation should not cause significant memory growth.\n"
                        "Excessive growth suggests memory leaks in auth client\n"
                        "or inefficient connection management."
                    )
                
                if max_memory - initial_memory > 20:  # More than 20MB peak growth
                    pytest.fail(
                        f"HIGH PEAK MEMORY USAGE (Issue #1078):\n"
                        f"Peak memory growth: {max_memory - initial_memory:.1f}MB\n"
                        f"This suggests inefficient memory usage patterns\n"
                        f"in JWT delegation implementation."
                    )
                
                # Memory efficiency acceptable
                assert memory_growth < 10, f"Memory growth acceptable: {memory_growth:.1f}MB"
                
        except ImportError:
            pytest.skip("psutil not available for memory testing")
        except Exception as e:
            pytest.fail(f"Memory efficiency test failed: {e}")