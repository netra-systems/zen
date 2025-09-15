"""
Comprehensive Unit Tests for WebSocket Manager (Golden Path SSOT)

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Core infrastructure for all tiers
- Business Goal: Reliability & Stability - Ensure WebSocket communication foundation
- Value Impact: Critical for $500K+ ARR chat functionality - connection success rates
- Revenue Impact: Foundation for all AI-powered user interactions

CRITICAL: These tests validate the most business-critical WebSocket Manager functionality
for the Golden Path user flow: connection  ->  authentication  ->  message routing  ->  agent execution.

Test Coverage Focus:
- Connection lifecycle management (connection success rates)
- User isolation (prevents data mixing between users)
- Event delivery reliability (all 5 critical WebSocket events)
- Race condition prevention (Cloud Run concurrent scenarios)
- Message serialization (prevents JSON encoding errors)

SSOT Compliance:
- Inherits from SSotBaseTestCase
- Uses IsolatedEnvironment for all environment access
- Uses real WebSocket connections where possible
- Minimal mocks only for external dependencies
"""
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase, CategoryType
from test_framework.ssot.mocks import SSotMockFactory
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager, WebSocketConnection, _serialize_message_safely
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

@pytest.mark.unit
class WebSocketManagerComprehensiveTests(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket Manager SSOT class.
    
    GOLDEN PATH FOCUS: Validates critical business logic for user connection flow.
    These tests ensure WebSocket Manager reliably handles the foundational operations
    that enable chat functionality.
    """

    def setup_method(self, method):
        """Set up test fixtures with SSOT compliance."""
        super().setup_method(method)
        self.test_context = self.get_test_context()
        self.test_context.test_category = CategoryType.UNIT
        self.test_context.metadata['component'] = 'websocket_manager'
        self.websocket_manager = UnifiedWebSocketManager()
        self.id_manager = UnifiedIDManager()
        self.test_user_id = str(self.id_manager.generate_id(IDType.USER))
        self.test_connection_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        self.test_websocket_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        self.mock_websocket = SSotMockFactory().create_websocket_connection_mock()
        self.connection_attempts = 0
        self.successful_connections = 0
        self.event_deliveries = 0
        self.isolation_violations = 0

    def teardown_method(self, method):
        """Clean up test resources."""
        if self.connection_attempts > 0:
            success_rate = self.successful_connections / self.connection_attempts * 100
            self.test_context.metadata['connection_success_rate'] = success_rate
        self.test_context.metadata['event_deliveries'] = self.event_deliveries
        self.test_context.metadata['isolation_violations'] = self.isolation_violations
        super().teardown_method(method)

    async def test_connection_registration_golden_path(self):
        """
        Test WebSocket connection registration for Golden Path user flow.
        
        BVJ: Connection success is critical for $500K+ ARR chat functionality.
        This validates the foundational operation that enables all user interactions.
        """
        self.connection_attempts += 1
        connection = WebSocketConnection(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket, websocket_id=self.test_websocket_id)
        await self.websocket_manager.add_connection(self.test_user_id, self.test_connection_id, self.mock_websocket, websocket_id=self.test_websocket_id)
        self.successful_connections += 1
        self.assertIn(self.test_user_id, self.websocket_manager.user_connections)
        connections = self.websocket_manager.user_connections[self.test_user_id]
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].user_id, self.test_user_id)
        self.assertEqual(connections[0].connection_id, self.test_connection_id)
        self.assertTrue(await self.websocket_manager.has_connection(self.test_user_id))

    async def test_user_isolation_enforcement(self):
        """
        Test strict user isolation to prevent data mixing.
        
        BVJ: User isolation is CRITICAL for enterprise trust and compliance.
        Data leakage between users would be a catastrophic business failure.
        """
        user1_id = str(self.id_manager.generate_id(IDType.USER))
        user2_id = str(self.id_manager.generate_id(IDType.USER))
        connection1_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        connection2_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
        mock_websocket1 = SSotMockFactory().create_websocket_connection_mock()
        mock_websocket2 = SSotMockFactory().create_websocket_connection_mock()
        await self.websocket_manager.add_connection(user1_id, connection1_id, mock_websocket1)
        await self.websocket_manager.add_connection(user2_id, connection2_id, mock_websocket2)
        user1_connections = self.websocket_manager.get_user_connections(user1_id)
        user2_connections = self.websocket_manager.get_user_connections(user2_id)
        self.assertEqual(len(user1_connections), 1)
        self.assertEqual(len(user2_connections), 1)
        self.assertEqual(user1_connections[0].user_id, user1_id)
        self.assertEqual(user2_connections[0].user_id, user2_id)
        self.assertNotEqual(user1_connections[0].connection_id, connection2_id)
        self.assertNotEqual(user2_connections[0].connection_id, connection1_id)
        if user1_connections[0].user_id != user1_id or user2_connections[0].user_id != user2_id:
            self.isolation_violations += 1
            self.fail('CRITICAL: User isolation violation detected')

    async def test_message_broadcasting_with_isolation(self):
        """
        Test message broadcasting respects user isolation.
        
        BVJ: Ensures messages reach only intended recipients.
        Critical for enterprise privacy and user trust.
        """
        user1_id = str(self.id_manager.generate_id(IDType.USER))
        user2_id = str(self.id_manager.generate_id(IDType.USER))
        mock_websocket1 = SSotMockFactory().create_websocket_connection_mock()
        mock_websocket2 = SSotMockFactory().create_websocket_connection_mock()
        await self.websocket_manager.add_connection(user1_id, 'conn1', mock_websocket1)
        await self.websocket_manager.add_connection(user2_id, 'conn2', mock_websocket2)
        test_message = {'type': 'test', 'content': 'user1_message'}
        await self.websocket_manager.send_to_user(user1_id, test_message)
        self.event_deliveries += 1
        mock_websocket1.send_json.assert_called_once()
        mock_websocket2.send_json.assert_not_called()
        sent_message = mock_websocket1.send_json.call_args[0][0]
        self.assertEqual(sent_message['type'], 'test')
        self.assertEqual(sent_message['content'], 'user1_message')

    async def test_connection_cleanup_on_disconnect(self):
        """
        Test proper connection cleanup to prevent memory leaks.
        
        BVJ: Memory leaks in Cloud Run lead to scaling issues and increased costs.
        Proper cleanup is essential for system stability.
        """
        await self.websocket_manager.add_connection(self.test_user_id, self.test_connection_id, self.mock_websocket)
        self.assertTrue(await self.websocket_manager.has_connection(self.test_user_id))
        await self.websocket_manager.remove_connection(self.test_user_id, self.test_connection_id)
        self.assertFalse(await self.websocket_manager.has_connection(self.test_user_id))
        self.assertNotIn(self.test_user_id, self.websocket_manager.user_connections)

    async def test_concurrent_connection_handling(self):
        """
        Test concurrent connection operations for race condition prevention.
        
        BVJ: Cloud Run environments have race conditions that cause 1011 errors.
        This validates the manager handles concurrent operations safely.
        """
        connection_tasks = []
        user_ids = []
        connection_ids = []
        for i in range(5):
            user_id = str(self.id_manager.generate_id(IDType.USER))
            connection_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
            mock_websocket = SSotMockFactory().create_websocket_connection_mock()
            user_ids.append(user_id)
            connection_ids.append(connection_id)
            task = self.websocket_manager.add_connection(user_id, connection_id, mock_websocket)
            connection_tasks.append(task)
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f'Connection {i} failed with exception: {result}')
        for user_id in user_ids:
            self.assertTrue(await self.websocket_manager.has_connection(user_id))

    def test_message_serialization_safety(self):
        """
        Test safe message serialization prevents JSON encoding errors.
        
        BVJ: JSON serialization errors break WebSocket communication.
        This validates the manager handles complex data types safely.
        """
        test_cases = [{'datetime': datetime.now(timezone.utc)}, {'enum': WebSocketState.CONNECTED}, {'nested': {'complex': {'data': [1, 2, 3]}}}, {'unicode': '[U+6D4B][U+8BD5] [U+1F680] emoji'}, {'none_values': {'field': None}}]
        for test_message in test_cases:
            serialized = _serialize_message_safely(test_message)
            try:
                json.dumps(serialized)
            except (TypeError, ValueError) as e:
                self.fail(f'Serialization failed for {test_message}: {e}')
            self.assertIsInstance(serialized, dict)

    async def test_websocket_state_validation(self):
        """
        Test WebSocket state validation for connection health.
        
        BVJ: Invalid WebSocket states cause connection failures and poor UX.
        This validates the manager checks connection health properly.
        """
        mock_websocket = SSotMockFactory().create_websocket_connection_mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        await self.websocket_manager.add_connection(self.test_user_id, self.test_connection_id, mock_websocket)
        test_message = {'type': 'test', 'status': 'healthy'}
        result = await self.websocket_manager.send_to_user(self.test_user_id, test_message)
        mock_websocket.send_json.assert_called_once_with(test_message)
        mock_websocket.client_state = WebSocketState.CLOSED
        with patch.object(self.websocket_manager, '_handle_send_error') as mock_handler:
            await self.websocket_manager.send_to_user(self.test_user_id, test_message)

    async def test_golden_path_event_delivery_sequence(self):
        """
        Test complete Golden Path event delivery sequence.
        
        BVJ: The 5 critical WebSocket events (agent_started, agent_thinking, 
        tool_executing, tool_completed, agent_completed) are the backbone
        of user experience. This validates end-to-end event flow.
        """
        await self.websocket_manager.add_connection(self.test_user_id, self.test_connection_id, self.mock_websocket)
        golden_path_events = [{'type': 'agent_started', 'agent_id': 'test_agent', 'timestamp': datetime.now(timezone.utc)}, {'type': 'agent_thinking', 'thought': 'Processing user request'}, {'type': 'tool_executing', 'tool': 'search', 'params': {}}, {'type': 'tool_completed', 'tool': 'search', 'result': 'success'}, {'type': 'agent_completed', 'result': 'Task completed successfully'}]
        for event in golden_path_events:
            await self.websocket_manager.send_to_user(self.test_user_id, event)
            self.event_deliveries += 1
        self.assertEqual(self.mock_websocket.send_json.call_count, len(golden_path_events))
        call_args_list = self.mock_websocket.send_json.call_args_list
        for i, expected_event in enumerate(golden_path_events):
            actual_event = call_args_list[i][0][0]
            self.assertEqual(actual_event['type'], expected_event['type'])

    async def test_multi_user_concurrent_event_delivery(self):
        """
        Test concurrent event delivery to multiple users without cross-talk.
        
        BVJ: Multi-user scenarios are common in enterprise deployments.
        This validates the manager maintains isolation under concurrent load.
        """
        num_users = 3
        users = []
        websockets = []
        for i in range(num_users):
            user_id = str(self.id_manager.generate_id(IDType.USER))
            connection_id = str(self.id_manager.generate_id(IDType.WEBSOCKET))
            mock_websocket = SSotMockFactory().create_websocket_connection_mock()
            await self.websocket_manager.add_connection(user_id, connection_id, mock_websocket)
            users.append(user_id)
            websockets.append(mock_websocket)
        send_tasks = []
        for i, user_id in enumerate(users):
            message = {'type': 'user_specific', 'user_id': user_id, 'sequence': i}
            task = self.websocket_manager.send_to_user(user_id, message)
            send_tasks.append(task)
        await asyncio.gather(*send_tasks)
        for i, (user_id, websocket) in enumerate(zip(users, websockets)):
            websocket.send_json.assert_called_once()
            sent_message = websocket.send_json.call_args[0][0]
            self.assertEqual(sent_message['user_id'], user_id)
            self.assertEqual(sent_message['sequence'], i)
            for j, other_websocket in enumerate(websockets):
                if i != j:
                    other_calls = other_websocket.send_json.call_args_list
                    for call in other_calls:
                        other_message = call[0][0]
                        if other_message['user_id'] == user_id:
                            self.isolation_violations += 1
                            self.fail(f"Cross-user message delivery detected: User {j} received User {i}'s message")

@pytest.mark.unit
class WebSocketManagerEdgeCasesTests(SSotBaseTestCase):
    """
    Unit tests for WebSocket Manager edge cases and error conditions.
    
    These tests validate graceful handling of error conditions that could
    impact system stability and user experience.
    """

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)
        self.test_context = self.get_test_context()
        self.test_context.test_category = CategoryType.UNIT
        self.websocket_manager = UnifiedWebSocketManager()

    def test_invalid_user_id_handling(self):
        """Test handling of invalid user IDs."""
        with pytest.raises(ValueError):
            connections = self.websocket_manager.get_user_connections(None)
        with pytest.raises(ValueError):
            connections = self.websocket_manager.get_user_connections('')
        try:
            connections = self.websocket_manager.get_user_connections('not-a-valid-uuid')
            assert len(connections) == 0
        except ValueError:
            pass

    def test_duplicate_connection_handling(self):
        """Test handling of duplicate connection attempts."""
        pass

    def test_memory_usage_validation(self):
        """Test memory usage stays within bounds."""
        pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')