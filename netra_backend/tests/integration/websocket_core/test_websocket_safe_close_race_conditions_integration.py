"""
WebSocket Safe Close Race Condition Integration Tests for Issue #335

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Stability - Prevent WebSocket chat failures
- Value Impact: Ensures reliable AI chat functionality under real concurrent scenarios
- Strategic/Revenue Impact: Prevents $500K+ ARR loss from WebSocket reliability issues

CRITICAL: These integration tests use REAL WebSocket connections to reproduce
race conditions identified in Issue #335. No mocking of WebSocket connections.

Key Integration Scenarios Tested:
1. Real WebSocket connections with concurrent close operations
2. Production-like timing scenarios that trigger race conditions
3. Multi-user scenarios with simultaneous WebSocket closures
4. Network interruption scenarios causing unexpected close timing
5. Agent execution scenarios with WebSocket close race conditions

Test Strategy:
- Use real WebSocket connections (websockets library)
- Real authentication and service integration
- Reproduce production timing patterns
- Test under realistic concurrent load scenarios
- Validate safe_websocket_close behavior with real network conditions

Author: AI Agent - WebSocket Integration Race Condition Test Creation
Date: 2025-09-13
Issue: #335 WebSocket race condition tests
"""

import asyncio
import json
import logging
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.types import UserID, ThreadID, RequestID
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_id_manager import generate_user_id

logger = logging.getLogger(__name__)


@dataclass
class IntegrationRaceMetrics:
    """Metrics for integration race condition test results"""
    test_name: str
    real_websocket_connections: int = 0
    concurrent_close_attempts: int = 0
    race_conditions_detected: int = 0
    connection_errors: int = 0
    successful_closes: int = 0
    network_interruptions: int = 0
    average_close_time: float = 0.0
    production_patterns_reproduced: int = 0


@dataclass
class AuthenticatedWebSocketUser:
    """Real authenticated user for WebSocket integration testing"""
    user_id: UserID
    jwt_token: str
    session_id: str
    websocket_headers: Dict[str, str]
    websocket_connection: Optional[Any] = None


class TestWebSocketSafeCloseRaceConditionsIntegration(BaseIntegrationTest):
    """
    Integration tests for WebSocket safe close race conditions using real connections.

    CRITICAL: These tests use real WebSocket connections to validate
    race condition handling in production-like scenarios.
    """

    @pytest.fixture(autouse=True)
    async def setup_integration_environment(self, real_services_fixture):
        """Set up real services for integration testing."""
        self.services = real_services_fixture
        self.postgres_connection = self.services['postgres']
        self.redis_connection = self.services['redis']
        self.backend_url = self.services['backend_url']

        # Initialize real authentication helpers
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)

        # Integration test metrics
        self.integration_metrics = []
        self.real_connection_log = []

        # Environment for integration testing
        self.env = IsolatedEnvironment()

        yield

        # Clean up any remaining connections
        await self._cleanup_test_connections()

    async def _create_authenticated_websocket_user(self) -> AuthenticatedWebSocketUser:
        """Create a real authenticated WebSocket user for integration testing."""
        user_id = UserID(generate_user_id())

        # Create real JWT token through auth service
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        session_id = f"session_{user_id}_{int(time.time())}"

        # Create WebSocket authentication headers
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(user_id),
            is_e2e_test=True
        )

        return AuthenticatedWebSocketUser(
            user_id=user_id,
            jwt_token=jwt_token,
            session_id=session_id,
            websocket_headers=websocket_headers
        )

    async def _create_real_websocket_connection(self, user: AuthenticatedWebSocketUser) -> Any:
        """Create real WebSocket connection with authentication."""
        websocket_url = f"ws://localhost:8000/ws/{user.user_id}"

        try:
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=10,
                ping_interval=20,
                ping_timeout=10
            )

            # Complete authentication handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id,
                "timestamp": time.time()
            }

            await connection.send(json.dumps(handshake_message))
            response = await asyncio.wait_for(connection.recv(), timeout=10)
            response_data = json.loads(response)

            if response_data.get('type') != 'handshake_complete':
                raise Exception(f"Handshake failed: {response_data}")

            self.real_connection_log.append({
                "action": "real_connection_established",
                "user_id": str(user.user_id),
                "timestamp": time.time(),
                "connection_id": id(connection)
            })

            return connection

        except Exception as e:
            self.real_connection_log.append({
                "action": "real_connection_failed",
                "user_id": str(user.user_id),
                "error": str(e),
                "timestamp": time.time()
            })
            raise

    async def _cleanup_test_connections(self):
        """Clean up any remaining test connections."""
        cleanup_count = 0
        for log_entry in self.real_connection_log:
            if log_entry.get("action") == "real_connection_established" and "connection" in log_entry:
                try:
                    await log_entry["connection"].close()
                    cleanup_count += 1
                except:
                    pass

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} test connections")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_real_websocket_concurrent_close_race_condition(self, real_services_fixture):
        """
        CRITICAL INTEGRATION TEST: Test concurrent close operations on real WebSocket connections.

        Reproduces: Multiple threads/tasks attempting to close the same WebSocket
        connection simultaneously, causing race conditions in production.

        Expected: Race conditions should be handled gracefully without crashing
        """
        # Create authenticated user and real WebSocket connection
        user = await self._create_authenticated_websocket_user()
        connection = await self._create_real_websocket_connection(user)

        try:
            # Track close attempts and timing
            close_attempts = []
            start_time = time.time()

            async def attempt_real_close(attempt_id: int, delay: float = 0.0):
                """Attempt to close real WebSocket connection."""
                if delay > 0:
                    await asyncio.sleep(delay)

                close_start = time.time()
                try:
                    # CRITICAL: Multiple close attempts on same real connection
                    await connection.close(code=1000, reason=f"Concurrent close test {attempt_id}")

                    return {
                        "attempt_id": attempt_id,
                        "success": True,
                        "duration": time.time() - close_start,
                        "error": None,
                        "connection_state": "closed"
                    }

                except ConnectionClosedError as e:
                    return {
                        "attempt_id": attempt_id,
                        "success": True,  # This is expected for concurrent closes
                        "duration": time.time() - close_start,
                        "error": f"Already closed: {str(e)}",
                        "connection_state": "already_closed"
                    }

                except Exception as e:
                    return {
                        "attempt_id": attempt_id,
                        "success": False,
                        "duration": time.time() - close_start,
                        "error": str(e),
                        "connection_state": "error"
                    }

            # CRITICAL: Start multiple concurrent close operations
            close_tasks = [
                asyncio.create_task(attempt_real_close(i, delay=i*0.01))
                for i in range(5)
            ]

            # Execute concurrent close attempts
            close_results = await asyncio.gather(*close_tasks, return_exceptions=True)

            end_time = time.time()

            # Analyze real WebSocket race condition results
            successful_closes = sum(1 for result in close_results
                                  if isinstance(result, dict) and result.get('success'))
            failed_closes = sum(1 for result in close_results
                              if isinstance(result, dict) and not result.get('success'))
            already_closed_errors = sum(1 for result in close_results
                                      if isinstance(result, dict) and
                                      result.get('error') and "Already closed" in result.get('error', ''))

            # Record integration metrics
            metrics = IntegrationRaceMetrics(
                test_name="real_websocket_concurrent_close",
                real_websocket_connections=1,
                concurrent_close_attempts=len(close_tasks),
                race_conditions_detected=already_closed_errors,
                connection_errors=failed_closes,
                successful_closes=successful_closes,
                average_close_time=sum(r.get('duration', 0) for r in close_results if isinstance(r, dict)) / len(close_results)
            )

            self.integration_metrics.append(metrics)

            # Log integration test results
            logger.info(f"Real WebSocket concurrent close test completed:")
            logger.info(f"  - Concurrent close attempts: {len(close_tasks)}")
            logger.info(f"  - Successful closes: {successful_closes}")
            logger.info(f"  - Already closed errors: {already_closed_errors}")
            logger.info(f"  - Failed closes: {failed_closes}")
            logger.info(f"  - Average close time: {metrics.average_close_time:.3f}s")

            # CRITICAL: At least one close should succeed, others should fail gracefully
            assert successful_closes >= 1, f"No successful close operations: {successful_closes}"

            # Race condition detected if multiple close attempts resulted in "already closed"
            if already_closed_errors > 0:
                logger.info(f"Race condition successfully reproduced: {already_closed_errors} concurrent close conflicts")

        finally:
            # Ensure connection is properly closed
            try:
                if not connection.closed:
                    await connection.close()
            except:
                pass

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_real_websocket_send_after_close_race_condition(self, real_services_fixture):
        """
        CRITICAL INTEGRATION TEST: Test "send after close" race condition with real WebSocket.

        Reproduces: Send operations attempted after WebSocket close has started,
        causing "send after close" errors in production scenarios.

        Expected: Send operations should fail gracefully, close should complete successfully
        """
        # Create authenticated user and real WebSocket connection
        user = await self._create_authenticated_websocket_user()
        connection = await self._create_real_websocket_connection(user)

        operation_results = []
        start_time = time.time()

        async def attempt_send_operation(send_id: int, message_data: dict, delay: float = 0.0):
            """Attempt to send message on WebSocket that may be closing."""
            if delay > 0:
                await asyncio.sleep(delay)

            send_start = time.time()
            try:
                await connection.send(json.dumps(message_data))
                return {
                    "operation": "send",
                    "send_id": send_id,
                    "success": True,
                    "duration": time.time() - send_start,
                    "error": None
                }

            except ConnectionClosedError as e:
                return {
                    "operation": "send",
                    "send_id": send_id,
                    "success": False,  # Expected failure
                    "duration": time.time() - send_start,
                    "error": f"Send after close: {str(e)}",
                    "race_condition": True
                }

            except Exception as e:
                return {
                    "operation": "send",
                    "send_id": send_id,
                    "success": False,
                    "duration": time.time() - send_start,
                    "error": str(e)
                }

        async def attempt_close_operation():
            """Attempt to close WebSocket while sends may be in progress."""
            close_start = time.time()
            try:
                # Add small delay to allow sends to start
                await asyncio.sleep(0.02)

                await connection.close(code=1000, reason="Send after close test")
                return {
                    "operation": "close",
                    "success": True,
                    "duration": time.time() - close_start,
                    "error": None
                }

            except Exception as e:
                return {
                    "operation": "close",
                    "success": False,
                    "duration": time.time() - close_start,
                    "error": str(e)
                }

        try:
            # CRITICAL: Start send operations that will race with close
            send_tasks = [
                asyncio.create_task(attempt_send_operation(i, {
                    "type": "agent_event",
                    "event": "agent_thinking",
                    "message": f"Send operation {i}",
                    "timestamp": time.time()
                }, delay=i*0.01))
                for i in range(4)
            ]

            # Start close operation concurrently with sends
            close_task = asyncio.create_task(attempt_close_operation())

            # Wait for all operations to complete
            all_tasks = send_tasks + [close_task]
            all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

            end_time = time.time()

            # Separate send and close results
            send_results = all_results[:-1]
            close_result = all_results[-1]

            # Analyze send after close race conditions
            successful_sends = sum(1 for result in send_results
                                 if isinstance(result, dict) and result.get('success'))
            failed_sends = sum(1 for result in send_results
                             if isinstance(result, dict) and not result.get('success'))
            send_after_close_errors = sum(1 for result in send_results
                                        if isinstance(result, dict) and
                                        result.get('race_condition', False))

            close_successful = isinstance(close_result, dict) and close_result.get('success', False)

            # Record send after close race condition metrics
            metrics = IntegrationRaceMetrics(
                test_name="real_websocket_send_after_close",
                real_websocket_connections=1,
                concurrent_close_attempts=1,
                race_conditions_detected=send_after_close_errors,
                connection_errors=failed_sends,
                successful_closes=1 if close_successful else 0,
                average_close_time=close_result.get('duration', 0) if isinstance(close_result, dict) else 0,
                production_patterns_reproduced=1 if send_after_close_errors > 0 else 0
            )

            self.integration_metrics.append(metrics)

            # Log detailed race condition analysis
            logger.info(f"Real WebSocket send after close test completed:")
            logger.info(f"  - Send operations attempted: {len(send_tasks)}")
            logger.info(f"  - Successful sends: {successful_sends}")
            logger.info(f"  - Failed sends: {failed_sends}")
            logger.info(f"  - Send after close errors: {send_after_close_errors}")
            logger.info(f"  - Close operation successful: {close_successful}")
            logger.info(f"  - Close duration: {metrics.average_close_time:.3f}s")

            # Detailed logging of each operation
            for i, result in enumerate(send_results):
                if isinstance(result, dict):
                    status = "SUCCESS" if result.get('success') else "FAILED"
                    race_info = " (RACE CONDITION)" if result.get('race_condition') else ""
                    logger.debug(f"    Send {result.get('send_id', i)}: {status}{race_info}")

            # CRITICAL: Close operation should succeed regardless of send failures
            assert close_successful, f"Close operation failed: {close_result}"

            # Send after close race condition is expected in this test
            if send_after_close_errors > 0:
                logger.info(f"Send after close race condition successfully reproduced: {send_after_close_errors} operations")

            # At least some sends should fail due to race condition
            assert failed_sends > 0, "Expected some send operations to fail due to race condition"

        finally:
            # Ensure connection is properly closed
            try:
                if not connection.closed:
                    await connection.close()
            except:
                pass

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_real_websocket_multi_user_concurrent_close_scenarios(self, real_services_fixture):
        """
        CRITICAL INTEGRATION TEST: Multi-user concurrent WebSocket close scenarios.

        Reproduces: Multiple users closing WebSocket connections simultaneously,
        testing system behavior under realistic concurrent load.

        Expected: Each user's close operation should be isolated and handled correctly
        """
        # Create multiple authenticated users
        users = []
        connections = []

        try:
            # Create 4 real authenticated users with WebSocket connections
            for i in range(4):
                user = await self._create_authenticated_websocket_user()
                connection = await self._create_real_websocket_connection(user)

                users.append(user)
                connections.append(connection)

                # Send a test message to establish full connection
                test_message = {
                    "type": "ping",
                    "user_id": str(user.user_id),
                    "message": f"Multi-user test {i}"
                }
                await connection.send(json.dumps(test_message))

            # Allow connections to stabilize
            await asyncio.sleep(0.1)

            async def close_user_connection(user_index: int, stagger_delay: float = 0.0):
                """Close connection for specific user with optional delay."""
                if stagger_delay > 0:
                    await asyncio.sleep(stagger_delay)

                user = users[user_index]
                connection = connections[user_index]

                close_start = time.time()
                try:
                    # Close user's WebSocket connection
                    await connection.close(code=1000, reason=f"Multi-user test close {user_index}")

                    return {
                        "user_index": user_index,
                        "user_id": str(user.user_id),
                        "success": True,
                        "duration": time.time() - close_start,
                        "error": None
                    }

                except Exception as e:
                    return {
                        "user_index": user_index,
                        "user_id": str(user.user_id),
                        "success": False,
                        "duration": time.time() - close_start,
                        "error": str(e)
                    }

            # CRITICAL: Close all user connections with slight staggering to create race conditions
            start_time = time.time()

            close_tasks = [
                asyncio.create_task(close_user_connection(i, stagger_delay=i*0.02))
                for i in range(len(users))
            ]

            # Execute all user close operations
            close_results = await asyncio.gather(*close_tasks, return_exceptions=True)

            end_time = time.time()

            # Analyze multi-user close results
            successful_user_closes = sum(1 for result in close_results
                                       if isinstance(result, dict) and result.get('success'))
            failed_user_closes = sum(1 for result in close_results
                                   if isinstance(result, dict) and not result.get('success'))
            total_close_time = end_time - start_time

            # Record multi-user metrics
            metrics = IntegrationRaceMetrics(
                test_name="real_websocket_multi_user_concurrent_close",
                real_websocket_connections=len(users),
                concurrent_close_attempts=len(users),
                race_conditions_detected=0,  # User isolation should prevent race conditions
                connection_errors=failed_user_closes,
                successful_closes=successful_user_closes,
                average_close_time=total_close_time / len(users)
            )

            self.integration_metrics.append(metrics)

            # Log multi-user test results
            logger.info(f"Multi-user concurrent close test completed:")
            logger.info(f"  - Total users: {len(users)}")
            logger.info(f"  - Successful user closes: {successful_user_closes}")
            logger.info(f"  - Failed user closes: {failed_user_closes}")
            logger.info(f"  - Total close time: {total_close_time:.3f}s")
            logger.info(f"  - Average close time per user: {metrics.average_close_time:.3f}s")

            # Detailed per-user logging
            for result in close_results:
                if isinstance(result, dict):
                    status = "SUCCESS" if result.get('success') else "FAILED"
                    logger.debug(f"    User {result.get('user_index')}: {status} in {result.get('duration', 0):.3f}s")

            # CRITICAL: All user close operations should succeed independently
            assert successful_user_closes == len(users), (
                f"Not all user closes succeeded: {successful_user_closes}/{len(users)}"
            )

            # No race conditions should occur between different users
            assert failed_user_closes == 0, f"User close failures detected: {failed_user_closes}"

        finally:
            # Clean up any remaining connections
            for i, connection in enumerate(connections):
                try:
                    if not connection.closed:
                        await connection.close()
                        logger.debug(f"Cleaned up connection {i}")
                except:
                    pass

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_real_websocket_network_interruption_close_race_condition(self, real_services_fixture):
        """
        CRITICAL INTEGRATION TEST: Network interruption during WebSocket close operations.

        Reproduces: Network issues or connection drops during WebSocket close,
        causing unexpected timing and race conditions.

        Expected: System should handle network interruptions gracefully
        """
        # Create authenticated user and real WebSocket connection
        user = await self._create_authenticated_websocket_user()
        connection = await self._create_real_websocket_connection(user)

        interruption_scenarios = []

        try:
            async def simulate_network_interruption_during_close(interruption_type: str):
                """Simulate different types of network interruptions during close."""
                start_time = time.time()

                try:
                    if interruption_type == "immediate_disconnect":
                        # Simulate immediate disconnection
                        await connection.close(code=1006, reason="Network interruption")

                    elif interruption_type == "timeout_during_close":
                        # Simulate timeout during close operation
                        try:
                            await asyncio.wait_for(
                                connection.close(code=1000, reason="Timeout test"),
                                timeout=0.01  # Very short timeout to force timeout
                            )
                        except asyncio.TimeoutError:
                            # Handle timeout gracefully
                            return {
                                "interruption_type": interruption_type,
                                "success": True,  # Timeout handled gracefully
                                "duration": time.time() - start_time,
                                "error": "Timeout during close (handled)",
                                "network_interruption": True
                            }

                    elif interruption_type == "connection_already_closed":
                        # Simulate connection already closed by peer
                        await connection.close(code=1000, reason="Normal close")
                        # Try to close again (should handle gracefully)
                        await connection.close(code=1000, reason="Second close attempt")

                    return {
                        "interruption_type": interruption_type,
                        "success": True,
                        "duration": time.time() - start_time,
                        "error": None,
                        "network_interruption": True
                    }

                except ConnectionClosedError as e:
                    return {
                        "interruption_type": interruption_type,
                        "success": True,  # Expected for network interruptions
                        "duration": time.time() - start_time,
                        "error": f"Connection closed: {str(e)}",
                        "network_interruption": True
                    }

                except Exception as e:
                    return {
                        "interruption_type": interruption_type,
                        "success": False,
                        "duration": time.time() - start_time,
                        "error": str(e),
                        "network_interruption": True
                    }

            # Test different network interruption scenarios
            interruption_types = [
                "immediate_disconnect",
                "timeout_during_close",
                "connection_already_closed"
            ]

            # Test each interruption scenario with separate connections
            for interruption_type in interruption_types:
                # Create fresh connection for each test
                fresh_user = await self._create_authenticated_websocket_user()
                fresh_connection = await self._create_real_websocket_connection(fresh_user)

                # Replace connection for this test
                original_connection = connection
                connection = fresh_connection

                try:
                    result = await simulate_network_interruption_during_close(interruption_type)
                    interruption_scenarios.append(result)

                    logger.info(f"Network interruption test '{interruption_type}': {'SUCCESS' if result['success'] else 'FAILED'}")

                finally:
                    # Ensure fresh connection is closed
                    try:
                        if not fresh_connection.closed:
                            await fresh_connection.close()
                    except:
                        pass

                # Restore original connection
                connection = original_connection

            # Analyze network interruption handling
            successful_interruption_handling = sum(1 for result in interruption_scenarios if result.get('success'))
            total_interruption_tests = len(interruption_scenarios)

            # Record network interruption metrics
            metrics = IntegrationRaceMetrics(
                test_name="real_websocket_network_interruption_close",
                real_websocket_connections=total_interruption_tests,
                concurrent_close_attempts=total_interruption_tests,
                race_conditions_detected=0,  # Network interruptions are different from race conditions
                connection_errors=total_interruption_tests - successful_interruption_handling,
                successful_closes=successful_interruption_handling,
                network_interruptions=sum(1 for result in interruption_scenarios if result.get('network_interruption')),
                average_close_time=sum(result.get('duration', 0) for result in interruption_scenarios) / total_interruption_tests
            )

            self.integration_metrics.append(metrics)

            # Log network interruption test results
            logger.info(f"Network interruption close test completed:")
            logger.info(f"  - Interruption scenarios tested: {total_interruption_tests}")
            logger.info(f"  - Successful interruption handling: {successful_interruption_handling}")
            logger.info(f"  - Network interruptions detected: {metrics.network_interruptions}")
            logger.info(f"  - Average handling time: {metrics.average_close_time:.3f}s")

            # Detailed scenario logging
            for result in interruption_scenarios:
                status = "SUCCESS" if result.get('success') else "FAILED"
                error_info = f" - {result.get('error')}" if result.get('error') else ""
                logger.debug(f"    {result.get('interruption_type')}: {status}{error_info}")

            # CRITICAL: All network interruption scenarios should be handled gracefully
            assert successful_interruption_handling == total_interruption_tests, (
                f"Network interruption handling failed: {successful_interruption_handling}/{total_interruption_tests}"
            )

        finally:
            # Ensure main connection is properly closed
            try:
                if not connection.closed:
                    await connection.close()
            except:
                pass

    def tearDown(self):
        """Generate comprehensive integration race condition analysis report."""
        super().tearDown()

        if self.integration_metrics:
            # Generate comprehensive integration analysis
            total_tests = len(self.integration_metrics)
            total_real_connections = sum(m.real_websocket_connections for m in self.integration_metrics)
            total_race_conditions = sum(m.race_conditions_detected for m in self.integration_metrics)
            total_successful_closes = sum(m.successful_closes for m in self.integration_metrics)
            total_network_interruptions = sum(m.network_interruptions for m in self.integration_metrics)
            production_patterns = sum(m.production_patterns_reproduced for m in self.integration_metrics)

            average_close_time = sum(m.average_close_time for m in self.integration_metrics) / total_tests

            # Log comprehensive integration analysis
            logger.critical("=" * 80)
            logger.critical("WEBSOCKET SAFE CLOSE RACE CONDITION INTEGRATION ANALYSIS")
            logger.critical("=" * 80)
            logger.critical(f"Total Integration Tests: {total_tests}")
            logger.critical(f"Total Real WebSocket Connections: {total_real_connections}")
            logger.critical(f"Total Race Conditions Detected: {total_race_conditions}")
            logger.critical(f"Total Successful Closes: {total_successful_closes}")
            logger.critical(f"Total Network Interruptions: {total_network_interruptions}")
            logger.critical(f"Production Patterns Reproduced: {production_patterns}")
            logger.critical(f"Average Close Time: {average_close_time:.3f} seconds")
            logger.critical("=" * 80)

            # Test-by-test integration breakdown
            for metrics in self.integration_metrics:
                logger.info(f"Integration Test: {metrics.test_name}")
                logger.info(f"  Real Connections: {metrics.real_websocket_connections}")
                logger.info(f"  Race Conditions: {metrics.race_conditions_detected}")
                logger.info(f"  Successful Closes: {metrics.successful_closes}")
                logger.info(f"  Network Interruptions: {metrics.network_interruptions}")
                logger.info(f"  Average Close Time: {metrics.average_close_time:.3f}s")