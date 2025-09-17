"""
E2E Staging Tests for Issue #1278 - HTTP 503 Service Unavailable Reproduction

These E2E tests reproduce Issue #1278 HTTP 503 errors in the actual staging environment
by testing real infrastructure constraints and timeout scenarios.

Expected Result: Tests should FAIL, reproducing actual HTTP 503 errors
"""

import asyncio
import pytest
import aiohttp
import time
from typing import List, Dict, Optional
from test_framework.base_e2e_test import BaseE2ETest


class TestIssue1278StagingReproduction(BaseE2ETest):
    """E2E tests reproducing Issue #1278 in staging environment."""

    # Staging environment URLs (must use *.netrasystems.ai domains)
    STAGING_BACKEND_URL = "https://staging.netrasystems.ai"
    STAGING_FRONTEND_URL = "https://staging.netrasystems.ai"
    STAGING_WEBSOCKET_URL = "wss://api.staging.netrasystems.ai"

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_http_503_during_service_startup(self):
        """
        Test HTTP 503 errors during service startup in staging environment.

        Expected: TEST FAILURE - Reproduces actual HTTP 503 errors
        """
        # Test multiple concurrent requests during service startup window
        # This reproduces the exact Issue #1278 scenario

        concurrent_requests = 20
        http_503_occurrences = 0
        successful_requests = 0
        request_times = []

        async def make_staging_request(session: aiohttp.ClientSession, request_id: int) -> Dict:
            """Make request to staging environment during startup window."""
            start_time = time.time()

            try:
                # Health check endpoint should be available
                async with session.get(
                    f"{self.STAGING_BACKEND_URL}/health",
                    timeout=aiohttp.ClientTimeout(total=30.0)
                ) as response:
                    request_time = time.time() - start_time

                    return {
                        "request_id": request_id,
                        "status_code": response.status,
                        "request_time": request_time,
                        "status": "success" if response.status == 200 else "error",
                        "headers": dict(response.headers)
                    }

            except aiohttp.ClientError as e:
                request_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status_code": None,
                    "request_time": request_time,
                    "status": "failed",
                    "error": str(e)
                }
            except asyncio.TimeoutError:
                request_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status_code": 503,  # Timeout likely results in 503
                    "request_time": request_time,
                    "status": "timeout",
                    "error": "Request timeout - likely service unavailable"
                }

        # Execute concurrent requests to staging
        async with aiohttp.ClientSession() as session:
            tasks = [
                make_staging_request(session, i)
                for i in range(concurrent_requests)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze staging response patterns
        for result in results:
            if isinstance(result, dict):
                request_times.append(result["request_time"])

                if result["status_code"] == 503:
                    http_503_occurrences += 1
                elif result["status_code"] == 200:
                    successful_requests += 1

        # Calculate failure metrics
        http_503_rate = http_503_occurrences / len(results)
        success_rate = successful_requests / len(results)
        avg_request_time = sum(request_times) / len(request_times) if request_times else 0

        # CRITICAL TEST: HTTP 503 rate indicates Issue #1278 reproduction
        if http_503_rate > 0.1:  # >10% HTTP 503 rate
            pytest.fail(
                f"Issue #1278 HTTP 503 reproduced in staging: "
                f"{http_503_rate:.1%} HTTP 503 rate ({http_503_occurrences}/{len(results)}) "
                f"with {success_rate:.1%} success rate, "
                f"average request time {avg_request_time:.1f}s"
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket
    async def test_staging_websocket_connection_failures_during_503(self):
        """
        Test WebSocket connection failures during HTTP 503 periods.

        Expected: TEST FAILURE - WebSocket connections fail during infrastructure issues
        """
        # WebSocket connections should fail when backend returns HTTP 503
        # This tests the compound failure pattern

        websocket_connection_attempts = 10
        websocket_failures = 0
        websocket_timeouts = 0
        connection_times = []

        async def attempt_staging_websocket_connection(attempt_id: int) -> Dict:
            """Attempt WebSocket connection to staging during potential 503 period."""
            start_time = time.time()

            try:
                # Use staging WebSocket URL
                import websockets

                # Attempt connection with realistic timeout
                async with websockets.connect(
                    f"{self.STAGING_WEBSOCKET_URL}/ws",
                    timeout=20.0  # Reasonable timeout for staging
                ) as websocket:
                    # Send test message
                    await websocket.send('{"type": "test", "message": "Issue #1278 test"}')

                    # Wait for response (with timeout)
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                    connection_time = time.time() - start_time
                    return {
                        "attempt_id": attempt_id,
                        "status": "success",
                        "connection_time": connection_time,
                        "response": response
                    }

            except asyncio.TimeoutError:
                connection_time = time.time() - start_time
                return {
                    "attempt_id": attempt_id,
                    "status": "timeout",
                    "connection_time": connection_time,
                    "error": "WebSocket connection timeout - likely backend unavailable"
                }
            except Exception as e:
                connection_time = time.time() - start_time
                return {
                    "attempt_id": attempt_id,
                    "status": "failed",
                    "connection_time": connection_time,
                    "error": str(e)
                }

        # Execute WebSocket connection attempts
        websocket_results = []
        for attempt_id in range(websocket_connection_attempts):
            result = await attempt_staging_websocket_connection(attempt_id)
            websocket_results.append(result)

            connection_times.append(result["connection_time"])

            if result["status"] == "failed":
                websocket_failures += 1
            elif result["status"] == "timeout":
                websocket_timeouts += 1

            # Small delay between attempts
            await asyncio.sleep(1.0)

        # Analyze WebSocket failure patterns
        websocket_failure_rate = (websocket_failures + websocket_timeouts) / websocket_connection_attempts
        avg_connection_time = sum(connection_times) / len(connection_times)

        # CRITICAL TEST: High WebSocket failure rate during HTTP 503 periods
        if websocket_failure_rate > 0.3:  # >30% WebSocket failure rate
            pytest.fail(
                f"Issue #1278 WebSocket failure pattern during HTTP 503: "
                f"WebSocket failure rate {websocket_failure_rate:.1%} "
                f"({websocket_failures + websocket_timeouts}/{websocket_connection_attempts}) "
                f"with average connection time {avg_connection_time:.1f}s"
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_load_balancer_timeout_pattern(self):
        """
        Test load balancer timeout patterns that cause HTTP 503 in staging.

        Expected: TEST FAILURE - Load balancer timeouts cause service unavailability
        """
        # Load balancer has timeout thresholds that cause HTTP 503
        # Test requests that approach or exceed these thresholds

        load_balancer_timeout_threshold = 60.0  # Typical Cloud Load Balancer timeout
        long_running_requests = 5
        timeout_violations = 0
        request_durations = []

        async def make_long_running_staging_request(session: aiohttp.ClientSession, request_id: int) -> Dict:
            """Make request that may trigger load balancer timeout."""
            start_time = time.time()

            try:
                # Use endpoint that might have longer processing time
                timeout_config = aiohttp.ClientTimeout(total=load_balancer_timeout_threshold + 10.0)

                async with session.get(
                    f"{self.STAGING_BACKEND_URL}/api/health",  # Extended health check
                    timeout=timeout_config
                ) as response:
                    request_duration = time.time() - start_time

                    return {
                        "request_id": request_id,
                        "status_code": response.status,
                        "request_duration": request_duration,
                        "status": "success" if response.status == 200 else "error",
                        "load_balancer_timeout_exceeded": request_duration > load_balancer_timeout_threshold
                    }

            except asyncio.TimeoutError:
                request_duration = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status_code": 503,  # Load balancer timeout manifests as 503
                    "request_duration": request_duration,
                    "status": "timeout",
                    "error": "Load balancer timeout",
                    "load_balancer_timeout_exceeded": True
                }
            except Exception as e:
                request_duration = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status_code": None,
                    "request_duration": request_duration,
                    "status": "failed",
                    "error": str(e),
                    "load_balancer_timeout_exceeded": request_duration > load_balancer_timeout_threshold
                }

        # Execute long-running requests
        async with aiohttp.ClientSession() as session:
            tasks = [
                make_long_running_staging_request(session, i)
                for i in range(long_running_requests)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze load balancer timeout patterns
        for result in results:
            if isinstance(result, dict):
                request_durations.append(result["request_duration"])

                if result["load_balancer_timeout_exceeded"]:
                    timeout_violations += 1

        # Calculate timeout metrics
        timeout_violation_rate = timeout_violations / len(results)
        avg_request_duration = sum(request_durations) / len(request_durations) if request_durations else 0

        # CRITICAL TEST: Load balancer timeouts cause HTTP 503
        if timeout_violation_rate > 0.2:  # >20% timeout violation rate
            pytest.fail(
                f"Issue #1278 load balancer timeout pattern: "
                f"Timeout violation rate {timeout_violation_rate:.1%} "
                f"({timeout_violations}/{len(results)}) "
                f"with average request duration {avg_request_duration:.1f}s "
                f"exceeding load balancer threshold {load_balancer_timeout_threshold}s"
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_database_connection_timeout_cascade(self):
        """
        Test database connection timeout cascade that leads to HTTP 503.

        Expected: TEST FAILURE - Database timeouts cascade to HTTP 503 responses
        """
        # Database connection issues cascade to cause HTTP 503 responses
        # Test the complete failure chain

        database_dependent_requests = 8
        database_timeout_indicators = 0
        slow_response_count = 0
        response_times = []

        async def make_database_dependent_request(session: aiohttp.ClientSession, request_id: int) -> Dict:
            """Make request that depends on database connectivity."""
            start_time = time.time()

            try:
                # Use endpoint that requires database access
                async with session.get(
                    f"{self.STAGING_BACKEND_URL}/api/status",  # Status endpoint likely uses database
                    timeout=aiohttp.ClientTimeout(total=45.0)
                ) as response:
                    response_time = time.time() - start_time

                    # Slow responses (>20s) indicate database timeout issues
                    slow_response = response_time > 20.0

                    return {
                        "request_id": request_id,
                        "status_code": response.status,
                        "response_time": response_time,
                        "status": "success" if response.status == 200 else "error",
                        "slow_response": slow_response,
                        "database_timeout_indicated": slow_response or response.status in [503, 504]
                    }

            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status_code": 503,
                    "response_time": response_time,
                    "status": "timeout",
                    "error": "Database connection timeout cascade",
                    "slow_response": True,
                    "database_timeout_indicated": True
                }
            except Exception as e:
                response_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "status_code": None,
                    "response_time": response_time,
                    "status": "failed",
                    "error": str(e),
                    "slow_response": response_time > 20.0,
                    "database_timeout_indicated": True
                }

        # Execute database-dependent requests
        async with aiohttp.ClientSession() as session:
            tasks = [
                make_database_dependent_request(session, i)
                for i in range(database_dependent_requests)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze database timeout cascade patterns
        for result in results:
            if isinstance(result, dict):
                response_times.append(result["response_time"])

                if result["database_timeout_indicated"]:
                    database_timeout_indicators += 1

                if result["slow_response"]:
                    slow_response_count += 1

        # Calculate cascade failure metrics
        database_timeout_rate = database_timeout_indicators / len(results)
        slow_response_rate = slow_response_count / len(results)
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # CRITICAL TEST: High database timeout indicators suggest cascade failure
        if database_timeout_rate > 0.25:  # >25% database timeout indicators
            pytest.fail(
                f"Issue #1278 database timeout cascade to HTTP 503: "
                f"Database timeout indicator rate {database_timeout_rate:.1%} "
                f"({database_timeout_indicators}/{len(results)}) "
                f"with {slow_response_rate:.1%} slow responses, "
                f"average response time {avg_response_time:.1f}s"
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_health_check_failure_during_503_period(self):
        """
        Test health check failures during HTTP 503 periods in staging.

        Expected: TEST FAILURE - Health checks fail during infrastructure constraints
        """
        # Health checks should fail during HTTP 503 periods
        # This confirms infrastructure-level issues

        health_check_attempts = 12
        health_check_failures = 0
        health_check_timeouts = 0
        health_response_times = []

        async def perform_staging_health_check(session: aiohttp.ClientSession, check_id: int) -> Dict:
            """Perform health check against staging environment."""
            start_time = time.time()

            try:
                async with session.get(
                    f"{self.STAGING_BACKEND_URL}/health",
                    timeout=aiohttp.ClientTimeout(total=15.0)  # Health checks should be fast
                ) as response:
                    response_time = time.time() - start_time

                    # Health check success criteria
                    health_check_passed = (
                        response.status == 200 and
                        response_time < 10.0  # Health checks should be quick
                    )

                    return {
                        "check_id": check_id,
                        "status_code": response.status,
                        "response_time": response_time,
                        "health_check_passed": health_check_passed,
                        "status": "success" if health_check_passed else "unhealthy"
                    }

            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                return {
                    "check_id": check_id,
                    "status_code": 503,
                    "response_time": response_time,
                    "health_check_passed": False,
                    "status": "timeout",
                    "error": "Health check timeout"
                }
            except Exception as e:
                response_time = time.time() - start_time
                return {
                    "check_id": check_id,
                    "status_code": None,
                    "response_time": response_time,
                    "health_check_passed": False,
                    "status": "failed",
                    "error": str(e)
                }

        # Execute health checks with intervals
        async with aiohttp.ClientSession() as session:
            health_results = []
            for check_id in range(health_check_attempts):
                result = await perform_staging_health_check(session, check_id)
                health_results.append(result)

                health_response_times.append(result["response_time"])

                if not result["health_check_passed"]:
                    if result["status"] == "timeout":
                        health_check_timeouts += 1
                    else:
                        health_check_failures += 1

                # Interval between health checks
                await asyncio.sleep(2.0)

        # Analyze health check failure patterns
        total_health_failures = health_check_failures + health_check_timeouts
        health_failure_rate = total_health_failures / health_check_attempts
        avg_health_response_time = sum(health_response_times) / len(health_response_times)

        # CRITICAL TEST: High health check failure rate during HTTP 503 periods
        if health_failure_rate > 0.2:  # >20% health check failure rate
            pytest.fail(
                f"Issue #1278 health check failures during HTTP 503 period: "
                f"Health failure rate {health_failure_rate:.1%} "
                f"({total_health_failures}/{health_check_attempts}) "
                f"with average health response time {avg_health_response_time:.1f}s"
            )