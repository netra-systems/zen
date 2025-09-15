"""
WebSocket Multi-User Routing Integration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Multi-User Chat Reliability 
- Value Impact: Ensures 8+ concurrent users get correct messages with zero cross-user leakage
- Strategic Impact: MISSION CRITICAL - prevents User A seeing User B's messages, core chat isolation

This test suite validates WebSocket routing accuracy under concurrent multi-user scenarios.
Tests the core isolation that prevents cross-user message leakage - the most critical
business risk for chat applications.

BUSINESS IMPACT: Each test prevents specific user isolation failures that would destroy user trust.
"""
import asyncio
import pytest
import uuid
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import AsyncMock, Mock, MagicMock, call
from concurrent.futures import ThreadPoolExecutor
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, UserWebSocketEmitter, UserWebSocketContext, WebSocketEvent
from test_framework.ssot.base_test_case import SSotBaseTestCase
logger = central_logger.get_logger(__name__)

@pytest.mark.integration
class TestWebSocketMultiUserRoutingIntegration(SSotBaseTestCase):
    """
    Integration tests for multi-user WebSocket routing with complete isolation.
    
    Tests critical multi-user scenarios that affect chat business value:
    - Message routing accuracy (User A  ->  User A only)
    - Connection multiplexing (8+ concurrent users)
    - Cross-user isolation verification
    - High-volume message routing under load
    - Connection cleanup and resource management
    
    BUSINESS IMPACT: Prevents cross-user message leakage that would destroy user trust.
    """

    async def asyncSetUp(self):
        """Set up multi-user WebSocket routing test environment."""
        await super().asyncSetUp()
        self.ws_manager = UnifiedWebSocketManager()
        self.bridge_factory = WebSocketBridgeFactory()
        self.test_users = {}
        self.user_websockets = {}
        self.user_emitters = {}
        for i in range(10):
            user_id = f'user_{i:02d}'
            thread_id = f'thread_{i:02d}'
            connection_id = str(uuid.uuid4())
            mock_websocket = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.user_id = user_id
            mock_websocket.connection_id = connection_id
            mock_websocket._sent_messages = []

            async def capture_message(data, websocket=mock_websocket):
                """Capture messages for verification."""
                websocket._sent_messages.append({'data': data.copy() if isinstance(data, dict) else data, 'timestamp': datetime.now(timezone.utc), 'user_id': websocket.user_id})
            mock_websocket.send_json.side_effect = capture_message
            connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_websocket, connected_at=datetime.now(timezone.utc), metadata={'thread_id': thread_id})
            await self.ws_manager.add_connection(connection)
            self.test_users[user_id] = {'thread_id': thread_id, 'connection_id': connection_id, 'connection': connection}
            self.user_websockets[user_id] = mock_websocket
        logger.info(f'Multi-user routing test setup completed with {len(self.test_users)} users')

    async def test_basic_multi_user_message_routing(self):
        """
        Test basic message routing to correct users.
        
        BVJ: Fundamental routing accuracy - ensures messages reach intended recipients.
        This is the foundation of chat reliability.
        """
        test_messages = []
        for user_id in self.test_users.keys():
            message = {'type': 'user_specific_test', 'user_id': user_id, 'content': f'Message for {user_id}', 'timestamp': datetime.now(timezone.utc).isoformat(), 'test_id': str(uuid.uuid4())}
            test_messages.append((user_id, message))
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.1)
        for user_id, expected_message in test_messages:
            mock_websocket = self.user_websockets[user_id]
            self.assertEqual(len(mock_websocket._sent_messages), 1, f'User {user_id} should receive exactly 1 message')
            sent_message = mock_websocket._sent_messages[0]
            self.assertEqual(sent_message['data']['user_id'], user_id)
            self.assertEqual(sent_message['data']['content'], f'Message for {user_id}')
            self.assertEqual(sent_message['user_id'], user_id)
        all_user_ids = set(self.test_users.keys())
        for user_id, expected_message in test_messages:
            mock_websocket = self.user_websockets[user_id]
            sent_message = mock_websocket._sent_messages[0]['data']
            other_user_ids = all_user_ids - {user_id}
            message_str = json.dumps(sent_message)
            for other_user_id in other_user_ids:
                self.assertNotIn(other_user_id, message_str, f'User {user_id} received message containing {other_user_id}')

    async def test_concurrent_message_routing_isolation(self):
        """
        Test concurrent message sending with strict isolation verification.
        
        BVJ: Prevents race conditions that could cause cross-user message leakage
        under high concurrent load (critical for multi-user chat).
        """
        for mock_ws in self.user_websockets.values():
            mock_ws._sent_messages.clear()

        async def send_user_messages(user_id: str, message_count: int):
            """Send multiple messages to a specific user."""
            messages = []
            for i in range(message_count):
                message = {'type': 'concurrent_test', 'user_id': user_id, 'message_index': i, 'content': f'Concurrent message {i} for {user_id}', 'test_batch': str(uuid.uuid4()), 'timestamp': datetime.now(timezone.utc).isoformat()}
                messages.append(message)
                await self.ws_manager.send_to_user(user_id, message)
            return messages
        message_count = 20
        tasks = [send_user_messages(user_id, message_count) for user_id in self.test_users.keys()]
        sent_messages_per_user = await asyncio.gather(*tasks)
        await asyncio.sleep(0.5)
        for i, user_id in enumerate(self.test_users.keys()):
            mock_websocket = self.user_websockets[user_id]
            expected_messages = sent_messages_per_user[i]
            self.assertEqual(len(mock_websocket._sent_messages), message_count, f'User {user_id} should receive exactly {message_count} messages')
            for j, sent_message in enumerate(mock_websocket._sent_messages):
                data = sent_message['data']
                self.assertEqual(data['user_id'], user_id, f'Message {j} for {user_id} has wrong user_id')
                self.assertIn(user_id, data['content'], f"Message {j} content doesn't match user {user_id}")
            for j in range(message_count):
                sent_message = mock_websocket._sent_messages[j]['data']
                self.assertEqual(sent_message['message_index'], j, f'Message ordering broken for {user_id} at index {j}')

    async def test_user_connection_multiplexing(self):
        """
        Test connection multiplexing with multiple connections per user.
        
        BVJ: Supports users with multiple browser tabs/devices while maintaining
        message delivery to all user connections.
        """
        multi_connection_users = ['user_00', 'user_01', 'user_02']
        additional_connections = {}
        for user_id in multi_connection_users:
            connection_id_2 = str(uuid.uuid4())
            mock_websocket_2 = AsyncMock()
            mock_websocket_2._sent_messages = []

            async def capture_message_2(data, ws=mock_websocket_2, uid=user_id):
                ws._sent_messages.append({'data': data.copy() if isinstance(data, dict) else data, 'timestamp': datetime.now(timezone.utc), 'user_id': uid})
            mock_websocket_2.send_json.side_effect = capture_message_2
            connection_2 = WebSocketConnection(connection_id=connection_id_2, user_id=user_id, websocket=mock_websocket_2, connected_at=datetime.now(timezone.utc))
            await self.ws_manager.add_connection(connection_2)
            additional_connections[user_id] = mock_websocket_2
        for mock_ws in self.user_websockets.values():
            mock_ws._sent_messages.clear()
        for mock_ws in additional_connections.values():
            mock_ws._sent_messages.clear()
        for user_id in multi_connection_users:
            message = {'type': 'multi_connection_test', 'user_id': user_id, 'content': f'Multi-connection message for {user_id}', 'timestamp': datetime.now(timezone.utc).isoformat()}
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.1)
        for user_id in multi_connection_users:
            mock_ws_1 = self.user_websockets[user_id]
            self.assertEqual(len(mock_ws_1._sent_messages), 1, f'First connection for {user_id} should receive message')
            mock_ws_2 = additional_connections[user_id]
            self.assertEqual(len(mock_ws_2._sent_messages), 1, f'Second connection for {user_id} should receive message')
            msg_1 = mock_ws_1._sent_messages[0]['data']
            msg_2 = mock_ws_2._sent_messages[0]['data']
            self.assertEqual(msg_1, msg_2, f'Messages should be identical for {user_id}')
            self.assertEqual(msg_1['user_id'], user_id)
            self.assertEqual(msg_2['user_id'], user_id)

    async def test_high_volume_routing_accuracy(self):
        """
        Test routing accuracy under high message volume.
        
        BVJ: Ensures chat reliability under peak usage - prevents message
        mixing or loss during high-traffic periods.
        """
        for mock_ws in self.user_websockets.values():
            mock_ws._sent_messages.clear()
        messages_per_user = 100

        async def flood_user_messages(user_id: str):
            """Send flood of messages to specific user."""
            for i in range(messages_per_user):
                message = {'type': 'flood_test', 'user_id': user_id, 'sequence': i, 'content': f'Flood message {i} for {user_id}', 'batch_id': str(uuid.uuid4())[:8], 'timestamp': datetime.now(timezone.utc).isoformat()}
                await self.ws_manager.send_to_user(user_id, message)
                if i % 10 == 0:
                    await asyncio.sleep(0.001)
        start_time = time.time()
        tasks = [flood_user_messages(user_id) for user_id in self.test_users.keys()]
        await asyncio.gather(*tasks)
        await asyncio.sleep(2.0)
        end_time = time.time()
        total_expected = len(self.test_users) * messages_per_user
        logger.info(f'High volume test: {total_expected} messages in {end_time - start_time:.2f}s')
        total_received = 0
        for user_id in self.test_users.keys():
            mock_websocket = self.user_websockets[user_id]
            received_count = len(mock_websocket._sent_messages)
            total_received += received_count
            min_expected = int(messages_per_user * 0.95)
            self.assertGreaterEqual(received_count, min_expected, f'User {user_id} should receive at least {min_expected} messages')
            for i, sent_message in enumerate(mock_websocket._sent_messages):
                data = sent_message['data']
                self.assertEqual(data['user_id'], user_id, f"Message {i} for {user_id} has wrong user_id: {data['user_id']}")
        delivery_rate = total_received / total_expected
        self.assertGreater(delivery_rate, 0.9, f'Message delivery rate too low: {delivery_rate:.2%}')

    async def test_user_isolation_verification(self):
        """
        Test complete user isolation - ensures no data leakage between users.
        
        BVJ: CRITICAL - prevents the most serious security/privacy violation
        where users see each other's sensitive data.
        """
        sensitive_data = {}
        for user_id in self.test_users.keys():
            sensitive_data[user_id] = {'type': 'sensitive_data', 'user_id': user_id, 'secret_token': f'SECRET_{user_id}_{uuid.uuid4()}', 'private_message': f'CONFIDENTIAL: Private data for {user_id}', 'api_key': f'API_KEY_{user_id}', 'personal_info': {'user_specific_id': user_id, 'session': str(uuid.uuid4()), 'internal_data': f'INTERNAL_{user_id}'}}
        for mock_ws in self.user_websockets.values():
            mock_ws._sent_messages.clear()
        for user_id, data in sensitive_data.items():
            await self.ws_manager.send_to_user(user_id, data)
        await asyncio.sleep(0.1)
        for user_id in self.test_users.keys():
            mock_websocket = self.user_websockets[user_id]
            self.assertEqual(len(mock_websocket._sent_messages), 1, f'User {user_id} should receive exactly one message')
            received_data = mock_websocket._sent_messages[0]['data']
            self.assertEqual(received_data['user_id'], user_id)
            self.assertIn(user_id, received_data['secret_token'])
            self.assertIn(user_id, received_data['private_message'])
            self.assertEqual(received_data['personal_info']['user_specific_id'], user_id)
            other_users = set(self.test_users.keys()) - {user_id}
            message_str = json.dumps(received_data)
            for other_user_id in other_users:
                other_secret = f'SECRET_{other_user_id}'
                other_api = f'API_KEY_{other_user_id}'
                other_internal = f'INTERNAL_{other_user_id}'
                self.assertNotIn(other_secret, message_str, f"User {user_id} received {other_user_id}'s secret token")
                self.assertNotIn(other_api, message_str, f"User {user_id} received {other_user_id}'s API key")
                self.assertNotIn(other_internal, message_str, f"User {user_id} received {other_user_id}'s internal data")
                self.assertNotIn(f'CONFIDENTIAL: Private data for {other_user_id}', message_str)

    async def test_connection_failure_isolation(self):
        """
        Test that connection failures don't affect other users.
        
        BVJ: Ensures individual connection issues don't cause system-wide
        chat failures affecting all users.
        """
        failing_users = ['user_01', 'user_03', 'user_05']
        healthy_users = [u for u in self.test_users.keys() if u not in failing_users]
        for user_id in failing_users:
            mock_websocket = self.user_websockets[user_id]
            mock_websocket.send_json.side_effect = Exception(f'Connection failed for {user_id}')
        for user_id in healthy_users:
            self.user_websockets[user_id]._sent_messages.clear()
        for user_id in self.test_users.keys():
            message = {'type': 'failure_test', 'user_id': user_id, 'content': f'Test message for {user_id}', 'timestamp': datetime.now(timezone.utc).isoformat()}
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.2)
        for user_id in healthy_users:
            mock_websocket = self.user_websockets[user_id]
            self.assertEqual(len(mock_websocket._sent_messages), 1, f'Healthy user {user_id} should still receive messages')
            received_data = mock_websocket._sent_messages[0]['data']
            self.assertEqual(received_data['user_id'], user_id)

    async def test_message_ordering_per_user(self):
        """
        Test message ordering preservation per user.
        
        BVJ: Ensures chat message chronology is maintained for each user,
        critical for coherent conversation flow.
        """
        for mock_ws in self.user_websockets.values():
            mock_ws._sent_messages.clear()
        sequence_length = 50

        async def send_ordered_sequence(user_id: str):
            """Send ordered sequence to specific user."""
            for i in range(sequence_length):
                message = {'type': 'ordering_test', 'user_id': user_id, 'sequence_number': i, 'content': f'Message {i} for {user_id}', 'timestamp': datetime.now(timezone.utc).isoformat()}
                await self.ws_manager.send_to_user(user_id, message)
                await asyncio.sleep(0.001)
        test_users = list(self.test_users.keys())[:5]
        tasks = [send_ordered_sequence(user_id) for user_id in test_users]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.5)
        for user_id in test_users:
            mock_websocket = self.user_websockets[user_id]
            messages = mock_websocket._sent_messages
            self.assertEqual(len(messages), sequence_length, f'User {user_id} should receive all {sequence_length} messages')
            for i, sent_message in enumerate(messages):
                data = sent_message['data']
                expected_seq = i
                actual_seq = data['sequence_number']
                self.assertEqual(actual_seq, expected_seq, f'Message ordering broken for {user_id}: position {i} has sequence {actual_seq}, expected {expected_seq}')
                self.assertEqual(data['user_id'], user_id)

    async def test_resource_cleanup_on_disconnection(self):
        """
        Test proper resource cleanup when users disconnect.
        
        BVJ: Prevents memory leaks and resource exhaustion that would
        degrade chat performance over time.
        """
        disconnect_users = ['user_06', 'user_07', 'user_08']
        initial_connections = len(self.ws_manager._connections)
        initial_user_connections = len(self.ws_manager._user_connections)
        for user_id in disconnect_users:
            connection_id = self.test_users[user_id]['connection_id']
            await self.ws_manager.remove_connection(connection_id)
        remaining_connections = len(self.ws_manager._connections)
        remaining_user_connections = len(self.ws_manager._user_connections)
        expected_removed = len(disconnect_users)
        self.assertEqual(remaining_connections, initial_connections - expected_removed, 'Connection count should decrease by number of disconnected users')
        for user_id in disconnect_users:
            mock_websocket = self.user_websockets[user_id]
            mock_websocket._sent_messages.clear()
        for user_id in self.test_users.keys():
            message = {'type': 'cleanup_test', 'user_id': user_id, 'content': f'Post-disconnect message for {user_id}'}
            await self.ws_manager.send_to_user(user_id, message)
        await asyncio.sleep(0.1)
        for user_id in disconnect_users:
            mock_websocket = self.user_websockets[user_id]
            self.assertEqual(len(mock_websocket._sent_messages), 0, f'Disconnected user {user_id} should not receive messages')
        connected_users = [u for u in self.test_users.keys() if u not in disconnect_users]
        for user_id in connected_users:
            mock_websocket = self.user_websockets[user_id]
            self.assertGreater(len(mock_websocket._sent_messages), 0, f'Connected user {user_id} should still receive messages')

    async def asyncTearDown(self):
        """Clean up multi-user routing test resources."""
        for user_id, user_data in self.test_users.items():
            connection_id = user_data['connection_id']
            await self.ws_manager.remove_connection(connection_id)
        self.test_users.clear()
        self.user_websockets.clear()
        self.user_emitters.clear()
        await super().asyncTearDown()
        logger.info('Multi-user routing test teardown completed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')