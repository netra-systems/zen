"""Network Retry and Recovery Testing



This module contains utilities for testing retry patterns, circuit breakers,

and progressive timeout scenarios.

"""



import asyncio

import logging



# Add project root to path for imports

import sys

import time

from pathlib import Path

from typing import Any, Dict





from tests.e2e.helpers.resilience.error_propagation.error_generators import (

    RealErrorPropagationTester,

)

from test_framework.http_client import ClientConfig

from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient



logger = logging.getLogger(__name__)





class RetryPatternTester:

    """Utility for testing specific retry patterns."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

    

    async def test_circuit_breaker_behavior(self, endpoint: str = "/health") -> Dict[str, Any]:

        """Test circuit breaker pattern behavior."""

        failure_count = 0

        success_count = 0

        

        # Simulate multiple rapid failures

        for attempt in range(5):

            try:

                config = ClientConfig(timeout=0.01, max_retries=0)  # Immediate timeout

                client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)

                

                try:

                    await client.get(endpoint)

                    success_count += 1

                except Exception:

                    failure_count += 1

                finally:

                    await client.close()

                    

            except Exception:

                failure_count += 1

            

            await asyncio.sleep(0.1)  # Brief pause between attempts

        

        return {

            "total_attempts": 5,

            "failure_count": failure_count,

            "success_count": success_count,

            "circuit_breaker_triggered": failure_count >= 3

        }

    

    async def test_progressive_timeout_increase(self) -> Dict[str, Any]:

        """Test progressive timeout increase pattern."""

        timeouts = [0.1, 0.2, 0.5, 1.0]

        results = []

        

        for timeout in timeouts:

            config = ClientConfig(timeout=timeout, max_retries=1)

            client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)

            

            try:

                start_time = time.time()

                await client.get("/health")

                end_time = time.time()

                

                results.append({

                    "timeout_setting": timeout,

                    "actual_time": end_time - start_time,

                    "success": True

                })

                break  # Success, no need to try longer timeouts

                

            except Exception as e:

                results.append({

                    "timeout_setting": timeout,

                    "success": False,

                    "error": str(e)

                })

            finally:

                await client.close()

        

        return {

            "progressive_timeouts": results,

            "eventual_success": any(r["success"] for r in results)

        }





class RecoveryScenarioTester:

    """Test various recovery scenarios and patterns."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

    

    async def test_service_degradation_recovery(self) -> Dict[str, Any]:

        """Test service recovery from degraded state."""

        # Test health endpoint (should always work)

        health_result = await self._test_endpoint_availability("/health")

        

        # Test critical endpoint (might be degraded)

        critical_result = await self._test_endpoint_availability("/auth/me")

        

        # Assess recovery capability

        recovery_assessment = self._assess_recovery_capability(health_result, critical_result)

        

        return {

            "health_endpoint": health_result,

            "critical_endpoint": critical_result,

            "recovery_assessment": recovery_assessment

        }

    

    async def _test_endpoint_availability(self, endpoint: str) -> Dict[str, Any]:

        """Test specific endpoint availability."""

        config = ClientConfig(timeout=5.0, max_retries=2)

        client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)

        

        try:

            start_time = time.time()

            response = await client.get(endpoint)

            end_time = time.time()

            

            return {

                "endpoint": endpoint,

                "available": True,

                "response_time": end_time - start_time,

                "status_code": getattr(response, 'status_code', None)

            }

            

        except Exception as e:

            return {

                "endpoint": endpoint,

                "available": False,

                "error": str(e),

                "degraded": self._is_degraded_error(str(e))

            }

        finally:

            await client.close()

    

    def _is_degraded_error(self, error_str: str) -> bool:

        """Check if error indicates service degradation rather than complete failure."""

        degradation_indicators = ["timeout", "slow", "degraded", "limited", "temporary"]

        return any(indicator in error_str.lower() for indicator in degradation_indicators)

    

    def _assess_recovery_capability(self, health_result: Dict, critical_result: Dict) -> Dict[str, Any]:

        """Assess system's recovery capability."""

        health_available = health_result.get("available", False)

        critical_available = critical_result.get("available", False)

        

        if health_available and critical_available:

            recovery_state = "fully_operational"

        elif health_available and not critical_available:

            recovery_state = "degraded_service"

        elif not health_available:

            recovery_state = "service_down"

        else:

            recovery_state = "unknown"

        

        return {

            "recovery_state": recovery_state,

            "health_monitoring_active": health_available,

            "critical_services_available": critical_available,

            "graceful_degradation": health_available and not critical_available

        }





class NetworkResilienceTester:

    """Test network resilience patterns."""

    

    def __init__(self, tester: RealErrorPropagationTester):

        self.tester = tester

    

    async def test_connection_pooling_behavior(self) -> Dict[str, Any]:

        """Test connection pooling behavior under stress."""

        concurrent_requests = 5

        results = []

        

        # Create multiple concurrent requests

        tasks = []

        for i in range(concurrent_requests):

            task = self._make_concurrent_request(f"request_{i}")

            tasks.append(task)

        

        # Execute all requests concurrently

        results = await asyncio.gather(*tasks, return_exceptions=True)

        

        # Analyze results

        successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

        failed_requests = concurrent_requests - successful_requests

        

        return {

            "concurrent_requests": concurrent_requests,

            "successful_requests": successful_requests,

            "failed_requests": failed_requests,

            "connection_pooling_effective": successful_requests >= concurrent_requests * 0.8,

            "detailed_results": [r for r in results if isinstance(r, dict)]

        }

    

    async def _make_concurrent_request(self, request_id: str) -> Dict[str, Any]:

        """Make a single concurrent request."""

        config = ClientConfig(timeout=3.0, max_retries=1, pool_size=2)

        client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)

        

        try:

            start_time = time.time()

            response = await client.get("/health")

            end_time = time.time()

            

            return {

                "request_id": request_id,

                "success": True,

                "response_time": end_time - start_time,

                "status_code": getattr(response, 'status_code', None)

            }

            

        except Exception as e:

            return {

                "request_id": request_id,

                "success": False,

                "error": str(e),

                "connection_issue": "connection" in str(e).lower()

            }

        finally:

            await client.close()

    

    async def test_keepalive_behavior(self) -> Dict[str, Any]:

        """Test HTTP keep-alive behavior."""

        config = ClientConfig(timeout=5.0, max_retries=1, pool_size=1)

        client = RealHTTPClient(self.tester.orchestrator.get_service_url("backend"), config)

        

        try:

            # Make multiple requests on the same client to test keep-alive

            request_times = []

            

            for i in range(3):

                start_time = time.time()

                await client.get("/health")

                end_time = time.time()

                

                request_times.append(end_time - start_time)

                await asyncio.sleep(0.1)  # Small delay between requests

            

            # First request typically takes longer (connection establishment)

            # Subsequent requests should be faster (keep-alive)

            first_request_time = request_times[0]

            avg_subsequent_time = sum(request_times[1:]) / len(request_times[1:]) if len(request_times) > 1 else 0

            

            keepalive_effective = (

                len(request_times) >= 2 and 

                avg_subsequent_time < first_request_time * 0.8

            )

            

            return {

                "request_times": request_times,

                "first_request_time": first_request_time,

                "avg_subsequent_time": avg_subsequent_time,

                "keepalive_effective": keepalive_effective,

                "connection_reused": keepalive_effective

            }

            

        except Exception as e:

            return {

                "keepalive_test_failed": True,

                "error": str(e)

            }

        finally:

            await client.close()





class TimeoutPatternAnalyzer:

    """Analyze timeout patterns and behaviors."""

    

    @staticmethod

    def analyze_timeout_progression(timeout_results: list) -> Dict[str, Any]:

        """Analyze timeout progression patterns."""

        if not timeout_results:

            return {"error": "no_timeout_results"}

        

        successful_timeouts = [r for r in timeout_results if r.get("success", False)]

        failed_timeouts = [r for r in timeout_results if not r.get("success", False)]

        

        if successful_timeouts:

            min_successful_timeout = min(r.get("timeout_setting", float('inf')) for r in successful_timeouts)

            avg_successful_time = sum(r.get("actual_time", 0) for r in successful_timeouts) / len(successful_timeouts)

        else:

            min_successful_timeout = None

            avg_successful_time = 0

        

        return {

            "total_timeout_tests": len(timeout_results),

            "successful_timeouts": len(successful_timeouts),

            "failed_timeouts": len(failed_timeouts),

            "min_successful_timeout": min_successful_timeout,

            "avg_successful_response_time": avg_successful_time,

            "timeout_effectiveness": len(successful_timeouts) > 0

        }

    

    @staticmethod

    def calculate_optimal_timeout(response_times: list, percentile: float = 95.0) -> Dict[str, Any]:

        """Calculate optimal timeout based on response time distribution."""

        if not response_times:

            return {"error": "no_response_times"}

        

        sorted_times = sorted(response_times)

        percentile_index = int(len(sorted_times) * (percentile / 100.0))

        if percentile_index >= len(sorted_times):

            percentile_index = len(sorted_times) - 1

        

        percentile_time = sorted_times[percentile_index]

        avg_time = sum(response_times) / len(response_times)

        max_time = max(response_times)

        min_time = min(response_times)

        

        # Suggest timeout with buffer

        suggested_timeout = percentile_time * 1.5  # 50% buffer

        

        return {

            "response_time_count": len(response_times),

            "avg_response_time": avg_time,

            "min_response_time": min_time,

            "max_response_time": max_time,

            f"p{percentile}_response_time": percentile_time,

            "suggested_timeout": suggested_timeout,

            "timeout_buffer_factor": 1.5

        }

