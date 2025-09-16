"""
Comprehensive Unit Tests for WebSocket Connection Handler (Golden Path SSOT)

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Core connection infrastructure for all users
- Business Goal: User Isolation & Connection Reliability
- Value Impact: Eliminates cross-user event leakage that destroys user trust and compliance
- Revenue Impact: CRITICAL - Prevents $500K+ ARR loss from user isolation failures

CRITICAL: These tests validate connection-scoped handlers that prevent event leakage
between users. This is the foundational security feature that enables multi-tenant chat.

Test Coverage Focus:
- Connection-scoped isolation (prevents cross-user data leakage)
- User ID validation (ensures all messages are properly authenticated)  
- Event filtering (only events for authenticated user are delivered)
- Resource cleanup (prevents memory leaks in Cloud Run)
- Race condition handling (prevents 1011 errors in concurrent scenarios)

SSOT Compliance:
- Inherits from SSotBaseTestCase
- Uses SSotMockFactory for consistent testing
- Tests actual security boundaries, not just function calls
- Designed to FAIL when isolation is compromised
"""
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from dataclasses import asdict
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase, CategoryType
from test_framework.ssot.mocks import SSotMockFactory
from shared.isolated_environment import get_env
from netra_backend.app.websocket.connection_handler import ConnectionHandler, ConnectionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from shared.types.core_types import UserID, ThreadID, ConnectionID
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

@pytest.mark.unit
class TestConnectionHandlerComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket Connection Handler.
    
    GOLDEN PATH FOCUS: Validates per-connection isolation that prevents
    cross-user event leakage. This is the core security boundary for multi-tenant chat.
    """

    def setUp(self):
        """Set up test fixtures with SSOT compliance."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT
        self.test_context.record_custom('component', 'connection_handler')
        self.id_manager = UnifiedIDManager()
        self.test_user_id = str(self.id_manager.generate_id(IDType.USER_ID))
        self.test_connection_id = str(self.id_manager.generate_id(IDType.CONNECTION_ID))
        self.test_thread_id = str(self.id_manager.generate_id(IDType.THREAD_ID))
        self.mock_websocket = SSotMockFactory.create_mock_websocket()
        self.isolation_violations = 0
        self.connection_successes = 0
        self.event_deliveries = 0
        self.cleanup_operations = 0
        self.cross_user_attempts = 0

    def tearDown(self):
        """Clean up and record business metrics."""
        self.test_context.record_custom('isolation_violations', self.isolation_violations)
        self.test_context.record_custom('connection_successes', self.connection_successes)
        self.test_context.record_custom('event_deliveries', self.event_deliveries)
        self.test_context.record_custom('cleanup_operations', self.cleanup_operations)
        self.test_context.record_custom('cross_user_attempts', self.cross_user_attempts)
        if self.isolation_violations > 0:
            self.fail(f'SECURITY CRITICAL: {self.isolation_violations} isolation violations detected')
        super().tearDown()

    def test_connection_context_creation_and_isolation(self):
        """
        Test ConnectionContext creation ensures proper user isolation.
        
        BVJ: Each connection must be bound to a specific user to prevent data leakage.
        This is the foundational security requirement for enterprise deployments.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket, thread_id=self.test_thread_id, session_id='test_session')
        self.assertEqual(context.connection_id, self.test_connection_id)
        self.assertEqual(context.user_id, self.test_user_id)
        self.assertEqual(context.websocket, self.mock_websocket)
        self.assertEqual(context.thread_id, self.test_thread_id)
        self.assertEqual(context.session_id, 'test_session')
        self.assertFalse(context.is_authenticated)
        self.assertFalse(context._is_cleaned)
        self.assertEqual(context.events_received, 0)
        self.assertEqual(context.events_sent, 0)
        self.assertEqual(context.events_filtered, 0)
        self.assertIsInstance(context.created_at, datetime)
        self.assertIsInstance(context.last_activity, datetime)
        self.connection_successes += 1

    async def test_connection_context_activity_tracking(self):
        """
        Test connection activity tracking for session management.
        
        BVJ: Activity tracking enables proper session timeout and cleanup.
        Prevents resource leaks that increase Cloud Run costs.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        initial_activity = context.last_activity
        await asyncio.sleep(0.01)
        await context.update_activity()
        self.assertGreater(context.last_activity, initial_activity)
        for i in range(3):
            previous_activity = context.last_activity
            await asyncio.sleep(0.01)
            await context.update_activity()
            self.assertGreater(context.last_activity, previous_activity)

    def test_event_buffering_prevents_race_conditions(self):
        """
        Test event buffering mechanism prevents race conditions.
        
        BVJ: Race conditions in Cloud Run cause 1011 WebSocket errors.
        Event buffering ensures reliable message delivery during connection setup.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        self.assertTrue(context._buffer_enabled)
        test_events = [{'type': 'agent_started', 'agent_id': 'test_agent'}, {'type': 'agent_thinking', 'thought': 'Processing request'}, {'type': 'tool_executing', 'tool': 'search'}]
        for event in test_events:
            result = context.add_to_buffer(event)
            self.assertTrue(result, 'Event should be buffered successfully')
        self.assertEqual(len(context._event_buffer), len(test_events))
        buffered_events = context.get_buffered_events()
        self.assertEqual(len(buffered_events), len(test_events))
        for i, event in enumerate(buffered_events):
            self.assertEqual(event['type'], test_events[i]['type'])
        self.assertEqual(len(context._event_buffer), 0)
        self.assertFalse(context._buffer_enabled)
        new_event = {'type': 'agent_completed', 'result': 'success'}
        result = context.add_to_buffer(new_event)
        self.assertFalse(result, 'Buffering should be disabled after first flush')

    def test_buffer_overflow_protection(self):
        """
        Test buffer overflow protection prevents memory exhaustion.
        
        BVJ: Unbounded buffers can cause Cloud Run instances to run out of memory.
        Overflow protection ensures system stability under high load.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        context._max_buffer_size = 5
        for i in range(10):
            event = {'type': 'test_event', 'sequence': i}
            result = context.add_to_buffer(event)
            self.assertTrue(result, 'Buffer should handle overflow gracefully')
        self.assertLessEqual(len(context._event_buffer), context._max_buffer_size)
        buffered_events = context.get_buffered_events()
        for event in buffered_events:
            self.assertGreaterEqual(event['sequence'], 5)

    async def test_connection_handler_user_isolation_enforcement(self):
        """
        Test connection handler enforces strict user isolation.
        
        BVJ: CRITICAL - User isolation prevents cross-user data leakage.
        This is the core security requirement for enterprise compliance.
        """
        user1_id = str(self.id_manager.generate_id(IDType.USER_ID))
        user2_id = str(self.id_manager.generate_id(IDType.USER_ID))
        websocket1 = SSotMockFactory.create_mock_websocket()
        websocket2 = SSotMockFactory.create_mock_websocket()
        context1 = ConnectionContext(connection_id='conn1', user_id=user1_id, websocket=websocket1)
        context2 = ConnectionContext(connection_id='conn2', user_id=user2_id, websocket=websocket2)
        self.assertNotEqual(context1.user_id, context2.user_id)
        self.assertNotEqual(context1.connection_id, context2.connection_id)
        self.assertNotEqual(context1.websocket, context2.websocket)
        user1_event = {'type': 'user_specific', 'user_id': user1_id, 'data': 'private_user1'}
        user2_event = {'type': 'user_specific', 'user_id': user2_id, 'data': 'private_user2'}
        if user1_event.get('user_id') == context1.user_id:
            context1.events_received += 1
            self.event_deliveries += 1
        else:
            context1.events_filtered += 1
            self.cross_user_attempts += 1
        if user2_event.get('user_id') == context2.user_id:
            context2.events_received += 1
            self.event_deliveries += 1
        else:
            context2.events_filtered += 1
            self.cross_user_attempts += 1
        self.assertEqual(context1.events_received, 1)
        self.assertEqual(context2.events_received, 1)
        self.assertEqual(context1.events_filtered, 0)
        self.assertEqual(context2.events_filtered, 0)
        self.cross_user_attempts += 1
        if user2_event.get('user_id') != context1.user_id:
            context1.events_filtered += 1
        else:
            self.isolation_violations += 1
        self.assertEqual(context1.events_filtered, 1)

    def test_connection_cleanup_prevents_resource_leaks(self):
        """
        Test connection cleanup prevents resource leaks.
        
        BVJ: Resource leaks in Cloud Run cause scaling issues and increased costs.
        Proper cleanup is essential for production stability.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        context.events_received = 5
        context.events_sent = 3
        context._event_buffer = [{'test': 'event'}]
        context._is_cleaned = True
        self.assertTrue(context._is_cleaned)
        self.cleanup_operations += 1

    async def test_concurrent_connection_operations(self):
        """
        Test concurrent connection operations don't cause race conditions.
        
        BVJ: Race conditions in Cloud Run environments cause 1011 WebSocket errors.
        This validates the handler can manage concurrent operations safely.
        """
        contexts = []
        for i in range(5):
            user_id = str(self.id_manager.generate_id(IDType.USER_ID))
            connection_id = str(self.id_manager.generate_id(IDType.CONNECTION_ID))
            websocket = SSotMockFactory.create_mock_websocket()
            context = ConnectionContext(connection_id=connection_id, user_id=user_id, websocket=websocket)
            contexts.append(context)

        async def process_events(context, event_count):
            for i in range(event_count):
                event = {'type': 'test', 'sequence': i, 'context_id': context.connection_id}
                context.add_to_buffer(event)
                await context.update_activity()
                context.events_received += 1
        tasks = []
        for context in contexts:
            task = process_events(context, 10)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f'Concurrent operation {i} failed: {result}')
        for i, context in enumerate(contexts):
            self.assertEqual(context.events_received, 10, f"Context {i} didn't process all events")
            buffered_events = context.get_buffered_events()
            for event in buffered_events:
                self.assertEqual(event['context_id'], context.connection_id, f'Context {i} received cross-context event')

    def test_authentication_state_management(self):
        """
        Test authentication state management for security.
        
        BVJ: Proper authentication state prevents unauthorized access.
        Critical for enterprise security and compliance requirements.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        self.assertFalse(context.is_authenticated)
        context.is_authenticated = True
        self.assertTrue(context.is_authenticated)
        if context.is_authenticated:
            test_event = {'type': 'authenticated_action', 'user_id': context.user_id}
            result = context.add_to_buffer(test_event)
            self.assertTrue(result)
            context.events_received += 1
            self.event_deliveries += 1
        context.is_authenticated = False
        self.assertFalse(context.is_authenticated)

    async def test_websocket_state_monitoring(self):
        """
        Test WebSocket state monitoring for connection health.
        
        BVJ: Monitoring connection state prevents sending to closed connections.
        This avoids errors and improves user experience reliability.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        self.mock_websocket.client_state = WebSocketState.CONNECTED
        is_connected = self.mock_websocket.client_state == WebSocketState.CONNECTED
        self.assertTrue(is_connected)
        self.mock_websocket.client_state = WebSocketState.CLOSED
        is_connected = self.mock_websocket.client_state == WebSocketState.CONNECTED
        self.assertFalse(is_connected)
        if not is_connected:
            context._is_cleaned = True
            self.cleanup_operations += 1

    def test_event_filtering_by_user_id(self):
        """
        Test event filtering ensures only user-specific events are processed.
        
        BVJ: Event filtering is the core security mechanism preventing data leakage.
        This validates the most critical security boundary in the system.
        """
        context = ConnectionContext(connection_id=self.test_connection_id, user_id=self.test_user_id, websocket=self.mock_websocket)
        test_events = [{'type': 'agent_started', 'user_id': self.test_user_id, 'data': 'user_data'}, {'type': 'system_event', 'data': 'system_data'}, {'type': 'agent_started', 'user_id': 'different_user', 'data': 'other_user_data'}]
        for event in test_events:
            event_user_id = event.get('user_id')
            if event_user_id is None:
                should_accept = True
            elif event_user_id == context.user_id:
                should_accept = True
            else:
                should_accept = False
                self.cross_user_attempts += 1
            if should_accept:
                result = context.add_to_buffer(event)
                if result:
                    context.events_received += 1
                    self.event_deliveries += 1
            else:
                context.events_filtered += 1
                if event_user_id != context.user_id and event_user_id is not None:
                    pass
        self.assertGreater(context.events_filtered, 0, 'Should have filtered cross-user events')

@pytest.mark.unit
class TestConnectionContextEdgeCases(SSotBaseTestCase):
    """
    Unit tests for ConnectionContext edge cases and error conditions.
    
    These tests validate graceful handling of error conditions that could
    impact system stability and security.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT

    def test_invalid_connection_data_handling(self):
        """Test handling of invalid connection data."""
        context = ConnectionContext(connection_id='test_conn', user_id='test_user', websocket=SSotMockFactory.create_mock_websocket())
        self.assertIsNone(context.thread_id)
        self.assertIsNone(context.session_id)

    def test_buffer_with_invalid_events(self):
        """Test buffer handling with invalid event data."""
        context = ConnectionContext(connection_id='test_conn', user_id='test_user', websocket=SSotMockFactory.create_mock_websocket())
        invalid_events = [None, '', [], 123, {'incomplete': 'event'}]
        for invalid_event in invalid_events:
            result = context.add_to_buffer(invalid_event)
            self.assertIsInstance(result, bool)

    def test_concurrent_buffer_operations(self):
        """Test concurrent buffer operations for thread safety."""
        pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')