""""""
E2E Test: WebSocket Golden Path Resource Limits on GCP Staging

This test validates the WebSocket Manager Emergency Cleanup Failure in the
full Golden Path user flow on GCP Staging environment.

REPRODUCTION TARGET:
- Real user authentication through staging auth service
- Real WebSocket connections to GCP staging infrastructure
- Real agent execution with resource limits
- Emergency cleanup under actual production conditions

GOLDEN PATH CONTEXT:
- User login → WebSocket connection → Agent execution → AI response
- Resource exhaustion during peak usage simulation
- Connection limit enforcement in production-like environment

BUSINESS IMPACT:
- Validates $500K+ ARR Golden Path reliability under resource pressure
- Ensures production stability during high user concurrency
- Prevents customer-facing failures during peak usage

This test requires GCP staging environment and real service connectivity.
""

import pytest
import asyncio
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager import (
    check_websocket_service_available,
    get_websocket_manager,
    create_test_user_context
)
from netra_backend.app.websocket_core.websocket_manager import MAX_CONNECTIONS_PER_USER
from netra_backend.app.websocket_core.types import WebSocketManagerMode
from shared.types.core_types import ensure_user_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import staging environment validation
try:
    from netra_backend.app.core.configuration.base import get_config
    from netra_backend.app.auth_integration.auth import AuthenticationService
    STAGING_AVAILABLE = True
except ImportError:
    STAGING_AVAILABLE = False

# Import WebSocket client for real connection testing
try:
    import websockets
    from websockets.exceptions import ConnectionClosed, InvalidURI
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False

# Import HTTP client for staging API testing
try:
    import httpx
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False


class TestWebSocketGoldenPathResourceLimits(SSotAsyncTestCase):
""""""
    E2E tests for WebSocket resource limits in Golden Path user flow on GCP Staging.

    These tests validate the complete user experience under resource pressure:
    - Real authentication and session management
    - Real WebSocket connections to staging infrastructure
    - Real agent execution and AI interactions
    - Resource limit enforcement in production-like conditions
""

    def setup_method(self, method):
        "Setup E2E test environment with GCP staging connectivity."""
        super().setup_method(method)

        # Skip if staging environment not available
        if not (STAGING_AVAILABLE and WEBSOCKET_CLIENT_AVAILABLE and HTTP_CLIENT_AVAILABLE):
            pytest.skip(GCP Staging environment or required dependencies not available")"

        self.id_manager = UnifiedIDManager()

        # Create test users for E2E scenarios
        self.test_users = {
            'golden_path_user': ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix=e2e_golden)),
            'concurrent_user_1': ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix=e2e_concurrent1)),""
            'concurrent_user_2': ensure_user_id(self.id_manager.generate_id(IDType.USER, prefix="e2e_concurrent2))"
        }

        # Track real connections and sessions for cleanup
        self.active_websockets: List[Any] = []
        self.active_sessions: Dict[str, str] = {}  # user_id -> session_token
        self.staging_metrics: Dict[str, Any] = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'cleanup_failures': 0,
            'golden_path_completions': 0,
            'resource_limit_hits': 0,
            'staging_errors': []
        }

        # Get staging configuration
        try:
            self.config = get_config()
            self.staging_websocket_url = self._get_staging_websocket_url()
            self.staging_api_url = self._get_staging_api_url()
        except Exception as e:
            pytest.skip(fStaging configuration not available: {e})

    async def teardown_method(self, method):
        "Comprehensive cleanup of E2E test resources."
        cleanup_start = time.time()

        # Close all real WebSocket connections
        for websocket in self.active_websockets:
            try:
                await websocket.close()
            except Exception as e:
                self.logger.warning(fFailed to close WebSocket connection: {e})""

        # Invalidate all staging sessions
        for user_id, session_token in self.active_sessions.items():
            try:
                await self._invalidate_staging_session(session_token)
            except Exception as e:
                self.logger.warning(f"Failed to invalidate session for {user_id}: {e})"

        cleanup_time = time.time() - cleanup_start
        self.logger.info(fE2E cleanup completed in {cleanup_time:.3f}s)
        self.logger.info(fStaging metrics: {self.staging_metrics})

        await super().teardown_method(method)

    def _get_staging_websocket_url(self) -> str:
        ""Get the staging WebSocket URL from configuration.
        # Use the corrected staging domain per Issue #1278 fix
        return wss://api.staging.netrasystems.ai/ws""

    def _get_staging_api_url(self) -> str:
        "Get the staging API URL from configuration."""
        # Use the corrected staging domain per Issue #1278 fix
        return "https://staging.netrasystems.ai/api"

    async def _authenticate_staging_user(self, user_id: str) -> str:
        Authenticate a test user with staging auth service and return session token.""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use staging-appropriate test authentication
                auth_payload = {
                    "user_id: user_id,"""
                    test_mode: True,
                    "e2e_test: True"
                }

                response = await client.post(
                    f{self.staging_api_url}/auth/test-login,
                    json=auth_payload,
                    headers={Content-Type: application/json"}"

                if response.status_code == 200:
                    auth_data = response.json()
                    session_token = auth_data.get("session_token) or auth_data.get(access_token)"

                    if session_token:
                        self.active_sessions[user_id] = session_token
                        return session_token
                    else:
                        raise Exception(No session token in auth response)

                else:
                    self.staging_metrics['staging_errors'].append({
                        'type': 'auth_failure',
                        'status_code': response.status_code,
                        'response': response.text[:200]
                    }
                    raise Exception(fAuthentication failed: {response.status_code} {response.text}")"

        except Exception as e:
            self.logger.error(fStaging authentication failed for {user_id}: {e})
            raise

    async def _invalidate_staging_session(self, session_token: str):
        Invalidate a staging session token.""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(
                    f{self.staging_api_url}/auth/logout,
                    headers={Authorization: fBearer {session_token}}
        except Exception as e:
            self.logger.warning(fFailed to invalidate staging session: {e})""

    async def _create_staging_websocket_connection(self, user_id: str, session_token: str) -> Any:
        "Create a real WebSocket connection to GCP staging infrastructure."""
        try:
            self.staging_metrics['connection_attempts'] += 1

            # Create WebSocket connection with authentication
            headers = {
                Authorization": f"Bearer {session_token},
                X-User-ID: user_id,
                X-Test-Mode: e2e
            }

            websocket = await websockets.connect(
                self.staging_websocket_url,
                extra_headers=headers,
                timeout=30,
                ping_timeout=20,
                ping_interval=30
            )

            self.active_websockets.append(websocket)
            self.staging_metrics['successful_connections'] += 1

            return websocket

        except Exception as e:
            self.staging_metrics['staging_errors'].append({
                'type': 'websocket_connection_failure',
                'user_id': user_id,
                'error': str(e)
            }
            raise

    async def _execute_golden_path_with_websocket(self, websocket: Any, user_id: str) -> Dict[str, Any]:
        "Execute the Golden Path user flow with a real WebSocket connection."
        golden_path_start = time.time()

        try:
            # Send initial Golden Path message (agent execution request)
            golden_path_message = {
                type: "agent_execution_request,"
                user_id": user_id,"
                request_id: self.id_manager.generate_id(IDType.REQUEST, prefix=golden_path),
                "message: Optimize my AI infrastructure for cost and performance",
                test_mode: True,
                e2e_test: True""
            }

            await websocket.send(json.dumps(golden_path_message))

            # Wait for Golden Path response sequence
            expected_events = [
                "agent_started,"""
                agent_thinking,
                "tool_executing,"
                tool_completed,
                agent_completed""
            ]

            received_events = []
            timeout_start = time.time()
            timeout_duration = 60.0  # 60 second timeout for Golden Path completion

            while len(received_events) < len(expected_events) and (time.time() - timeout_start) < timeout_duration:
                try:
                    # Wait for response with timeout
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)

                    event_type = response_data.get(type")"
                    if event_type in expected_events:
                        received_events.append(event_type)
                        self.logger.info(fGolden Path event received: {event_type})

                except asyncio.TimeoutError:
                    self.logger.warning(Timeout waiting for Golden Path event)""
                    break
                except ConnectionClosed:
                    self.logger.error("WebSocket connection closed during Golden Path execution)"
                    break

            golden_path_time = time.time() - golden_path_start

            # Validate Golden Path completion
            golden_path_completed = len(received_events) >= 3  # At least 3 critical events

            if golden_path_completed:
                self.staging_metrics['golden_path_completions'] += 1

            return {
                'completed': golden_path_completed,
                'events_received': received_events,
                'execution_time': golden_path_time,
                'expected_events': expected_events
            }

        except Exception as e:
            golden_path_time = time.time() - golden_path_start
            self.staging_metrics['staging_errors'].append({
                'type': 'golden_path_execution_failure',
                'user_id': user_id,
                'error': str(e),
                'execution_time': golden_path_time
            }
            raise

    async def test_golden_path_resource_limit_enforcement(self):
        
        Test Golden Path user flow under resource limit conditions on GCP staging.

        This is the primary E2E test that validates:
        1. User can complete Golden Path flow normally
        2. Resource limits are enforced during high load
        3. Emergency cleanup works in staging environment
        4. Golden Path recovery after resource exhaustion
""
        if not await check_websocket_service_available():
            pytest.skip(WebSocket service not available for E2E testing)

        self.logger.info(Testing Golden Path resource limit enforcement on GCP staging...")"

        primary_user = self.test_users['golden_path_user']

        # PHASE 1: Authenticate and establish baseline Golden Path
        session_token = await self._authenticate_staging_user(primary_user)
        self.assertIsNotNone(session_token, Should successfully authenticate with staging)

        baseline_websocket = await self._create_staging_websocket_connection(primary_user, session_token)
        baseline_result = await self._execute_golden_path_with_websocket(baseline_websocket, primary_user)

        self.assertTrue(baseline_result['completed'],
                       fBaseline Golden Path should complete successfully. ""
                       f"Events: {baseline_result['events_received']})"

        self.assertLess(baseline_result['execution_time'], 45.0,
                       fBaseline Golden Path should complete within 45 seconds, 
                       fgot {baseline_result['execution_time']:.1f}s)

        # PHASE 2: Simulate resource exhaustion by creating many connections
        resource_test_connections = []
        connection_limit_hit = False

        for i in range(MAX_CONNECTIONS_PER_USER + 5):  # Try to exceed limit
            try:
                connection_websocket = await self._create_staging_websocket_connection(primary_user, session_token)
                resource_test_connections.append(connection_websocket)

                # Test Golden Path functionality on each connection (up to 5 for performance)
                if i < 5:
                    golden_path_result = await self._execute_golden_path_with_websocket(
                        connection_websocket, primary_user
                    )
                    self.assertTrue(golden_path_result['completed'],
                                  fGolden Path should work on connection {i}")"

            except Exception as e:
                if connection limit in str(e).lower() or maximum in str(e).lower():
                    connection_limit_hit = True
                    self.staging_metrics['resource_limit_hits'] += 1
                    self.logger.info(fResource limit hit at connection {i}: {e})
                    break
                else:
                    self.staging_metrics['staging_errors'].append({
                        'type': 'unexpected_connection_error',
                        'connection_index': i,
                        'error': str(e)
                    }

        # PHASE 3: Verify resource limit enforcement
        self.assertTrue(connection_limit_hit or len(resource_test_connections) >= MAX_CONNECTIONS_PER_USER,
                       Should hit resource limits or reach maximum connections")"

        # PHASE 4: Test Golden Path degradation under resource pressure
        if len(resource_test_connections) >= MAX_CONNECTIONS_PER_USER - 2:
            # System should still provide Golden Path functionality even near limits
            stress_websocket = resource_test_connections[-1] if resource_test_connections else baseline_websocket
            stress_result = await self._execute_golden_path_with_websocket(stress_websocket, primary_user)

            # Golden Path may be slower under stress but should still work
            self.assertTrue(stress_result['completed'] or len(stress_result['events_received'] >= 2,
                           fGolden Path should maintain basic functionality under resource pressure. 
                           fEvents: {stress_result['events_received']})

        # PHASE 5: Test recovery after resource exhaustion
        recovery_start_time = time.time()

        # Close half of the connections to simulate cleanup
        connections_to_close = resource_test_connections[:len(resource_test_connections)//2]
        for connection in connections_to_close:
            try:
                await connection.close()
                self.active_websockets.remove(connection)
            except Exception as e:
                self.staging_metrics['cleanup_failures'] += 1
                self.logger.warning(f"Cleanup failure during recovery: {e})"

        recovery_time = time.time() - recovery_start_time

        # Test Golden Path recovery
        recovery_websocket = await self._create_staging_websocket_connection(primary_user, session_token)
        recovery_result = await self._execute_golden_path_with_websocket(recovery_websocket, primary_user)

        self.assertTrue(recovery_result['completed'],
                       fGolden Path should recover after resource cleanup. ""
                       fEvents: {recovery_result['events_received']})

        self.assertLess(recovery_result['execution_time'], 60.0,
                       fGolden Path recovery should complete within 60 seconds, ""
                       f"got {recovery_result['execution_time']:.1f}s)"

        self.logger.info(fGolden Path resource limit test completed. 
                        fConnections created: {len(resource_test_connections)}, 
                        fRecovery time: {recovery_time:.3f}s, ""
                        fGolden Path completions: {self.staging_metrics['golden_path_completions']})

    async def test_concurrent_golden_path_resource_competition(self):
        
        Test Golden Path functionality with multiple concurrent users competing for resources.

        Validates:
        - Multiple users can execute Golden Path simultaneously
        - Resource limits are enforced per-user correctly
        - Golden Path quality is maintained during user concurrency
""
        if not await check_websocket_service_available():
            pytest.skip(WebSocket service not available for E2E testing)

        self.logger.info(Testing concurrent Golden Path resource competition on staging...")"

        # Authenticate all test users
        user_sessions = {}
        for user_key, user_id in self.test_users.items():
            session_token = await self._authenticate_staging_user(user_id)
            user_sessions[user_key] = session_token

        async def execute_user_golden_path(user_key: str, user_id: str, session_token: str) -> Dict[str, Any]:
            Execute Golden Path for a single user with resource competition.""
            user_results = {
                'user_key': user_key,
                'connections_created': 0,
                'golden_path_attempts': 0,
                'golden_path_successes': 0,
                'resource_limits_hit': 0,
                'errors': []
            }

            try:
                # Create multiple connections for this user (simulate resource usage)
                user_connections = []
                for i in range(min(MAX_CONNECTIONS_PER_USER, 8)):  # Limit for E2E performance
                    try:
                        websocket = await self._create_staging_websocket_connection(user_id, session_token)
                        user_connections.append(websocket)
                        user_results['connections_created'] += 1

                        # Execute Golden Path on every 2nd connection
                        if i % 2 == 0:
                            user_results['golden_path_attempts'] += 1
                            golden_path_result = await self._execute_golden_path_with_websocket(websocket, user_id)

                            if golden_path_result['completed']:
                                user_results['golden_path_successes'] += 1

                    except Exception as e:
                        if limit" in str(e).lower():"
                            user_results['resource_limits_hit'] += 1
                        else:
                            user_results['errors'].append(str(e))
                        break

                return user_results

            except Exception as e:
                user_results['errors'].append(fUser execution failed: {e})
                return user_results

        # Execute all users concurrently
        concurrent_start_time = time.time()

        concurrent_tasks = [
            execute_user_golden_path(user_key, user_id, user_sessions[user_key]
            for user_key, user_id in self.test_users.items()
        ]

        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_execution_time = time.time() - concurrent_start_time

        # Analyze concurrent execution results
        total_golden_path_successes = 0
        total_connections_created = 0
        total_resource_limits_hit = 0

        for result in concurrent_results:
            if isinstance(result, Exception):
                self.logger.error(fConcurrent user execution failed: {result})""
                continue

            user_key = result['user_key']
            total_golden_path_successes += result['golden_path_successes']
            total_connections_created += result['connections_created']
            total_resource_limits_hit += result['resource_limits_hit']

            self.logger.info(f"User {user_key}: {result['golden_path_successes']}/{result['golden_path_attempts']} "
                           fGolden Path successes, {result['connections_created']} connections, 
                           f{result['resource_limits_hit']} resource limits hit)

            # Each user should achieve some level of Golden Path success
            if result['golden_path_attempts'] > 0:
                success_rate = result['golden_path_successes'] / result['golden_path_attempts']
                self.assertGreater(success_rate, 0.3,
                                  fUser {user_key} should have >30% Golden Path success rate during concurrency, ""
                                  fgot {success_rate:.1%})

        # Overall system validation
        self.assertGreater(total_golden_path_successes, 0,
                          At least some Golden Path executions should succeed during concurrent resource competition)

        self.assertGreater(total_connections_created, len(self.test_users),
                          "Should have created multiple connections across users)"

        self.assertLess(concurrent_execution_time, 120.0,
                       fConcurrent execution should complete within 2 minutes, got {concurrent_execution_time:.1f}s)

        self.logger.info(fConcurrent Golden Path test completed in {concurrent_execution_time:.1f}s. 
                        fTotal successes: {total_golden_path_successes}, ""
                        fTotal connections: {total_connections_created}, 
                        fResource limits hit: {total_resource_limits_hit})

    async def test_golden_path_under_staging_infrastructure_stress(self):
    ""
        Test Golden Path reliability under staging infrastructure stress conditions.

        This test validates Golden Path performance under realistic production-like stress:
        - Network latency and connection instability
        - Service degradation simulation
        - Infrastructure resource competition
        
        if not await check_websocket_service_available():
            pytest.skip(WebSocket service not available for E2E testing")"

        self.logger.info(Testing Golden Path under staging infrastructure stress...)

        primary_user = self.test_users['golden_path_user']
        session_token = await self._authenticate_staging_user(primary_user)

        # Create multiple WebSocket connections to simulate infrastructure stress
        stress_connections = []
        golden_path_results = []

        stress_start_time = time.time()

        try:
            # PHASE 1: Build up infrastructure stress with multiple connections
            for i in range(min(MAX_CONNECTIONS_PER_USER, 12)):  # Reasonable limit for E2E
                try:
                    websocket = await self._create_staging_websocket_connection(primary_user, session_token)
                    stress_connections.append(websocket)

                    # Execute Golden Path under increasing stress
                    if i % 3 == 0:  # Every 3rd connection
                        golden_path_start = time.time()
                        golden_path_result = await self._execute_golden_path_with_websocket(websocket, primary_user)
                        golden_path_time = time.time() - golden_path_start

                        golden_path_results.append({
                            'connection_index': i,
                            'completed': golden_path_result['completed'],
                            'events_received': len(golden_path_result['events_received'],
                            'execution_time': golden_path_time,
                            'infrastructure_stress_level': i / 12  # 0.0 to 1.0
                        }

                        self.logger.info(fGolden Path at stress level {i/12:.1%}: ""
                                       f"completed={golden_path_result['completed']}, "
                                       fevents={len(golden_path_result['events_received']}, 
                                       ftime={golden_path_time:.1f}s)

                except Exception as e:
                    self.logger.warning(fInfrastructure stress connection {i} failed: {e}")"
                    break

            stress_execution_time = time.time() - stress_start_time

            # PHASE 2: Validate Golden Path degradation under stress
            if golden_path_results:
                # Calculate success rate under stress
                successful_executions = sum(1 for r in golden_path_results if r['completed']
                success_rate = successful_executions / len(golden_path_results)

                self.assertGreater(success_rate, 0.5,
                                  fGolden Path should maintain >50% success rate under infrastructure stress, 
                                  fgot {success_rate:.1%} ({successful_executions}/{len(golden_path_results)})

                # Validate execution time degradation is reasonable
                execution_times = [r['execution_time'] for r in golden_path_results if r['completed']]
                if execution_times:
                    avg_execution_time = sum(execution_times) / len(execution_times)
                    max_execution_time = max(execution_times)

                    self.assertLess(avg_execution_time, 90.0,
                                   f"Average Golden Path execution time should remain under 90s under stress, "
                                   fgot {avg_execution_time:.1f}s")"

                    self.assertLess(max_execution_time, 120.0,
                                   fMaximum Golden Path execution time should remain under 120s under stress, 
                                   fgot {max_execution_time:.1f}s)""

                # Validate events received (partial success acceptable under stress)
                avg_events = sum(r['events_received'] for r in golden_path_results) / len(golden_path_results)
                self.assertGreater(avg_events, 2.0,
                                  f"Should receive at least 2 Golden Path events on average under stress, "
                                  fgot {avg_events:.1f})

            # PHASE 3: Validate infrastructure recovery
            recovery_start = time.time()

            # Close some connections to reduce stress
            connections_to_close = stress_connections[:len(stress_connections)//2]
            for connection in connections_to_close:
                try:
                    await connection.close()
                    if connection in self.active_websockets:
                        self.active_websockets.remove(connection)
                except Exception:
                    pass

            # Test Golden Path recovery
            recovery_websocket = await self._create_staging_websocket_connection(primary_user, session_token)
            recovery_result = await self._execute_golden_path_with_websocket(recovery_websocket, primary_user)

            recovery_time = time.time() - recovery_start

            self.assertTrue(recovery_result['completed'],
                           fGolden Path should recover after infrastructure stress reduction. 
                           fEvents: {recovery_result['events_received']}")"

            self.assertLess(recovery_result['execution_time'], 45.0,
                           fGolden Path recovery should be faster than stressed execution, 
                           fgot {recovery_result['execution_time']:.1f}s)

            self.logger.info(f"Infrastructure stress test completed in {stress_execution_time:.1f}s. "
                           fGolden Path results: {len(golden_path_results)} attempts, ""
                           fRecovery time: {recovery_time:.1f}s)

        finally:
            # Cleanup remaining connections
            for connection in stress_connections:
                try:
                    await connection.close()
                    if connection in self.active_websockets:
                        self.active_websockets.remove(connection)
                except Exception:
                    pass


if __name__ == __main__:""
    pytest.main([__file__, "-v, --tb=short", "-s"]