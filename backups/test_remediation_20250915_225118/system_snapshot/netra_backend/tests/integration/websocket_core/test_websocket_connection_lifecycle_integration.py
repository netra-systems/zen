"""
WebSocket Connection Lifecycle Integration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat Reliability & Recovery
- Value Impact: Ensures chat connections recover gracefully from temporary network issues
- Strategic Impact: Prevents user abandonment due to connection failures - maintains chat session continuity

This test suite validates WebSocket connection lifecycle management including:
- Connection establishment and teardown
- Graceful recovery from temporary network issues
- Message queuing during disconnections
- Reconnection handling and state restoration
- Resource cleanup and memory management

BUSINESS IMPACT: Each test prevents specific scenarios that would disrupt user chat experience.
"""
import asyncio
import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from contextlib import asynccontextmanager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, UserWebSocketEmitter, UserWebSocketContext, UserWebSocketConnection, WebSocketEvent, ConnectionStatus
from test_framework.ssot.base_test_case import SSotBaseTestCase
logger = central_logger.get_logger(__name__)

class MockWebSocketState:
    """Mock WebSocket with controllable connection state."""

    def __init__(self, user_id: str, initial_healthy: bool=True):
        self.user_id = user_id
        self._healthy = initial_healthy
        self._closed = False
        self._sent_messages = []
        self.send_json = AsyncMock(side_effect=self._send_json_impl)
        self.ping = AsyncMock(side_effect=self._ping_impl)
        self.close = AsyncMock(side_effect=self._close_impl)
        self._connection_failures = 0
        self._network_delay = 0.0
        self._should_timeout = False

    async def _send_json_impl(self, data):
        """Simulate sending JSON with controllable behavior."""
        if self._closed:
            raise ConnectionError(f'WebSocket closed for {self.user_id}')
        if not self._healthy:
            self._connection_failures += 1
            raise ConnectionError(f'Network error for {self.user_id} (failure #{self._connection_failures})')
        if self._should_timeout:
            await asyncio.sleep(10)
        if self._network_delay > 0:
            await asyncio.sleep(self._network_delay)
        self._sent_messages.append({'data': data, 'timestamp': datetime.now(timezone.utc), 'user_id': self.user_id})

    async def _ping_impl(self):
        """Simulate ping with controllable health."""
        if self._closed:
            return False
        if not self._healthy:
            raise ConnectionError(f'Ping failed for {self.user_id}')
        return True

    async def _close_impl(self):
        """Simulate connection close."""
        self._closed = True
        self._healthy = False

    def set_healthy(self, healthy: bool):
        """Control connection health."""
        self._healthy = healthy

    def set_network_delay(self, delay: float):
        """Simulate network latency."""
        self._network_delay = delay

    def set_should_timeout(self, timeout: bool):
        """Control whether operations should timeout."""
        self._should_timeout = timeout

    def reset_failure_count(self):
        """Reset connection failure tracking."""
        self._connection_failures = 0

@pytest.mark.integration
class WebSocketConnectionLifecycleIntegrationTests(SSotBaseTestCase):
    """
    Integration tests for WebSocket connection lifecycle management.
    
    Tests critical connection scenarios that affect chat business value:
    - Connection establishment and validation
    - Graceful handling of temporary network issues
    - Message queuing and recovery during disconnections
    - Automatic reconnection and state restoration
    - Resource cleanup and memory management
    
    BUSINESS IMPACT: Prevents chat session abandonment due to connection issues.
    """

    async def asyncSetUp(self):
        """Set up WebSocket connection lifecycle test environment."""
        await super().asyncSetUp()
        self.ws_manager = UnifiedWebSocketManager()
        self.bridge_factory = WebSocketBridgeFactory()
        self.test_users = {}
        self.mock_websockets = {}
        self.connections = {}
        user_count = 5
        for i in range(user_count):
            user_id = f'lifecycle_user_{i:02d}'
            connection_id = str(uuid.uuid4())
            mock_websocket = MockWebSocketState(user_id, initial_healthy=True)
            connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_websocket, connected_at=datetime.now(timezone.utc))
            await self.ws_manager.add_connection(connection)
            self.test_users[user_id] = {'connection_id': connection_id, 'thread_id': f'thread_{i:02d}'}
            self.mock_websockets[user_id] = mock_websocket
            self.connections[user_id] = connection
        logger.info(f'Connection lifecycle test setup completed with {user_count} users')

    async def test_normal_connection_lifecycle(self):
        """
        Test normal connection establishment and teardown.
        
        BVJ: Validates basic connection management that enables all chat functionality.
        Foundation for reliable chat experience.
        """
        user_id = 'lifecycle_user_00'
        connection_id = self.test_users[user_id]['connection_id']
        self.assertTrue(self.ws_manager.is_connection_active(user_id), 'Connection should be active after setup')
        test_message = {'type': 'lifecycle_test', 'content': 'Normal connection test', 'timestamp': datetime.now(timezone.utc).isoformat()}
        await self.ws_manager.send_to_user(user_id, test_message)
        await asyncio.sleep(0.1)
        mock_ws = self.mock_websockets[user_id]
        self.assertEqual(len(mock_ws._sent_messages), 1)
        sent_data = mock_ws._sent_messages[0]['data']
        self.assertEqual(sent_data['type'], 'lifecycle_test')
        health = self.ws_manager.get_connection_health(user_id)
        self.assertTrue(health['has_active_connections'])
        self.assertEqual(health['active_connections'], 1)
        await self.ws_manager.remove_connection(connection_id)
        self.assertFalse(self.ws_manager.is_connection_active(user_id), 'Connection should be inactive after removal')
        mock_ws._sent_messages.clear()
        await self.ws_manager.send_to_user(user_id, test_message)
        await asyncio.sleep(0.1)
        self.assertEqual(len(mock_ws._sent_messages), 0, 'No messages should be sent to disconnected user')

    async def test_connection_recovery_from_network_issues(self):
        """
        Test connection recovery from temporary network issues.
        
        BVJ: Critical for chat reliability - prevents user abandonment when
        temporary network issues occur (wifi drops, mobile switching, etc.).
        """
        user_id = 'lifecycle_user_01'
        mock_ws = self.mock_websockets[user_id]
        initial_message = {'type': 'pre_failure_test', 'content': 'Before network issue'}
        await self.ws_manager.send_to_user(user_id, initial_message)
        await asyncio.sleep(0.1)
        self.assertEqual(len(mock_ws._sent_messages), 1)
        mock_ws.set_healthy(False)
        mock_ws._sent_messages.clear()
        failure_messages = []
        for i in range(3):
            message = {'type': 'during_failure_test', 'content': f'Message during network issue {i}', 'sequence': i}
            failure_messages.append(message)
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.2)
        self.assertEqual(len(mock_ws._sent_messages), 0, 'Messages should not be delivered during network failure')
        mock_ws.set_healthy(True)
        mock_ws.reset_failure_count()
        recovery_message = {'type': 'post_recovery_test', 'content': 'After network recovery'}
        await self.ws_manager.send_to_user(user_id, recovery_message)
        await asyncio.sleep(0.1)
        self.assertGreater(len(mock_ws._sent_messages), 0, 'Messages should be delivered after recovery')
        self.assertTrue(self.ws_manager.is_connection_active(user_id), 'Connection should be active after recovery')

    async def test_message_queuing_during_disconnection(self):
        """
        Test message queuing and delivery when connection is temporarily unavailable.
        
        BVJ: Prevents message loss during brief disconnections - critical for
        maintaining chat conversation continuity.
        """
        user_id = 'lifecycle_user_02'
        mock_ws = self.mock_websockets[user_id]
        mock_ws._sent_messages.clear()
        mock_ws.set_healthy(False)
        queued_messages = []
        for i in range(5):
            message = {'type': 'queued_message', 'sequence': i, 'content': f'Queued message {i}', 'timestamp': datetime.now(timezone.utc).isoformat()}
            queued_messages.append(message)
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.3)
        self.assertEqual(len(mock_ws._sent_messages), 0, 'Messages should be queued during disconnection')
        mock_ws.set_healthy(True)
        mock_ws.reset_failure_count()
        trigger_message = {'type': 'trigger_processing', 'content': 'Trigger queue processing'}
        await self.ws_manager.send_to_user(user_id, trigger_message)
        await asyncio.sleep(0.5)
        self.assertGreater(len(mock_ws._sent_messages), 0, 'Messages should be delivered after reconnection')
        test_message = {'type': 'normal_test', 'content': 'Normal operation after recovery'}
        message_count_before = len(mock_ws._sent_messages)
        await self.ws_manager.send_to_user(user_id, test_message)
        await asyncio.sleep(0.1)
        self.assertGreater(len(mock_ws._sent_messages), message_count_before, 'New messages should be delivered normally')

    async def test_connection_timeout_handling(self):
        """
        Test handling of connection timeouts.
        
        BVJ: Prevents chat UI from hanging indefinitely when connections timeout.
        Ensures responsive user experience even with poor network conditions.
        """
        user_id = 'lifecycle_user_03'
        mock_ws = self.mock_websockets[user_id]
        mock_ws.set_should_timeout(True)
        mock_ws._sent_messages.clear()
        timeout_message = {'type': 'timeout_test', 'content': 'This message should timeout'}
        start_time = time.time()
        await self.ws_manager.send_to_user(user_id, timeout_message)
        end_time = time.time()
        elapsed = end_time - start_time
        self.assertLess(elapsed, 5.0, 'WebSocket operations should not hang indefinitely')
        self.assertEqual(len(mock_ws._sent_messages), 0, 'Timed out messages should not be marked as delivered')
        mock_ws.set_should_timeout(False)
        recovery_message = {'type': 'timeout_recovery_test', 'content': 'Recovery after timeout'}
        await self.ws_manager.send_to_user(user_id, recovery_message)
        await asyncio.sleep(0.1)
        self.assertEqual(len(mock_ws._sent_messages), 1, 'Messages should be delivered after timeout recovery')

    async def test_multiple_connection_failure_scenarios(self):
        """
        Test various connection failure scenarios in sequence.
        
        BVJ: Validates robustness under multiple types of network issues
        that users commonly experience (mobile networks, wifi issues, etc.).
        """
        user_id = 'lifecycle_user_04'
        mock_ws = self.mock_websockets[user_id]
        mock_ws._sent_messages.clear()
        scenarios = [('network_failure', lambda: mock_ws.set_healthy(False)), ('high_latency', lambda: mock_ws.set_network_delay(1.0)), ('timeout_risk', lambda: mock_ws.set_should_timeout(True)), ('connection_close', lambda: asyncio.create_task(mock_ws.close()))]
        for scenario_name, setup_failure in scenarios:
            logger.info(f'Testing scenario: {scenario_name}')
            setup_failure()
            test_message = {'type': f'test_{scenario_name}', 'content': f'Message during {scenario_name}', 'timestamp': datetime.now(timezone.utc).isoformat()}
            try:
                await self.ws_manager.send_to_user(user_id, test_message)
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.warning(f'Exception during {scenario_name}: {e}')
            mock_ws.set_healthy(True)
            mock_ws.set_network_delay(0.0)
            mock_ws.set_should_timeout(False)
            mock_ws.reset_failure_count()
            recovery_message = {'type': f'recovery_{scenario_name}', 'content': f'Recovery from {scenario_name}'}
            await self.ws_manager.send_to_user(user_id, recovery_message)
            await asyncio.sleep(0.1)
        final_message = {'type': 'final_test', 'content': 'Final connectivity test'}
        message_count_before = len(mock_ws._sent_messages)
        await self.ws_manager.send_to_user(user_id, final_message)
        await asyncio.sleep(0.1)
        self.assertGreater(len(mock_ws._sent_messages), message_count_before, 'Connection should be fully functional after all scenarios')

    async def test_concurrent_connection_lifecycle_management(self):
        """
        Test lifecycle management with concurrent users experiencing issues.
        
        BVJ: Ensures individual user connection issues don't affect other users.
        Critical for multi-user chat reliability.
        """
        for mock_ws in self.mock_websockets.values():
            mock_ws._sent_messages.clear()
        user_scenarios = {'lifecycle_user_00': 'normal', 'lifecycle_user_01': 'network_failure', 'lifecycle_user_02': 'high_latency', 'lifecycle_user_03': 'timeout', 'lifecycle_user_04': 'connection_close'}
        for user_id, scenario in user_scenarios.items():
            mock_ws = self.mock_websockets[user_id]
            if scenario == 'network_failure':
                mock_ws.set_healthy(False)
            elif scenario == 'high_latency':
                mock_ws.set_network_delay(2.0)
            elif scenario == 'timeout':
                mock_ws.set_should_timeout(True)
            elif scenario == 'connection_close':
                await mock_ws.close()

        async def send_to_user(user_id, scenario):
            message = {'type': 'concurrent_lifecycle_test', 'user_id': user_id, 'scenario': scenario, 'content': f'Message for {user_id} in {scenario} scenario', 'timestamp': datetime.now(timezone.utc).isoformat()}
            try:
                await self.ws_manager.send_to_user(user_id, message)
            except Exception as e:
                logger.warning(f'Expected exception for {user_id}: {e}')
        tasks = [send_to_user(user_id, scenario) for user_id, scenario in user_scenarios.items()]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(1.0)
        normal_user = 'lifecycle_user_00'
        normal_ws = self.mock_websockets[normal_user]
        self.assertGreater(len(normal_ws._sent_messages), 0, 'Normal user should receive messages despite other failures')
        latency_user = 'lifecycle_user_02'
        latency_ws = self.mock_websockets[latency_user]
        for user_id in user_scenarios.keys():
            mock_ws = self.mock_websockets[user_id]
            mock_ws.set_healthy(True)
            mock_ws.set_network_delay(0.0)
            mock_ws.set_should_timeout(False)
            mock_ws.reset_failure_count()
        for user_id in user_scenarios.keys():
            recovery_message = {'type': 'recovery_verification', 'user_id': user_id, 'content': f'Recovery verification for {user_id}'}
            await self.ws_manager.send_to_user(user_id, recovery_message)
        await asyncio.sleep(0.2)
        working_users = 0
        for user_id in user_scenarios.keys():
            mock_ws = self.mock_websockets[user_id]
            if len(mock_ws._sent_messages) > 0:
                working_users += 1
        self.assertGreaterEqual(working_users, 3, 'Most users should be functional after recovery')

    async def test_resource_cleanup_during_failures(self):
        """
        Test proper resource cleanup when connections fail.
        
        BVJ: Prevents memory leaks and resource exhaustion that would
        degrade chat performance over time, especially important for long-running systems.
        """
        initial_connections = len(self.ws_manager._connections)
        initial_user_connections = len(self.ws_manager._user_connections)
        temp_users = []
        for i in range(5):
            user_id = f'temp_failure_user_{i}'
            connection_id = str(uuid.uuid4())
            failing_ws = MockWebSocketState(user_id, initial_healthy=False)
            connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=failing_ws, connected_at=datetime.now(timezone.utc))
            await self.ws_manager.add_connection(connection)
            temp_users.append((user_id, connection_id))
        for user_id, _ in temp_users:
            message = {'type': 'failure_cleanup_test', 'content': f'Test message for {user_id}'}
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.5)
        for user_id, connection_id in temp_users:
            await self.ws_manager.remove_connection(connection_id)
        final_connections = len(self.ws_manager._connections)
        final_user_connections = len(self.ws_manager._user_connections)
        self.assertEqual(final_connections, initial_connections, 'Connection count should return to initial state after cleanup')
        stats = self.ws_manager.get_stats()
        self.assertEqual(stats['total_connections'], initial_connections, 'Stats should reflect proper cleanup')
        test_user = 'lifecycle_user_00'
        if self.ws_manager.is_connection_active(test_user):
            verification_message = {'type': 'cleanup_verification', 'content': 'Verify existing connections still work after cleanup'}
            await self.ws_manager.send_to_user(test_user, verification_message)
            await asyncio.sleep(0.1)
            mock_ws = self.mock_websockets[test_user]
            self.assertGreater(len(mock_ws._sent_messages), 0, 'Existing connections should still work after cleanup')

    async def asyncTearDown(self):
        """Clean up connection lifecycle test resources."""
        for user_id, user_data in self.test_users.items():
            connection_id = user_data['connection_id']
            try:
                await self.ws_manager.remove_connection(connection_id)
            except Exception as e:
                logger.warning(f'Error removing connection {connection_id}: {e}')
        self.test_users.clear()
        self.mock_websockets.clear()
        self.connections.clear()
        await super().asyncTearDown()
        logger.info('Connection lifecycle test teardown completed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')