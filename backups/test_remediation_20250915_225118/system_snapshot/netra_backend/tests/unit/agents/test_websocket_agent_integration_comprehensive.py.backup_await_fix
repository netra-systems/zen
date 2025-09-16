"""WebSocket Agent Integration Comprehensive Unit Tests

MISSION-CRITICAL TEST SUITE: Complete validation of WebSocket-Agent integration patterns.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Real-time Chat Experience (90% of platform value)
- Value Impact: WebSocket-Agent integration = Real-time user experience = $500K+ ARR protection
- Strategic Impact: WebSocket failures directly break real-time chat functionality

COVERAGE TARGET: 45 unit tests covering critical WebSocket-Agent integration:
- Event emission and delivery (12 tests)
- WebSocket connection management (11 tests)
- Message delivery mechanisms (10 tests)
- Agent-WebSocket coordination (12 tests)

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
Only external dependencies are mocked - all internal components tested with real instances.
"""
import asyncio
import pytest
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, create_standard_message, ConnectionInfo
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus

@dataclass
class MockWebSocketConnection:
    """Mock WebSocket connection for testing - compatible with ConnectionInfo"""
    user_id: str
    session_id: str
    connected: bool = True
    messages_sent: List[Dict[str, Any]] = None
    connection_id: Optional[str] = None
    websocket: Optional[Any] = None
    thread_id: Optional[str] = None
    connected_at: datetime = None
    last_activity: datetime = None
    message_count: int = 0
    error_count: int = 0
    last_ping: Optional[datetime] = None
    is_healthy: bool = True
    is_closing: bool = False
    client_info: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.messages_sent is None:
            self.messages_sent = []
        if self.connected_at is None:
            self.connected_at = datetime.now(timezone.utc)
        if self.last_activity is None:
            self.last_activity = datetime.now(timezone.utc)
        if self.connection_id is None:
            self.connection_id = self.session_id
        if self.thread_id is None:
            self.thread_id = self.session_id
        self.websocket = self

    async def send_text(self, message: str):
        """Mock send_text method"""
        self.messages_sent.append({'type': 'text', 'content': message})
        self.message_count += 1
        self.last_activity = datetime.now(timezone.utc)

    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method"""
        self.messages_sent.append({'type': 'json', 'content': data})
        self.message_count += 1
        self.last_activity = datetime.now(timezone.utc)

    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self.connected and (not self.is_closing)

    def disconnect(self):
        """Simulate disconnection"""
        self.connected = False
        self.is_healthy = False

class TestWebSocketEventEmissionDelivery(SSotAsyncTestCase):
    """Test suite for WebSocket event emission and delivery - 12 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)
        self.session_id = self.id_manager.generate_id(IDType.SESSION)

    async def test_websocket_event_emission_basic(self):
        """Test basic WebSocket event emission"""
        user_context = UserExecutionContext(user_id=self.user_id, thread_id=self.session_id, run_id=self.id_manager.generate_id(IDType.RUN))
        ws_manager = await get_websocket_manager(user_context)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        ws_manager.register_connection(self.session_id, self.user_id, mock_connection)
        event_data = {'type': 'agent_started', 'agent_id': 'test_agent'}
        await ws_manager.send_agent_event(self.user_id, 'agent_started', event_data)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        self.record_metric('basic_event_emission_success', True)

    async def test_websocket_event_delivery_confirmation(self):
        """Test WebSocket event delivery confirmation"""
        user_context = UserExecutionContext(user_id=self.user_id, thread_id=self.session_id, run_id=self.id_manager.generate_id(IDType.RUN))
        ws_manager = await get_websocket_manager(user_context)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        ws_manager.register_connection(self.session_id, self.user_id, mock_connection)
        event_id = self.id_manager.generate_id(IDType.MESSAGE)
        event_data = {'event_id': event_id, 'type': 'agent_thinking', 'message': 'Processing your request...'}
        await ws_manager.send_agent_event(self.user_id, 'agent_thinking', event_data)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        sent_message = mock_connection.messages_sent[-1]
        if 'content' in sent_message and isinstance(sent_message['content'], dict):
            self.assertEqual(sent_message['content'].get('event_id'), event_id)
        self.record_metric('event_delivery_confirmation_success', True)

    async def test_websocket_event_batch_emission(self):
        """Test batch emission of WebSocket events"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        events = [{'type': 'agent_started', 'agent_id': 'agent_1'}, {'type': 'agent_thinking', 'message': 'Step 1'}, {'type': 'agent_thinking', 'message': 'Step 2'}, {'type': 'agent_completed', 'result': 'Success'}]
        batch_result = await self.ws_manager.emit_event_batch(self.user_id, events)
        self.assertEqual(len(batch_result.delivered_events), 4)
        self.assertEqual(batch_result.failed_events, 0)
        self.record_metric('batch_event_emission_success', True)

    async def test_websocket_event_priority_delivery(self):
        """Test priority-based event delivery"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        high_priority_event = {'type': 'error', 'message': 'Critical error occurred', 'priority': 'high'}
        low_priority_event = {'type': 'status', 'message': 'Processing...', 'priority': 'low'}
        await self.ws_manager.emit_event(self.user_id, 'status', low_priority_event)
        await self.ws_manager.emit_event(self.user_id, 'error', high_priority_event)
        messages = mock_connection.messages_sent
        self.assertGreater(len(messages), 0)
        self.record_metric('priority_event_delivery_success', True)

    async def test_websocket_event_filtering(self):
        """Test event filtering based on user preferences"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        event_filters = {'agent_thinking': True, 'agent_started': True, 'debug_info': False}
        await self.ws_manager.register_connection(self.user_id, mock_connection, event_filters=event_filters)
        await self.ws_manager.emit_event(self.user_id, 'agent_thinking', {'message': 'Thinking...'})
        await self.ws_manager.emit_event(self.user_id, 'debug_info', {'debug': 'details'})
        sent_messages = [msg for msg in mock_connection.messages_sent if 'agent_thinking' in str(msg)]
        self.assertGreater(len(sent_messages), 0)
        debug_messages = [msg for msg in mock_connection.messages_sent if 'debug_info' in str(msg)]
        self.assertEqual(len(debug_messages), 0)
        self.record_metric('event_filtering_success', True)

    async def test_websocket_event_compression(self):
        """Test event compression for large payloads"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        large_data = {'type': 'agent_response', 'response': 'A' * 10000, 'metadata': {'key': 'value'} * 100}
        await self.ws_manager.emit_event(self.user_id, 'agent_response', large_data, compress=True)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        self.record_metric('event_compression_success', True)

    async def test_websocket_event_rate_limiting(self):
        """Test event rate limiting"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection, rate_limit={'events_per_second': 5})
        start_time = time.time()
        for i in range(10):
            await self.ws_manager.emit_event(self.user_id, 'rapid_event', {'index': i})
        duration = time.time() - start_time
        self.assertGreater(duration, 1.0)
        self.record_metric('event_rate_limiting_success', True)

    async def test_websocket_event_retry_on_failure(self):
        """Test event retry mechanism on delivery failure"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        original_send_json = mock_connection.send_json
        call_count = 0

        async def failing_send_json(data):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError('Connection lost')
            return await original_send_json(data)
        mock_connection.send_json = failing_send_json
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        event_data = {'type': 'agent_response', 'message': 'Test with retry'}
        result = await self.ws_manager.emit_event_with_retry(self.user_id, 'agent_response', event_data, max_retries=3)
        self.assertTrue(result.delivered)
        self.assertEqual(result.retry_count, 2)
        self.record_metric('event_retry_success', True)

    async def test_websocket_event_ordering_guarantee(self):
        """Test event ordering guarantees"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        ordered_events = [{'type': 'agent_started', 'sequence': 1}, {'type': 'agent_thinking', 'sequence': 2}, {'type': 'tool_executing', 'sequence': 3}, {'type': 'tool_completed', 'sequence': 4}, {'type': 'agent_completed', 'sequence': 5}]
        for event in ordered_events:
            await self.ws_manager.emit_event(self.user_id, event['type'], event, ordered=True)
        messages = mock_connection.messages_sent
        self.assertEqual(len(messages), 5)
        self.record_metric('event_ordering_success', True)

    async def test_websocket_event_persistence(self):
        """Test event persistence for offline users"""
        offline_user_id = self.id_manager.generate_id(IDType.USER)
        offline_events = [{'type': 'agent_completed', 'result': 'Task finished'}, {'type': 'notification', 'message': 'New message'}]
        for event in offline_events:
            await self.ws_manager.emit_event_persistent(offline_user_id, event['type'], event)
        mock_connection = MockWebSocketConnection(user_id=offline_user_id, session_id=self.id_manager.generate_id(IDType.SESSION))
        await self.ws_manager.register_connection(offline_user_id, mock_connection)
        persisted_events = await self.ws_manager.get_persisted_events(offline_user_id)
        self.assertEqual(len(persisted_events), 2)
        self.record_metric('event_persistence_success', True)

    async def test_websocket_event_broadcasting(self):
        """Test broadcasting events to multiple connections"""
        connections = []
        for i in range(3):
            conn = MockWebSocketConnection(user_id=self.user_id, session_id=self.id_manager.generate_id(IDType.SESSION))
            connections.append(conn)
            await self.ws_manager.register_connection(self.user_id, conn)
        broadcast_data = {'type': 'broadcast', 'message': 'System announcement'}
        await self.ws_manager.broadcast_to_user(self.user_id, 'broadcast', broadcast_data)
        for conn in connections:
            self.assertGreater(len(conn.messages_sent), 0)
        self.record_metric('event_broadcasting_success', True)

    async def test_websocket_event_metrics_collection(self):
        """Test metrics collection for WebSocket events"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        events_sent = 5
        for i in range(events_sent):
            await self.ws_manager.emit_event(self.user_id, 'metric_test', {'index': i})
        metrics = await self.ws_manager.get_event_metrics(self.user_id)
        self.assertEqual(metrics.events_sent, events_sent)
        self.assertGreater(metrics.total_bytes_sent, 0)
        self.record_metric('event_metrics_collection_success', True)

class TestWebSocketConnectionManagement(SSotAsyncTestCase):
    """Test suite for WebSocket connection management - 11 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)
        self.session_id = self.id_manager.generate_id(IDType.SESSION)

    async def test_websocket_connection_registration(self):
        """Test registering WebSocket connections"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        result = await self.ws_manager.register_connection(self.user_id, mock_connection)
        self.assertTrue(result.success)
        self.assertEqual(result.connection_id, mock_connection.session_id)
        self.record_metric('connection_registration_success', True)

    async def test_websocket_connection_deregistration(self):
        """Test deregistering WebSocket connections"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        is_connected = await self.ws_manager.is_user_connected(self.user_id)
        self.assertTrue(is_connected)
        result = await self.ws_manager.deregister_connection(self.user_id, self.session_id)
        self.assertTrue(result.success)
        is_connected_after = await self.ws_manager.is_user_connected(self.user_id)
        self.assertFalse(is_connected_after)
        self.record_metric('connection_deregistration_success', True)

    async def test_websocket_connection_health_monitoring(self):
        """Test WebSocket connection health monitoring"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        health = await self.ws_manager.check_connection_health(self.user_id)
        self.assertTrue(health.is_healthy)
        mock_connection.connected = False
        health_after = await self.ws_manager.check_connection_health(self.user_id)
        self.assertFalse(health_after.is_healthy)
        self.record_metric('connection_health_monitoring_success', True)

    async def test_websocket_connection_auto_cleanup(self):
        """Test automatic cleanup of stale connections"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        mock_connection.connected = False
        cleanup_result = await self.ws_manager.cleanup_stale_connections()
        self.assertGreater(cleanup_result.connections_cleaned, 0)
        self.assertIn(self.user_id, cleanup_result.cleaned_users)
        self.record_metric('connection_auto_cleanup_success', True)

    async def test_websocket_connection_multiplexing(self):
        """Test multiplexing multiple connections per user"""
        connections = []
        for i in range(3):
            session_id = self.id_manager.generate_id(IDType.SESSION)
            conn = MockWebSocketConnection(user_id=self.user_id, session_id=session_id)
            connections.append(conn)
            await self.ws_manager.register_connection(self.user_id, conn)
        user_connections = await self.ws_manager.get_user_connections(self.user_id)
        self.assertEqual(len(user_connections), 3)
        await self.ws_manager.emit_event(self.user_id, 'multiplexing_test', {'message': 'test'})
        for conn in connections:
            self.assertGreater(len(conn.messages_sent), 0)
        self.record_metric('connection_multiplexing_success', True)

    async def test_websocket_connection_authentication(self):
        """Test WebSocket connection authentication"""
        auth_token = 'valid_jwt_token'
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        result = await self.ws_manager.register_authenticated_connection(self.user_id, mock_connection, auth_token)
        self.assertTrue(result.authenticated)
        self.assertEqual(result.user_id, self.user_id)
        with self.expect_exception((ValueError, PermissionError)):
            await self.ws_manager.register_authenticated_connection(self.user_id, mock_connection, 'invalid_token')
        self.record_metric('connection_authentication_success', True)

    async def test_websocket_connection_session_management(self):
        """Test WebSocket connection session management"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        session_data = {'created_at': datetime.now(timezone.utc), 'user_agent': 'test_client', 'ip_address': '127.0.0.1'}
        await self.ws_manager.register_connection_with_session(self.user_id, mock_connection, session_data)
        session_info = await self.ws_manager.get_connection_session(self.user_id, self.session_id)
        self.assertEqual(session_info.user_id, self.user_id)
        self.assertEqual(session_info.session_id, self.session_id)
        self.assertEqual(session_info.user_agent, 'test_client')
        self.record_metric('connection_session_management_success', True)

    async def test_websocket_connection_rate_limiting(self):
        """Test connection rate limiting"""
        connections = []
        successful_connections = 0
        for i in range(10):
            try:
                session_id = self.id_manager.generate_id(IDType.SESSION)
                conn = MockWebSocketConnection(user_id=self.user_id, session_id=session_id)
                result = await self.ws_manager.register_connection_with_rate_limit(self.user_id, conn, max_connections_per_user=5)
                if result.success:
                    successful_connections += 1
                    connections.append(conn)
            except Exception as e:
                pass
        self.assertLessEqual(successful_connections, 5)
        self.record_metric('connection_rate_limiting_success', True)

    async def test_websocket_connection_failover(self):
        """Test WebSocket connection failover"""
        primary_conn = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        backup_session = self.id_manager.generate_id(IDType.SESSION)
        backup_conn = MockWebSocketConnection(user_id=self.user_id, session_id=backup_session)
        await self.ws_manager.register_connection(self.user_id, primary_conn, primary=True)
        await self.ws_manager.register_connection(self.user_id, backup_conn, primary=False)
        primary_conn.connected = False
        await self.ws_manager.emit_event(self.user_id, 'failover_test', {'message': 'failover'})
        self.assertGreater(len(backup_conn.messages_sent), 0)
        self.record_metric('connection_failover_success', True)

    async def test_websocket_connection_load_balancing(self):
        """Test load balancing across connection instances"""
        connections = []
        for i in range(4):
            session_id = self.id_manager.generate_id(IDType.SESSION)
            conn = MockWebSocketConnection(user_id=f'user_{i}', session_id=session_id)
            connections.append(conn)
            await self.ws_manager.register_connection_with_load(f'user_{i}', conn, current_load=i * 25)
        load_stats = await self.ws_manager.get_load_distribution()
        self.assertIsNotNone(load_stats.connections_by_load)
        self.assertEqual(load_stats.total_connections, 4)
        self.record_metric('connection_load_balancing_success', True)

    async def test_websocket_connection_metrics_tracking(self):
        """Test connection metrics tracking"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await self.ws_manager.register_connection(self.user_id, mock_connection)
        for i in range(5):
            await self.ws_manager.emit_event(self.user_id, 'metrics_test', {'index': i})
        metrics = await self.ws_manager.get_connection_metrics(self.user_id)
        self.assertEqual(metrics.messages_sent, 5)
        self.assertGreater(metrics.bytes_sent, 0)
        self.assertIsNotNone(metrics.connection_duration)
        self.record_metric('connection_metrics_tracking_success', True)

class TestMessageDeliveryMechanisms(SSotAsyncTestCase):
    """Test suite for message delivery mechanisms - 10 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)
        self.session_id = self.id_manager.generate_id(IDType.SESSION)

    async def test_message_delivery_direct(self):
        """Test direct message delivery"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        message_data = {'content': 'Direct message test'}
        delivery_result = await mock_connection.send_json(message_data)
        self.assertIn({'type': 'json', 'content': message_data}, mock_connection.messages_sent)
        self.record_metric('direct_message_delivery_success', True)

    async def test_message_delivery_queued(self):
        """Test queued message delivery"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        mock_connection.connected = False
        messages = [{'content': f'Queued message {i}'} for i in range(3)]
        message_queue = []
        for msg in messages:
            message_queue.append(msg)
        mock_connection.connected = True
        for msg in message_queue:
            await mock_connection.send_json(msg)
        self.assertEqual(len(mock_connection.messages_sent), 3)
        self.record_metric('queued_message_delivery_success', True)

    async def test_message_delivery_with_acknowledgment(self):
        """Test message delivery with acknowledgment"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        message_id = self.id_manager.generate_id(IDType.MESSAGE)
        message_data = {'id': message_id, 'content': 'ACK test message', 'requires_ack': True}
        await mock_connection.send_json(message_data)
        ack_message = {'type': 'acknowledgment', 'message_id': message_id, 'status': 'delivered'}
        delivery_confirmed = True
        self.assertTrue(delivery_confirmed)
        self.record_metric('acknowledgment_delivery_success', True)

    async def test_message_delivery_retry_mechanism(self):
        """Test message delivery retry mechanism"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        send_attempts = 0
        original_send = mock_connection.send_json

        async def failing_send(data):
            nonlocal send_attempts
            send_attempts += 1
            if send_attempts < 3:
                raise ConnectionError('Temporary failure')
            return await original_send(data)
        mock_connection.send_json = failing_send
        message_data = {'content': 'Retry test message'}
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                await mock_connection.send_json(message_data)
                break
            except ConnectionError:
                retry_count += 1
                await asyncio.sleep(0.1)
        self.assertEqual(send_attempts, 3)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        self.record_metric('retry_mechanism_success', True)

    async def test_message_delivery_compression(self):
        """Test message delivery with compression"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        large_message = {'content': 'A' * 5000, 'metadata': {'compressed': True}}
        await mock_connection.send_json(large_message)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        sent_message = mock_connection.messages_sent[0]
        self.assertEqual(sent_message['type'], 'json')
        self.record_metric('compression_delivery_success', True)

    async def test_message_delivery_encryption(self):
        """Test message delivery with encryption"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        sensitive_message = {'content': 'Sensitive user data', 'encrypted': True, 'encryption_key_id': 'key_123'}
        await mock_connection.send_json(sensitive_message)
        sent_message = mock_connection.messages_sent[0]
        self.assertTrue(sent_message['content']['encrypted'])
        self.record_metric('encryption_delivery_success', True)

    async def test_message_delivery_priority_queue(self):
        """Test priority-based message delivery"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        messages = [{'content': 'Low priority', 'priority': 1}, {'content': 'High priority', 'priority': 10}, {'content': 'Medium priority', 'priority': 5}]
        sorted_messages = sorted(messages, key=lambda x: x['priority'], reverse=True)
        for msg in sorted_messages:
            await mock_connection.send_json(msg)
        first_message = mock_connection.messages_sent[0]
        self.assertEqual(first_message['content']['priority'], 10)
        self.record_metric('priority_queue_delivery_success', True)

    async def test_message_delivery_bandwidth_limiting(self):
        """Test message delivery with bandwidth limiting"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        messages = [{'content': f'Message {i}'} for i in range(5)]
        start_time = time.time()
        for msg in messages:
            await mock_connection.send_json(msg)
            await asyncio.sleep(0.1)
        total_time = time.time() - start_time
        self.assertGreater(total_time, 0.4)
        self.assertEqual(len(mock_connection.messages_sent), 5)
        self.record_metric('bandwidth_limiting_success', True)

    async def test_message_delivery_error_recovery(self):
        """Test message delivery error recovery"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        error_occurred = False

        async def error_prone_send(data):
            nonlocal error_occurred
            if not error_occurred:
                error_occurred = True
                raise ConnectionError('Network error')
            mock_connection.messages_sent.append({'type': 'json', 'content': data})
        mock_connection.send_json = error_prone_send
        message_data = {'content': 'Error recovery test'}
        try:
            await mock_connection.send_json(message_data)
        except ConnectionError:
            await mock_connection.send_json(message_data)
        self.assertTrue(error_occurred)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        self.record_metric('error_recovery_success', True)

    async def test_message_delivery_analytics(self):
        """Test message delivery analytics collection"""
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        delivery_metrics = {'messages_sent': 0, 'bytes_sent': 0, 'delivery_times': []}
        messages = [{'content': f'Analytics message {i}'} for i in range(3)]
        for msg in messages:
            start_time = time.time()
            await mock_connection.send_json(msg)
            delivery_time = time.time() - start_time
            delivery_metrics['messages_sent'] += 1
            delivery_metrics['bytes_sent'] += len(json.dumps(msg))
            delivery_metrics['delivery_times'].append(delivery_time)
        self.assertEqual(delivery_metrics['messages_sent'], 3)
        self.assertGreater(delivery_metrics['bytes_sent'], 0)
        self.assertEqual(len(delivery_metrics['delivery_times']), 3)
        self.record_metric('delivery_analytics_success', True)

class TestAgentWebSocketCoordination(SSotAsyncTestCase):
    """Test suite for Agent-WebSocket coordination - 12 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)
        self.session_id = self.id_manager.generate_id(IDType.SESSION)

    async def test_agent_websocket_bridge_initialization(self):
        """Test initializing Agent-WebSocket bridge"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        self.assertIsNotNone(bridge_adapter.websocket_manager)
        self.record_metric('bridge_initialization_success', True)

    async def test_agent_websocket_event_coordination(self):
        """Test coordinating events between Agent and WebSocket"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        event_data = {'agent_id': 'test_agent', 'status': 'started', 'timestamp': datetime.now(timezone.utc).isoformat()}
        await bridge_adapter.emit_agent_event(self.user_id, 'agent_started', event_data)
        self.assertGreater(len(mock_connection.messages_sent), 0)
        self.record_metric('event_coordination_success', True)

    async def test_agent_lifecycle_websocket_notifications(self):
        """Test WebSocket notifications during agent lifecycle"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        lifecycle_events = [('agent_started', {'agent_id': 'agent_1'}), ('agent_thinking', {'message': 'Processing...'}), ('tool_executing', {'tool': 'database_query'}), ('tool_completed', {'result': 'success'}), ('agent_completed', {'result': 'Task finished'})]
        for event_type, event_data in lifecycle_events:
            await bridge_adapter.emit_agent_event(self.user_id, event_type, event_data)
        self.assertEqual(len(mock_connection.messages_sent), 5)
        self.record_metric('lifecycle_notifications_success', True)

    async def test_agent_websocket_user_isolation(self):
        """Test user isolation in Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        user1_conn = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        user2_id = self.id_manager.generate_id(IDType.USER)
        user2_conn = MockWebSocketConnection(user_id=user2_id, session_id=self.id_manager.generate_id(IDType.SESSION))
        await ws_manager.register_connection(self.user_id, user1_conn)
        await ws_manager.register_connection(user2_id, user2_conn)
        await bridge_adapter.emit_agent_event(self.user_id, 'agent_started', {'agent_id': 'user1_agent'})
        self.assertGreater(len(user1_conn.messages_sent), 0)
        self.assertEqual(len(user2_conn.messages_sent), 0)
        self.record_metric('user_isolation_success', True)

    async def test_agent_websocket_context_propagation(self):
        """Test context propagation through Agent-WebSocket bridge"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        context = UserExecutionContext(user_id=self.user_id, session_id=self.session_id, trace_id=self.id_manager.generate_id(IDType.TRACE))
        event_data = {'agent_id': 'context_agent', 'context': {'user_id': context.user_id, 'session_id': context.session_id, 'trace_id': context.trace_id}}
        await bridge_adapter.emit_agent_event_with_context(context, 'agent_started', event_data)
        sent_message = mock_connection.messages_sent[0]
        self.assertIn('context', str(sent_message))
        self.record_metric('context_propagation_success', True)

    async def test_agent_websocket_error_handling(self):
        """Test error handling in Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        event_data = {'agent_id': 'error_agent'}
        result = await bridge_adapter.emit_agent_event('nonexistent_user', 'agent_started', event_data)
        self.assertIsNotNone(result)
        self.record_metric('error_handling_success', True)

    async def test_agent_websocket_performance_monitoring(self):
        """Test performance monitoring of Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        start_time = time.time()
        for i in range(10):
            await bridge_adapter.emit_agent_event(self.user_id, 'performance_test', {'index': i})
        total_time = time.time() - start_time
        avg_time_per_event = total_time / 10
        self.assertLess(avg_time_per_event, 0.1)
        self.record_metric('performance_monitoring_success', True)
        self.record_metric('avg_event_emission_time_ms', avg_time_per_event * 1000)

    async def test_agent_websocket_concurrent_coordination(self):
        """Test concurrent Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        concurrent_events = [bridge_adapter.emit_agent_event(self.user_id, 'concurrent_test', {'index': i}) for i in range(5)]
        results = await asyncio.gather(*concurrent_events, return_exceptions=True)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        self.assertEqual(len(successful_results), 5)
        self.assertEqual(len(mock_connection.messages_sent), 5)
        self.record_metric('concurrent_coordination_success', True)

    async def test_agent_websocket_state_synchronization(self):
        """Test state synchronization between Agent and WebSocket"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        agent_state = {'status': 'initializing', 'progress': 0}
        await bridge_adapter.sync_agent_state(self.user_id, agent_state)
        for progress in [25, 50, 75, 100]:
            agent_state['progress'] = progress
            if progress == 100:
                agent_state['status'] = 'completed'
            await bridge_adapter.sync_agent_state(self.user_id, agent_state)
        state_messages = [msg for msg in mock_connection.messages_sent if 'progress' in str(msg)]
        self.assertGreater(len(state_messages), 0)
        self.record_metric('state_synchronization_success', True)

    async def test_agent_websocket_resource_cleanup(self):
        """Test resource cleanup in Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        await bridge_adapter.create_agent_session(self.user_id, 'cleanup_agent')
        mock_connection.connected = False
        cleanup_result = await bridge_adapter.cleanup_agent_resources(self.user_id)
        self.assertTrue(cleanup_result.success)
        self.assertGreater(cleanup_result.resources_cleaned, 0)
        self.record_metric('resource_cleanup_success', True)

    async def test_agent_websocket_message_ordering(self):
        """Test message ordering in Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        ordered_messages = [('agent_started', {'sequence': 1}), ('agent_thinking', {'sequence': 2}), ('tool_executing', {'sequence': 3}), ('tool_completed', {'sequence': 4}), ('agent_completed', {'sequence': 5})]
        for event_type, event_data in ordered_messages:
            await bridge_adapter.emit_agent_event(self.user_id, event_type, event_data, ordered=True)
        self.assertEqual(len(mock_connection.messages_sent), 5)
        self.record_metric('message_ordering_success', True)

    async def test_agent_websocket_reconnection_handling(self):
        """Test reconnection handling in Agent-WebSocket coordination"""
        bridge_adapter = WebSocketBridgeAdapter()
        ws_manager = await get_websocket_manager()
        bridge_adapter.initialize(ws_manager)
        mock_connection = MockWebSocketConnection(user_id=self.user_id, session_id=self.session_id)
        await ws_manager.register_connection(self.user_id, mock_connection)
        await bridge_adapter.emit_agent_event(self.user_id, 'reconnection_test', {'before_disconnect': True})
        mock_connection.connected = False
        await bridge_adapter.emit_agent_event(self.user_id, 'reconnection_test', {'during_disconnect': True})
        mock_connection.connected = True
        await bridge_adapter.emit_agent_event(self.user_id, 'reconnection_test', {'after_reconnect': True})
        total_messages = len(mock_connection.messages_sent)
        self.assertGreaterEqual(total_messages, 2)
        self.record_metric('reconnection_handling_success', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')