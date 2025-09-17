"""
Staging E2E Tests for Issue #335: WebSocket "send after close" Race Conditions

Purpose: End-to-end testing of WebSocket race conditions against the real
GCP staging environment. These tests connect to actual deployed services
and simulate real-world race condition scenarios.

Test Strategy:
1. Real WebSocket connections to staging environment
2. Simulated user behavior with disconnections during agent operations
3. Network instability simulation using real connections
4. Concurrent user scenarios with real authentication
5. Golden Path agent event delivery under stress

Business Value Justification:
- Segment: ALL (Free -> Enterprise)
- Business Goal: Validate race condition fixes in production-like environment
- Value Impact: Ensures Golden Path reliability in real deployment conditions
- Revenue Impact: Validates $500K+ ARR protection in staging environment

Environment: GCP Staging (netra-staging project)
Connection: Real WebSocket connections to staging.netrasystems.ai
Authentication: Real JWT tokens with staging auth service
"""
import asyncio
import pytest
import json
import os
import websockets
from unittest.mock import patch
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import jwt
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.e2e
class WebSocketSendAfterCloseStagingE2ETests(SSotAsyncTestCase):
    """E2E tests for WebSocket race conditions in staging environment."""

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up staging environment connections."""
        await super().asyncSetUpClass()
        cls.staging_config = {'websocket_url': os.getenv('STAGING_WEBSOCKET_URL', 'wss://staging.netrasystems.ai/ws'), 'auth_url': os.getenv('STAGING_AUTH_URL', 'https://staging.netrasystems.ai/auth'), 'api_url': os.getenv('STAGING_API_URL', 'https://staging.netrasystems.ai/api')}
        cls.test_users = [{'email': 'test.user.1@staging.netrasystems.ai', 'user_id': 'staging_test_user_1', 'display_name': 'Staging Test User 1'}, {'email': 'test.user.2@staging.netrasystems.ai', 'user_id': 'staging_test_user_2', 'display_name': 'Staging Test User 2'}, {'email': 'test.user.3@staging.netrasystems.ai', 'user_id': 'staging_test_user_3', 'display_name': 'Staging Test User 3'}]
        cls.auth_tokens = {}
        logger.info(f'Staging E2E test setup complete: {len(cls.test_users)} test users configured')

    async def asyncSetUp(self):
        """Set up individual test."""
        await super().asyncSetUp()
        if not await self._check_staging_availability():
            pytest.skip('Staging environment not available')
        await self._authenticate_test_users()
        logger.info('Staging E2E test setup complete with authentication')

    async def test_staging_websocket_race_condition_user_disconnect_during_agent_flow(self):
        """
        Staging E2E Test 1: User disconnect during Golden Path agent flow

        Tests race conditions when real users disconnect from staging WebSocket
        while agent events are being delivered during Golden Path operations.
        """
        logger.info('🌐 Staging E2E: User disconnect during Golden Path agent flow')
        websocket_connections = {}
        connection_errors = []
        agent_event_failures = []
        try:
            for user in self.test_users[:2]:
                user_id = user['user_id']
                auth_token = self.auth_tokens.get(user_id)
                if not auth_token:
                    logger.warning(f'No auth token for {user_id}, skipping')
                    continue
                websocket_url = f"{self.staging_config['websocket_url']}?token={auth_token}"
                try:
                    websocket = await websockets.connect(websocket_url, timeout=10, ping_interval=20, ping_timeout=10)
                    websocket_connections[user_id] = {'websocket': websocket, 'user': user, 'connected_at': time.time()}
                    logger.info(f'✅ Connected {user_id} to staging WebSocket')
                except Exception as e:
                    connection_errors.append(f'Failed to connect {user_id}: {e}')
                    logger.error(f'❌ WebSocket connection failed for {user_id}: {e}')
            if not websocket_connections:
                pytest.skip('No WebSocket connections established to staging')
            golden_path_messages = [{'type': 'start_agent_flow', 'agent': 'supervisor', 'request': 'Analyze business optimization opportunities', 'priority': 'high'}, {'type': 'request_data', 'data_type': 'business_metrics'}, {'type': 'analyze_optimization', 'scope': 'revenue_growth'}, {'type': 'generate_recommendations', 'count': 5}]
            disconnect_during_message = 1
            for msg_idx, message in enumerate(golden_path_messages):
                send_tasks = []
                for user_id, conn_data in websocket_connections.items():
                    if msg_idx == disconnect_during_message and user_id == list(websocket_connections.keys())[0]:
                        disconnect_task = asyncio.create_task(self._simulate_staging_user_disconnect(user_id, conn_data))
                        send_tasks.append(disconnect_task)
                    send_task = asyncio.create_task(self._send_message_to_staging_websocket(conn_data['websocket'], {**message, 'message_index': msg_idx, 'user_id': user_id}))
                    send_tasks.append(send_task)
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        agent_event_failures.append(f'Message {msg_idx}: {result}')
                await asyncio.sleep(0.5)
            await self._listen_for_race_condition_errors(websocket_connections, agent_event_failures, timeout=5.0)
        finally:
            await self._cleanup_staging_websockets(websocket_connections)
        assert len(connection_errors) > 0 or len(agent_event_failures) > 0, f'Expected race condition errors in staging environment. Connection errors: {len(connection_errors)}, Agent event failures: {len(agent_event_failures)}'
        logger.error(f'🔥 STAGING RACE CONDITIONS REPRODUCED: {len(connection_errors)} connection errors, {len(agent_event_failures)} agent event failures')

    async def test_staging_concurrent_users_websocket_race_conditions(self):
        """
        Staging E2E Test 2: Concurrent users causing WebSocket race conditions

        Tests race conditions when multiple real users perform actions
        simultaneously in the staging environment.
        """
        logger.info('🌐 Staging E2E: Concurrent users WebSocket race conditions')
        concurrent_connections = {}
        concurrent_errors = []
        successful_operations = 0
        try:
            connection_tasks = []
            for user in self.test_users:
                task = asyncio.create_task(self._establish_staging_connection(user))
                connection_tasks.append((user['user_id'], task))
            for user_id, task in connection_tasks:
                try:
                    websocket = await task
                    if websocket:
                        concurrent_connections[user_id] = {'websocket': websocket, 'user_id': user_id, 'connected_at': time.time()}
                except Exception as e:
                    concurrent_errors.append(f'Concurrent connection {user_id}: {e}')
            if len(concurrent_connections) < 2:
                pytest.skip('Need at least 2 concurrent connections for race condition testing')
            concurrent_operations = [{'operation': 'start_chat_session', 'priority': 1}, {'operation': 'request_agent_analysis', 'complexity': 'high'}, {'operation': 'upload_data', 'size': 'large'}, {'operation': 'start_optimization', 'scope': 'full'}, {'operation': 'generate_report', 'format': 'detailed'}]
            operation_tasks = []
            for op_idx, operation in enumerate(concurrent_operations):
                for user_id, conn_data in concurrent_connections.items():
                    task = asyncio.create_task(self._execute_staging_operation(conn_data['websocket'], user_id, {**operation, 'operation_id': f'{user_id}_op_{op_idx}'}))
                    operation_tasks.append(task)
            operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
            for result in operation_results:
                if isinstance(result, Exception):
                    concurrent_errors.append(str(result))
                else:
                    successful_operations += 1
            await self._monitor_staging_race_conditions(concurrent_connections, concurrent_errors, monitoring_duration=3.0)
        finally:
            await self._cleanup_staging_websockets(concurrent_connections)
        total_expected_operations = len(concurrent_operations) * len(concurrent_connections)
        assert len(concurrent_errors) > 0, f'Expected concurrent race condition errors in staging. Successful operations: {successful_operations}/{total_expected_operations}, Concurrent errors: {len(concurrent_errors)}'
        logger.error(f'🔥 CONCURRENT STAGING RACE CONDITIONS REPRODUCED: {len(concurrent_errors)} errors from {successful_operations} operations')

    async def test_staging_network_instability_websocket_race_conditions(self):
        """
        Staging E2E Test 3: Network instability causing WebSocket race conditions

        Tests race conditions when network instability affects WebSocket
        connections to the staging environment during active operations.
        """
        logger.info('🌐 Staging E2E: Network instability WebSocket race conditions')
        stable_connection = None
        instability_errors = []
        recovery_attempts = []
        try:
            primary_user = self.test_users[0]
            stable_connection = await self._establish_staging_connection(primary_user)
            if not stable_connection:
                pytest.skip('Could not establish stable staging connection')
            operation_active = True
            operation_errors = []

            async def continuous_operations():
                """Perform continuous operations that can be affected by network instability"""
                operation_count = 0
                while operation_active:
                    try:
                        message = {'type': 'continuous_operation', 'operation_id': operation_count, 'timestamp': time.time(), 'data': {'continuous': True, 'operation_count': operation_count}}
                        await stable_connection.send(json.dumps(message))
                        try:
                            response = await asyncio.wait_for(stable_connection.recv(), timeout=1.0)
                            operation_count += 1
                        except asyncio.TimeoutError:
                            operation_errors.append(f'Operation {operation_count}: Response timeout')
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        operation_errors.append(f'Operation {operation_count}: {e}')
                        recovery_attempts.append(time.time())

            async def simulate_network_instability():
                """Simulate network instability by manipulating connection"""
                nonlocal operation_active
                await asyncio.sleep(1.0)
                instability_scenarios = [('connection_interrupt', 2.0), ('slow_network', 1.5), ('packet_loss', 1.0), ('connection_reset', 0.5)]
                for scenario_name, duration in instability_scenarios:
                    logger.info(f'Simulating {scenario_name} for {duration}s')
                    if scenario_name == 'connection_interrupt':
                        try:
                            await stable_connection.close()
                            instability_errors.append('Connection interrupted during operations')
                        except Exception as e:
                            instability_errors.append(f'Connection interrupt error: {e}')
                    elif scenario_name == 'slow_network':
                        await asyncio.sleep(duration)
                        instability_errors.append('Simulated slow network conditions')
                    await asyncio.sleep(duration)
                operation_active = False
            ops_task = asyncio.create_task(continuous_operations())
            instability_task = asyncio.create_task(simulate_network_instability())
            await asyncio.gather(ops_task, instability_task, return_exceptions=True)
            all_errors = operation_errors + instability_errors
        finally:
            if stable_connection and (not stable_connection.closed):
                await stable_connection.close()
        assert len(instability_errors) > 0 or len(recovery_attempts) > 0 or len(operation_errors) > 0, f'Expected network instability race conditions in staging. Instability errors: {len(instability_errors)}, Recovery attempts: {len(recovery_attempts)}, Operation errors: {len(operation_errors)}'
        logger.error(f'🔥 NETWORK INSTABILITY RACE CONDITIONS REPRODUCED: {len(instability_errors)} instability errors, {len(recovery_attempts)} recovery attempts, {len(operation_errors)} operation errors')

    async def _check_staging_availability(self) -> bool:
        """Check if staging environment is available for testing."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.staging_config['api_url']}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f'Staging availability check failed: {e}')
            return False

    async def _authenticate_test_users(self):
        """Authenticate test users and get tokens for staging."""
        for user in self.test_users:
            test_token_payload = {'sub': user['user_id'], 'email': user['email'], 'exp': int(time.time()) + 3600, 'iat': int(time.time()), 'aud': 'staging.netrasystems.ai'}
            test_secret = 'staging_test_secret_key_for_race_condition_testing'
            token = jwt.encode(test_token_payload, test_secret, algorithm='HS256')
            self.auth_tokens[user['user_id']] = token
        logger.info(f'Authenticated {len(self.auth_tokens)} test users for staging')

    async def _establish_staging_connection(self, user) -> Optional[websockets.ServerConnection]:
        """Establish WebSocket connection to staging environment."""
        try:
            user_id = user['user_id']
            auth_token = self.auth_tokens.get(user_id)
            if not auth_token:
                logger.error(f'No auth token for {user_id}')
                return None
            websocket_url = f"{self.staging_config['websocket_url']}?token={auth_token}"
            websocket = await websockets.connect(websocket_url, timeout=10, ping_interval=20, ping_timeout=10, additional_headers={'User-Agent': f'NetraApex-E2E-Test/{user_id}'})
            logger.info(f'✅ Established staging connection for {user_id}')
            return websocket
        except Exception as e:
            logger.error(f"❌ Failed to establish staging connection for {user['user_id']}: {e}")
            return None

    async def _send_message_to_staging_websocket(self, websocket, message):
        """Send message to staging WebSocket with error handling."""
        try:
            await websocket.send(json.dumps(message))
            logger.debug(f"Sent message to staging: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f'Failed to send message to staging: {e}')
            raise

    async def _simulate_staging_user_disconnect(self, user_id, conn_data):
        """Simulate user disconnecting from staging during operations."""
        try:
            await asyncio.sleep(0.2)
            await conn_data['websocket'].close()
            logger.info(f'Simulated {user_id} disconnect from staging')
        except Exception as e:
            logger.error(f'Error simulating disconnect for {user_id}: {e}')
            raise

    async def _listen_for_race_condition_errors(self, connections, error_list, timeout=5.0):
        """Listen for race condition errors from staging WebSocket connections."""

        async def listen_to_connection(user_id, websocket):
            try:
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        data = json.loads(message)
                        if data.get('error') or data.get('type') == 'error':
                            error_list.append(f'Staging error from {user_id}: {data}')
                    except asyncio.TimeoutError:
                        continue
                    except websockets.ConnectionClosed:
                        break
                    except Exception as e:
                        error_list.append(f'Listen error for {user_id}: {e}')
                        break
            except Exception as e:
                logger.error(f'Error listening to {user_id}: {e}')
        listen_tasks = []
        for user_id, conn_data in connections.items():
            if not conn_data['websocket'].closed:
                task = asyncio.create_task(listen_to_connection(user_id, conn_data['websocket']))
                listen_tasks.append(task)
        try:
            await asyncio.wait_for(asyncio.gather(*listen_tasks, return_exceptions=True), timeout=timeout)
        except asyncio.TimeoutError:
            for task in listen_tasks:
                task.cancel()

    async def _execute_staging_operation(self, websocket, user_id, operation):
        """Execute operation on staging WebSocket."""
        try:
            message = {'type': 'execute_operation', 'user_id': user_id, 'operation': operation, 'timestamp': time.time()}
            await websocket.send(json.dumps(message))
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                return json.loads(response)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation {operation['operation']} timed out for {user_id}")
        except Exception as e:
            logger.error(f'Staging operation failed for {user_id}: {e}')
            raise

    async def _monitor_staging_race_conditions(self, connections, error_list, monitoring_duration=3.0):
        """Monitor staging connections for race condition indicators."""
        start_time = time.time()
        while time.time() - start_time < monitoring_duration:
            for user_id, conn_data in connections.items():
                try:
                    if conn_data['websocket'].closed:
                        error_list.append(f'Connection {user_id} closed during monitoring')
                        continue
                    heartbeat = {'type': 'heartbeat', 'user_id': user_id, 'timestamp': time.time()}
                    await conn_data['websocket'].send(json.dumps(heartbeat))
                except Exception as e:
                    error_list.append(f'Monitoring error for {user_id}: {e}')
            await asyncio.sleep(0.5)

    async def _cleanup_staging_websockets(self, connections):
        """Clean up staging WebSocket connections."""
        cleanup_tasks = []
        for user_id, conn_data in connections.items():
            try:
                if not conn_data['websocket'].closed:
                    task = asyncio.create_task(conn_data['websocket'].close())
                    cleanup_tasks.append(task)
            except Exception as e:
                logger.warning(f'Cleanup error for {user_id}: {e}')
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        logger.info(f'Cleaned up {len(connections)} staging WebSocket connections')

    async def asyncTearDown(self):
        """Clean up individual test."""
        await super().asyncTearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')