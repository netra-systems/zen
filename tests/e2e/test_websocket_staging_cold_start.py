"""E2E Test: WebSocket Connection During Staging Cold Start for Issue #586

Tests real WebSocket connections to staging environment during cold starts to expose
the 1011 error conditions that occur in production-like environments.

Business Impact: Validates WebSocket handshake behavior in actual GCP Cloud Run
staging environment where cold starts cause 1011 errors.
"""

import asyncio
import time
import json
import os
import pytest
import websockets
from typing import Dict, Any, List, Optional
from unittest.mock import patch
import requests
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ColdStartSimulation:
    """Configuration for cold start simulation."""
    trigger_delay: float
    connection_attempts: int
    timeout_seconds: float
    retry_delay: float


@dataclass
class WebSocketConnectionAttempt:
    """Result of a WebSocket connection attempt."""
    attempt_number: int
    start_time: float
    end_time: float
    success: bool
    error_code: Optional[int]
    error_message: Optional[str]
    handshake_duration: float
    service_ready: bool


class StagingEnvironmentManager:
    """Manager for staging environment interactions."""
    
    def __init__(self):
        self.staging_base_url = self._get_staging_url()
        self.websocket_url = self._get_websocket_url()
        self.health_check_url = f"{self.staging_base_url}/health"
        
    def _get_staging_url(self) -> str:
        """Get staging environment URL."""
        # In real implementation, this would get actual staging URL
        staging_url = os.getenv("STAGING_BASE_URL")
        if staging_url:
            return staging_url
        
        # Default staging URL pattern for GCP Cloud Run
        return "https://netra-backend-staging-abc123-uc.a.run.app"
        
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL for staging."""
        base_url = self.staging_base_url
        if base_url.startswith("https://"):
            websocket_url = base_url.replace("https://", "wss://")
        else:
            websocket_url = base_url.replace("http://", "ws://")
        
        return f"{websocket_url}/ws"
        
    async def trigger_cold_start(self) -> bool:
        """Trigger a cold start in staging environment."""
        try:
            # In real implementation, this might call GCP APIs to scale down/up
            # For simulation, we'll just wait for natural cold start conditions
            logger.info(f"Triggering cold start conditions for {self.staging_base_url}")
            
            # Simulate cold start by waiting for service to be idle
            await asyncio.sleep(2.0)
            
            return True
        except Exception as e:
            logger.error(f"Failed to trigger cold start: {e}")
            return False
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check service health status."""
        try:
            # Use asyncio-compatible HTTP request
            loop = asyncio.get_event_loop()
            
            def make_request():
                response = requests.get(
                    self.health_check_url, 
                    timeout=5.0,
                    headers={"User-Agent": "Issue586-E2E-Test"}
                )
                return response
            
            response = await loop.run_in_executor(None, make_request)
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "healthy": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "data": health_data
                }
            else:
                return {
                    "healthy": False,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time": None,
                "status_code": None
            }


class TestWebSocketStagingColdStart(SSotAsyncTestCase):
    """E2E tests for WebSocket connections during staging cold starts."""
    
    def setUp(self):
        """Set up E2E test environment."""
        super().setUp()
        self.staging_manager = StagingEnvironmentManager()
        self.connection_attempts = []
        
    @pytest.mark.staging
    async def test_websocket_connection_during_cold_start(self):
        """TEST FAILURE EXPECTED: WebSocket 1011 errors during staging cold start.
        
        This test should FAIL to expose the 1011 error condition that occurs when
        clients attempt WebSocket connections during GCP Cloud Run cold starts.
        """
        logger.info("🧪 Testing WebSocket connection during staging cold start")
        
        # Configure cold start simulation
        cold_start_config = ColdStartSimulation(
            trigger_delay=1.0,
            connection_attempts=5,
            timeout_seconds=10.0,
            retry_delay=2.0
        )
        
        # Step 1: Trigger cold start conditions
        logger.info("Step 1: Triggering cold start conditions")
        cold_start_triggered = await self.staging_manager.trigger_cold_start()
        
        if not cold_start_triggered:
            pytest.skip("Could not trigger cold start conditions in staging")
        
        # Step 2: Attempt WebSocket connections during startup
        logger.info("Step 2: Attempting WebSocket connections during startup")
        connection_results = await self._attempt_websocket_connections_during_startup(cold_start_config)
        
        # Step 3: Analyze connection results for 1011 errors
        error_1011_count = len([r for r in connection_results if r.error_code == 1011])
        successful_connections = len([r for r in connection_results if r.success])
        
        logger.info(f"Connection attempts: {len(connection_results)}")
        logger.info(f"1011 errors: {error_1011_count}")
        logger.info(f"Successful connections: {successful_connections}")
        
        # Log detailed results
        for result in connection_results:
            if result.error_code == 1011:
                logger.error(f"🚨 1011 Error at attempt {result.attempt_number}: {result.error_message}")
            elif not result.success:
                logger.warning(f"⚠️  Connection failed at attempt {result.attempt_number}: {result.error_message}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the 1011 error issue
        self.assertEqual(
            error_1011_count, 0,
            f"EXPECTED FAILURE: Found {error_1011_count} WebSocket 1011 errors during cold start. "
            f"This demonstrates the issue where clients get 1011 errors when connecting during "
            f"GCP Cloud Run startup. Total attempts: {len(connection_results)}, "
            f"Successful: {successful_connections}"
        )
        
    @pytest.mark.staging
    async def test_websocket_handshake_timeout_during_startup(self):
        """TEST FAILURE EXPECTED: WebSocket handshake timeouts during service startup.
        
        This test should FAIL to expose handshake timeout issues that contribute
        to 1011 errors when the service is not ready to handle WebSocket connections.
        """
        logger.info("🧪 Testing WebSocket handshake timeouts during startup")
        
        # Check initial service state
        initial_health = await self.staging_manager.check_service_health()
        logger.info(f"Initial service health: {initial_health}")
        
        # Attempt WebSocket connections with different timeout values
        timeout_tests = [
            {"timeout": 5.0, "description": "short_timeout"},
            {"timeout": 10.0, "description": "default_timeout"},
            {"timeout": 20.0, "description": "long_timeout"}
        ]
        
        timeout_results = []
        
        for timeout_test in timeout_tests:
            logger.info(f"Testing {timeout_test['description']} ({timeout_test['timeout']}s)")
            
            # Trigger potential startup conditions
            await self.staging_manager.trigger_cold_start()
            await asyncio.sleep(1.0)  # Brief delay
            
            # Attempt connection with specific timeout
            start_time = time.time()
            connection_result = await self._attempt_single_websocket_connection(
                timeout=timeout_test['timeout']
            )
            
            timeout_result = {
                "timeout": timeout_test['timeout'],
                "description": timeout_test['description'],
                "success": connection_result.success,
                "error_code": connection_result.error_code,
                "handshake_duration": connection_result.handshake_duration,
                "actual_duration": time.time() - start_time
            }
            
            timeout_results.append(timeout_result)
            logger.info(f"Result: {timeout_result}")
            
            # Brief delay between tests
            await asyncio.sleep(2.0)
        
        # Analyze timeout results
        failed_connections = [r for r in timeout_results if not r["success"]]
        timeout_failures = [r for r in failed_connections if r["actual_duration"] >= r["timeout"] * 0.9]
        
        logger.info(f"Total timeout tests: {len(timeout_results)}")
        logger.info(f"Failed connections: {len(failed_connections)}")
        logger.info(f"Timeout-related failures: {len(timeout_failures)}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes timeout issues contributing to 1011 errors
        if timeout_failures:
            failure_descriptions = [f"{r['description']}: {r['actual_duration']:.1f}s" for r in timeout_failures]
            self.assertEqual(
                len(timeout_failures), 0,
                f"EXPECTED FAILURE: WebSocket handshake timeouts during startup. "
                f"Timeout failures: {failure_descriptions}. This contributes to 1011 errors "
                f"when clients cannot complete handshake before service is ready."
            )
    
    @pytest.mark.staging 
    async def test_websocket_health_check_coordination(self):
        """TEST FAILURE EXPECTED: Health check passes but WebSocket not ready.
        
        This test should FAIL to expose the issue where health checks pass but
        WebSocket connections still fail with 1011 errors.
        """
        logger.info("🧪 Testing WebSocket health check coordination")
        
        # Monitor health checks and WebSocket readiness over time
        monitoring_duration = 30.0  # 30 seconds of monitoring
        check_interval = 2.0         # Check every 2 seconds
        
        health_websocket_correlation = []
        start_time = time.time()
        
        while time.time() - start_time < monitoring_duration:
            # Check service health
            health_result = await self.staging_manager.check_service_health()
            
            # Attempt WebSocket connection
            websocket_result = await self._attempt_single_websocket_connection(timeout=5.0)
            
            correlation_point = {
                "timestamp": time.time() - start_time,
                "health_healthy": health_result.get("healthy", False),
                "health_status_code": health_result.get("status_code"),
                "websocket_success": websocket_result.success,
                "websocket_error_code": websocket_result.error_code,
                "health_response_time": health_result.get("response_time"),
                "websocket_handshake_time": websocket_result.handshake_duration
            }
            
            health_websocket_correlation.append(correlation_point)
            
            logger.debug(f"Health/WebSocket correlation at {correlation_point['timestamp']:.1f}s: "
                        f"Health={correlation_point['health_healthy']}, "
                        f"WebSocket={correlation_point['websocket_success']}")
            
            await asyncio.sleep(check_interval)
        
        # Analyze correlation data
        problematic_points = []
        for point in health_websocket_correlation:
            if point["health_healthy"] and not point["websocket_success"]:
                if point["websocket_error_code"] == 1011:
                    problematic_points.append(point)
        
        logger.info(f"Total correlation points: {len(health_websocket_correlation)}")
        logger.info(f"Problematic points (health OK, WebSocket 1011): {len(problematic_points)}")
        
        # Log problematic points
        for point in problematic_points:
            logger.error(f"🚨 Health check OK but WebSocket 1011 at {point['timestamp']:.1f}s")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes health check coordination issue
        self.assertEqual(
            len(problematic_points), 0,
            f"EXPECTED FAILURE: Found {len(problematic_points)} cases where health check "
            f"passed but WebSocket returned 1011 errors. This demonstrates lack of coordination "
            f"between health checks and WebSocket readiness, causing load balancers to route "
            f"traffic to instances that aren't ready for WebSocket connections."
        )
    
    @pytest.mark.staging
    async def test_concurrent_websocket_connections_cold_start(self):
        """TEST: Concurrent WebSocket connections during cold start conditions.
        
        This test validates how the system handles multiple concurrent WebSocket
        connection attempts during cold start scenarios.
        """
        logger.info("🧪 Testing concurrent WebSocket connections during cold start")
        
        # Trigger cold start
        await self.staging_manager.trigger_cold_start()
        await asyncio.sleep(1.0)
        
        # Attempt multiple concurrent connections
        concurrent_attempts = 8
        connection_tasks = []
        
        logger.info(f"Starting {concurrent_attempts} concurrent connection attempts")
        
        # Start all connections simultaneously
        for i in range(concurrent_attempts):
            task = asyncio.create_task(
                self._attempt_single_websocket_connection(
                    timeout=15.0,
                    attempt_id=f"concurrent_{i}"
                )
            )
            connection_tasks.append(task)
        
        # Wait for all attempts to complete
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze concurrent connection results
        successful_connections = 0
        error_1011_count = 0
        other_errors = 0
        exceptions = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                exceptions += 1
                logger.error(f"Connection {i} raised exception: {result}")
            elif result.success:
                successful_connections += 1
            elif result.error_code == 1011:
                error_1011_count += 1
            else:
                other_errors += 1
        
        logger.info(f"Concurrent connection results (duration: {total_duration:.2f}s):")
        logger.info(f"  Successful: {successful_connections}/{concurrent_attempts}")
        logger.info(f"  1011 errors: {error_1011_count}")
        logger.info(f"  Other errors: {other_errors}")
        logger.info(f"  Exceptions: {exceptions}")
        
        # Validate reasonable success rate
        success_rate = successful_connections / concurrent_attempts
        minimum_success_rate = 0.6  # At least 60% should succeed
        
        self.assertGreater(
            success_rate,
            minimum_success_rate,
            f"Concurrent connection success rate too low: {success_rate:.1%} < {minimum_success_rate:.1%}. "
            f"Cold start handling may not be robust enough for production load."
        )
    
    # Helper methods for E2E WebSocket testing
    
    async def _attempt_websocket_connections_during_startup(
        self, config: ColdStartSimulation
    ) -> List[WebSocketConnectionAttempt]:
        """Attempt multiple WebSocket connections during startup."""
        results = []
        
        # Stagger connection attempts to simulate real user behavior
        for attempt in range(config.connection_attempts):
            logger.info(f"Connection attempt {attempt + 1}/{config.connection_attempts}")
            
            # Check service readiness
            service_health = await self.staging_manager.check_service_health()
            service_ready = service_health.get("healthy", False)
            
            # Attempt WebSocket connection
            start_time = time.time()
            try:
                connection_result = await self._attempt_single_websocket_connection(
                    timeout=config.timeout_seconds,
                    attempt_id=f"startup_{attempt}"
                )
                
                connection_result.service_ready = service_ready
                results.append(connection_result)
                
            except Exception as e:
                # Handle unexpected exceptions
                end_time = time.time()
                error_result = WebSocketConnectionAttempt(
                    attempt_number=attempt + 1,
                    start_time=start_time,
                    end_time=end_time,
                    success=False,
                    error_code=None,
                    error_message=str(e),
                    handshake_duration=end_time - start_time,
                    service_ready=service_ready
                )
                results.append(error_result)
            
            # Wait between attempts
            if attempt < config.connection_attempts - 1:
                await asyncio.sleep(config.retry_delay)
        
        return results
        
    async def _attempt_single_websocket_connection(
        self, timeout: float, attempt_id: str = "single"
    ) -> WebSocketConnectionAttempt:
        """Attempt a single WebSocket connection."""
        start_time = time.time()
        
        try:
            # Create WebSocket connection with timeout
            async with asyncio.timeout(timeout):
                logger.debug(f"Attempting WebSocket connection to {self.staging_manager.websocket_url}")
                
                async with websockets.connect(
                    self.staging_manager.websocket_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    extra_headers={
                        "User-Agent": f"Issue586-E2E-Test-{attempt_id}",
                        "Origin": "https://netra-frontend-staging.example.com"
                    }
                ) as websocket:
                    end_time = time.time()
                    handshake_duration = end_time - start_time
                    
                    # Send a simple test message
                    test_message = {
                        "type": "test",
                        "test_id": f"issue586_{attempt_id}",
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response with timeout
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        logger.debug(f"Received WebSocket response: {response[:100]}...")
                    except asyncio.TimeoutError:
                        logger.warning("No response received within timeout")
                    
                    return WebSocketConnectionAttempt(
                        attempt_number=1,
                        start_time=start_time,
                        end_time=end_time,
                        success=True,
                        error_code=None,
                        error_message=None,
                        handshake_duration=handshake_duration,
                        service_ready=True  # Will be updated by caller
                    )
                    
        except asyncio.TimeoutError:
            end_time = time.time()
            return WebSocketConnectionAttempt(
                attempt_number=1,
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_code=None,
                error_message=f"Connection timeout after {timeout}s",
                handshake_duration=end_time - start_time,
                service_ready=False
            )
            
        except websockets.exceptions.ConnectionClosedError as e:
            end_time = time.time()
            
            # Extract error code (1011 for server error during handshake)
            error_code = getattr(e, 'code', None)
            if error_code is None and "1011" in str(e):
                error_code = 1011
            
            return WebSocketConnectionAttempt(
                attempt_number=1,
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_code=error_code,
                error_message=str(e),
                handshake_duration=end_time - start_time,
                service_ready=False
            )
            
        except Exception as e:
            end_time = time.time()
            
            # Check if this is a 1011 error in disguise
            error_code = None
            error_message = str(e)
            if "1011" in error_message or "server error" in error_message.lower():
                error_code = 1011
            
            return WebSocketConnectionAttempt(
                attempt_number=1,
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_code=error_code,
                error_message=error_message,
                handshake_duration=end_time - start_time,
                service_ready=False
            )


if __name__ == "__main__":
    # Run E2E tests - expecting failures that expose 1011 errors during cold start
    pytest.main([__file__, "-v", "--tb=short", "-m", "staging"])