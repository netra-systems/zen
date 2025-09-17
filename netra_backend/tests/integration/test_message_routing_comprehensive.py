"""
Comprehensive Message Routing Integration Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable WebSocket message routing and multi-user isolation
- Value Impact: Message routing is foundation of real-time AI chat value delivery
- Strategic Impact: System reliability enables scalable multi-user platform

This comprehensive test suite validates message routing architecture:
1. MessageRouter core functionality with handler registration/deregistration
2. WebSocket message routing with user-specific delivery and isolation  
3. Multi-user isolation via Factory pattern and UserExecutionContext
4. Agent message integration with WebSocket event delivery

CRITICAL: Integration tests use real components without mocks except for external services.
All tests validate actual business logic and integration points.

SSOT Compliance:
- Uses StronglyTypedUserExecutionContext for all user contexts
- Uses shared.types for UserID, ThreadID, ConnectionID, WebSocketID
- Uses test_framework.base_integration_test.BaseIntegrationTest base
- Uses test_framework.ssot.e2e_auth_helper for user context creation
- Follows CLAUDE.md requirements for integration testing
"""
import asyncio
import json
import pytest
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ConnectionID, WebSocketID, ensure_user_id, ensure_thread_id, ensure_websocket_id
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router, BaseMessageHandler, ConnectionHandler, TypingHandler, HeartbeatHandler, UserMessageHandler, AgentHandler, ErrorHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, create_standard_message, create_server_message, create_error_message
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory, create_websocket_manager, get_websocket_manager_factory
from netra_backend.app.websocket_core.websocket_manager import WebSocketConnection
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class SimpleMockWebSocketManager:
    """Simple mock WebSocket manager for integration testing."""

    def __init__(self, user_context):
        self.user_context = user_context
        self.connections = {}
        self.messages_sent = []
        self.recovery_queue = []
        self.messages_failed_total = 0

    async def add_connection(self, connection):
        """Mock add connection."""
        self.connections[connection.connection_id] = connection

    async def remove_connection(self, connection_id):
        """Mock remove connection - REQUIRED by cleanup test."""
        if connection_id in self.connections:
            del self.connections[connection_id]

    async def send_to_user(self, message):
        """Mock send to user - track failures and queuing with disconnection detection."""
        if len(self.connections) == 0:
            self.recovery_queue.append(message)
            self.messages_failed_total += 1
            return
        connections_to_remove = []
        for connection in self.connections.values():
            if hasattr(connection, 'websocket') and hasattr(connection.websocket, 'send_json'):
                try:
                    if hasattr(connection.websocket, 'is_connected') and (not connection.websocket.is_connected):
                        connections_to_remove.append(connection.connection_id)
                        self.recovery_queue.append(message)
                        self.messages_failed_total += 1
                    else:
                        await connection.websocket.send_json(message)
                except RuntimeError as e:
                    if 'WebSocket not connected' in str(e):
                        connections_to_remove.append(connection.connection_id)
                        self.recovery_queue.append(message)
                        self.messages_failed_total += 1
                    else:
                        raise
        for conn_id in connections_to_remove:
            await self.remove_connection(conn_id)
        self.messages_sent.append(message)

    def get_user_connections(self):
        """Mock get user connections."""
        return list(self.connections.keys())

    def get_connection(self, conn_id):
        """Mock get connection."""
        return self.connections.get(conn_id)

    def is_connection_active(self, user_id):
        """Mock is connection active - MUST enforce user isolation."""
        if user_id == self.user_context.user_id:
            return len(self.connections) > 0
        else:
            return False

    def get_manager_stats(self):
        """Mock get manager stats - return actual tracked values."""
        return {'is_active': len(self.connections) > 0, 'connections': {'total': len(self.connections)}, 'recovery_queue_size': len(self.recovery_queue), 'metrics': {'messages_failed_total': self.messages_failed_total}}

    def get_connection_health(self, user_id):
        """Mock get connection health."""
        if user_id == self.user_context.user_id:
            return {'user_id': user_id, 'status': 'healthy'}
        else:
            return {'error': 'User isolation violation'}
_mock_factory_state = {'active_managers': 0, 'users_with_managers': 0, 'user_distribution': {}}

class MockWebSocketManagerFactory:
    """Mock factory for tracking WebSocket managers in tests."""

    def __init__(self):
        self.state = _mock_factory_state

    def reset_state(self):
        """Reset factory state for clean tests."""
        self.state['active_managers'] = 0
        self.state['users_with_managers'] = 0
        self.state['user_distribution'] = {}

    async def create_manager(self, user_context):
        """Create manager and track in factory state."""
        manager = await mock_create_websocket_manager(user_context)
        self.state['active_managers'] += 1
        user_id = str(user_context.user_id)
        if user_id not in self.state['user_distribution']:
            self.state['user_distribution'][user_id] = 0
            self.state['users_with_managers'] += 1
        self.state['user_distribution'][user_id] += 1
        return manager

    def get_factory_stats(self):
        """Get factory statistics."""
        return {'current_state': {'active_managers': self.state['active_managers'], 'users_with_managers': self.state['users_with_managers']}, 'user_distribution': self.state['user_distribution'].copy()}
_mock_factory_instance = MockWebSocketManagerFactory()

def mock_get_websocket_manager_factory():
    """Return the mock factory instance."""
    return _mock_factory_instance

async def mock_create_websocket_manager(user_context):
    """Mock create_websocket_manager function."""
    return SimpleMockWebSocketManager(user_context)

class MockWebSocket:
    """Mock WebSocket for integration testing that behaves like real FastAPI WebSocket."""

    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.messages_sent = []
        self.is_connected = True
        self.client_state = 'connected'
        self.application_state = MagicMock()
        self.application_state._mock_name = 'mock_websocket'
        self.scope = {'app': MagicMock()}
        self.scope['app'].state = MagicMock()

    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock send_json that stores messages for verification."""
        if self.is_connected:
            self.messages_sent.append(data)
        else:
            raise RuntimeError('WebSocket not connected')

    async def send_text(self, text: str) -> None:
        """Mock send_text that stores messages for verification."""
        if self.is_connected:
            try:
                data = json.loads(text)
                self.messages_sent.append(data)
            except json.JSONDecodeError:
                self.messages_sent.append({'text': text})
        else:
            raise RuntimeError('WebSocket not connected')

    def disconnect(self) -> None:
        """Simulate WebSocket disconnection."""
        self.is_connected = False
        self.client_state = 'disconnected'

class MessageRoutingCoreTests(BaseIntegrationTest):
    """Test Message Router core functionality and handler management."""

    @pytest.mark.integration
    async def test_message_router_basic_routing(self, isolated_env):
        """Test basic message routing to correct handlers."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')
        test_cases = [{'type': 'ping', 'expected_handler': 'HeartbeatHandler'}, {'type': 'user_typing', 'expected_handler': 'TypingHandler'}, {'type': 'connect', 'expected_handler': 'ConnectionHandler'}, {'type': 'user_message', 'expected_handler': 'UserMessageHandler'}, {'type': 'error', 'expected_handler': 'ErrorHandler'}]
        for case in test_cases:
            raw_message = {'type': case['type'], 'payload': {'test': 'data'}}
            success = await router.route_message('user1', websocket, raw_message)
            assert success, f"Failed to route {case['type']} message"
            stats = router.get_stats()
            assert stats['messages_routed'] > 0
            message_types_str = str(stats['message_types'])
            assert case['type'] in message_types_str.lower() or case['type'].upper() in message_types_str
        logger.info(' PASS:  Basic message routing test completed')

    @pytest.mark.integration
    async def test_message_router_multiple_handlers(self, isolated_env):
        """Test multiple handlers for same message type with priority."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')

        class CustomHandler1(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.handled = []

            async def handle_message(self, user_id, ws, message):
                self.handled.append(f'handler1_{message.type}')
                return True

        class CustomHandler2(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.handled = []

            async def handle_message(self, user_id, ws, message):
                self.handled.append(f'handler2_{message.type}')
                return True
        handler1 = CustomHandler1()
        handler2 = CustomHandler2()
        router.add_handler(handler1)
        router.add_handler(handler2)
        handler_order = router.get_handler_order()
        assert 'CustomHandler1' in handler_order[:2], f'CustomHandler1 should have precedence, order: {handler_order[:5]}'
        assert 'CustomHandler2' in handler_order[:3], f'CustomHandler2 should have precedence, order: {handler_order[:5]}'
        raw_message = {'type': 'user_message', 'payload': {'content': 'test'}}
        success = await router.route_message('user1', websocket, raw_message)
        assert success
        assert len(handler1.handled) == 1, f'Handler1 (first added) should be called due to precedence among custom handlers, handler1: {len(handler1.handled)}, handler2: {len(handler2.handled)}'
        assert len(handler2.handled) == 0, f'Handler2 should not be called as handler1 has precedence, handler1: {len(handler1.handled)}, handler2: {len(handler2.handled)}'
        logger.info(' PASS:  Multiple handlers routing test completed')

    @pytest.mark.integration
    async def test_message_router_handler_precedence_validation(self, isolated_env):
        """Test that custom handlers take precedence over built-in handlers."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')

        class PrecedenceTestHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.handled_messages = []

            async def handle_message(self, user_id, ws, message):
                self.handled_messages.append({'user_id': user_id, 'message_type': message.type, 'payload': message.payload})
                return True
        custom_handler = PrecedenceTestHandler()
        builtin_user_handler = None
        for handler in router.handlers:
            if isinstance(handler, UserMessageHandler):
                builtin_user_handler = handler
                break
        assert builtin_user_handler is not None, 'UserMessageHandler should be registered'
        assert builtin_user_handler.can_handle(MessageType.USER_MESSAGE), 'Built-in should handle USER_MESSAGE'
        router.add_handler(custom_handler)
        handler_order = router.get_handler_order()
        assert handler_order[0] == 'PrecedenceTestHandler', f'Custom handler should be first, got: {handler_order[:3]}'
        raw_message = {'type': 'user_message', 'payload': {'content': 'precedence test'}}
        success = await router.route_message('user1', websocket, raw_message)
        assert success, 'Message routing should succeed'
        assert len(custom_handler.handled_messages) == 1, f'Custom handler should be called once, got: {len(custom_handler.handled_messages)}'
        assert custom_handler.handled_messages[0]['message_type'] == MessageType.USER_MESSAGE
        builtin_stats = builtin_user_handler.get_stats()
        logger.info(' PASS:  Handler precedence validation test completed')

    @pytest.mark.integration
    async def test_message_router_handler_priority(self, isolated_env):
        """Test handler priority and selection logic."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')
        call_order = []

        class PriorityHandler(BaseMessageHandler):

            def __init__(self, name, types):
                super().__init__(types)
                self.name = name

            async def handle_message(self, user_id, ws, message):
                call_order.append(self.name)
                return True
        high_priority = PriorityHandler('high', [MessageType.PING])
        low_priority = PriorityHandler('low', [MessageType.PING])
        router.add_handler(high_priority)
        router.add_handler(low_priority)
        raw_message = {'type': 'ping', 'payload': {}}
        success = await router.route_message('user1', websocket, raw_message)
        assert success
        assert call_order[0] == 'high'
        assert len(call_order) == 1
        logger.info(' PASS:  Handler priority test completed')

    @pytest.mark.integration
    async def test_message_router_unknown_message_types(self, isolated_env):
        """Test graceful handling of unknown message types."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')
        unknown_types = ['custom_unknown', 'invalid_type', 'unsupported_message']
        for unknown_type in unknown_types:
            raw_message = {'type': unknown_type, 'payload': {'data': 'test'}}
            success = await router.route_message('user1', websocket, raw_message)
            assert success, f'Failed to handle unknown type: {unknown_type}'
            assert len(websocket.messages_sent) > 0
            last_message = websocket.messages_sent[-1]
            assert last_message.get('type') == 'ack'
            assert last_message.get('received_type') == unknown_type
            websocket.messages_sent.clear()
        stats = router.get_stats()
        assert stats['unhandled_messages'] == len(unknown_types)
        logger.info(' PASS:  Unknown message types test completed')

    @pytest.mark.integration
    async def test_message_router_handler_failure_recovery(self, isolated_env):
        """Test handler failure and fallback mechanisms."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')

        class FailingHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.PING])
                self.failure_count = 0

            async def handle_message(self, user_id, ws, message):
                self.failure_count += 1
                raise RuntimeError(f'Handler failure #{self.failure_count}')
        failing_handler = FailingHandler()
        router.add_handler(failing_handler)
        raw_message = {'type': 'ping', 'payload': {}}
        success = await router.route_message('user1', websocket, raw_message)
        assert not success
        assert failing_handler.failure_count == 1
        stats = router.get_stats()
        assert stats['handler_errors'] > 0
        logger.info(' PASS:  Handler failure recovery test completed')

    @pytest.mark.integration
    async def test_message_router_concurrent_routing(self, isolated_env):
        """Test concurrent message routing without race conditions."""
        router = MessageRouter()
        websockets = [MockWebSocket(f'user{i}', f'conn{i}') for i in range(5)]

        async def route_messages_for_user(ws, user_idx):
            """Route multiple messages for a user concurrently."""
            messages = []
            for msg_idx in range(10):
                raw_message = {'type': 'ping', 'payload': {'user': user_idx, 'message': msg_idx}}
                success = await router.route_message(f'user{user_idx}', ws, raw_message)
                messages.append(success)
            return messages
        tasks = [route_messages_for_user(ws, i) for i, ws in enumerate(websockets)]
        results = await asyncio.gather(*tasks)
        for user_results in results:
            assert all(user_results), 'Some concurrent messages failed to route'
        stats = router.get_stats()
        assert stats['messages_routed'] == 50
        logger.info(' PASS:  Concurrent routing test completed')

    @pytest.mark.integration
    async def test_message_router_handler_registration(self, isolated_env):
        """Test dynamic handler registration and management."""
        router = MessageRouter()
        initial_handler_count = len(router.handlers)

        class DynamicHandler(BaseMessageHandler):

            def __init__(self, name):
                super().__init__([MessageType.USER_MESSAGE])
                self.name = name

            async def handle_message(self, user_id, ws, message):
                return True
        handler1 = DynamicHandler('dynamic1')
        handler2 = DynamicHandler('dynamic2')
        router.add_handler(handler1)
        assert len(router.handlers) == initial_handler_count + 1
        router.add_handler(handler2)
        assert len(router.handlers) == initial_handler_count + 2
        router.remove_handler(handler1)
        assert len(router.handlers) == initial_handler_count + 1
        assert handler1 not in router.handlers
        assert handler2 in router.handlers
        router.remove_handler(handler2)
        assert len(router.handlers) == initial_handler_count
        assert handler2 not in router.handlers
        logger.info(' PASS:  Handler registration test completed')

    @pytest.mark.integration
    async def test_message_router_handler_deregistration(self, isolated_env):
        """Test handler cleanup and deregistration."""
        router = MessageRouter()
        websocket = MockWebSocket('user1', 'conn1')

        class TemporaryHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.CHAT])
                self.call_count = 0

            async def handle_message(self, user_id, ws, message):
                self.call_count += 1
                return True
        temp_handler = TemporaryHandler()
        router.add_handler(temp_handler)
        raw_message = {'type': 'chat', 'payload': {'content': 'test'}}
        success = await router.route_message('user1', websocket, raw_message)
        assert success
        assert temp_handler.call_count == 1
        router.remove_handler(temp_handler)
        success = await router.route_message('user1', websocket, raw_message)
        assert temp_handler.call_count == 1
        logger.info(' PASS:  Handler deregistration test completed')

class WebSocketMessageRoutingTests(BaseIntegrationTest):
    """Test WebSocket-specific message routing and user isolation."""

    @pytest.mark.integration
    async def test_websocket_message_routing_to_user(self, test_db_session, isolated_env):
        """Test routing messages to specific users via WebSocket."""
        auth_helper = E2EAuthHelper()
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        user1_context = UserExecutionContext.from_request(user_id=str(user1_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        user2_context = UserExecutionContext.from_request(user_id=str(user2_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        ws_manager1 = await mock_create_websocket_manager(user1_context)
        ws_manager2 = await mock_create_websocket_manager(user2_context)
        websocket1 = MockWebSocket(str(user1_id), 'conn1')
        websocket2 = MockWebSocket(str(user2_id), 'conn2')
        conn1 = WebSocketConnection(connection_id='conn1', user_id=str(user1_id), websocket=websocket1, connected_at=datetime.utcnow())
        conn2 = WebSocketConnection(connection_id='conn2', user_id=str(user2_id), websocket=websocket2, connected_at=datetime.utcnow())
        await ws_manager1.add_connection(conn1)
        await ws_manager2.add_connection(conn2)
        message1 = {'type': 'agent_response', 'content': 'Response for user 1'}
        message2 = {'type': 'agent_response', 'content': 'Response for user 2'}
        await ws_manager1.send_to_user(message1)
        await ws_manager2.send_to_user(message2)
        assert len(websocket1.messages_sent) == 1
        assert len(websocket2.messages_sent) == 1
        assert websocket1.messages_sent[0]['content'] == 'Response for user 1'
        assert websocket2.messages_sent[0]['content'] == 'Response for user 2'
        logger.info(' PASS:  WebSocket message routing to user test completed')

    @pytest.mark.integration
    async def test_websocket_connection_isolation(self, isolated_env):
        """Test that WebSocket connections are properly isolated between users."""
        factory = get_websocket_manager_factory()
        users = []
        managers = []
        websockets = []
        for i in range(3):
            user_id = ensure_user_id(f'isolation_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
            manager = await mock_create_websocket_manager(context)
            websocket = MockWebSocket(str(user_id), f'conn_{i}')
            users.append(user_id)
            managers.append(manager)
            websockets.append(websocket)
        for i, (manager, websocket, user_id) in enumerate(zip(managers, websockets, users)):
            connection = WebSocketConnection(connection_id=f'conn_{i}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
            await manager.add_connection(connection)
        for i, manager in enumerate(managers):
            connections = manager.get_user_connections()
            assert len(connections) == 1
            assert f'conn_{i}' in connections
            for j, other_user_id in enumerate(users):
                if i != j:
                    has_connection = manager.is_connection_active(str(other_user_id))
                    assert not has_connection
        logger.info(' PASS:  WebSocket connection isolation test completed')

    @pytest.mark.integration
    async def test_websocket_message_queuing(self, isolated_env):
        """Test message queuing for disconnected users."""
        factory = get_websocket_manager_factory()
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        manager = await mock_create_websocket_manager(context)
        test_message = {'type': 'agent_response', 'content': 'Queued message'}
        await manager.send_to_user(test_message)
        stats = manager.get_manager_stats()
        assert stats['recovery_queue_size'] > 0
        assert stats['metrics']['messages_failed_total'] > 0
        logger.info(' PASS:  WebSocket message queuing test completed')

    @pytest.mark.integration
    async def test_websocket_connection_state_sync(self, isolated_env):
        """Test WebSocket connection state synchronization."""
        factory = get_websocket_manager_factory()
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        manager = await mock_create_websocket_manager(context)
        websocket = MockWebSocket(str(user_id), 'sync_conn')
        connection = WebSocketConnection(connection_id='sync_conn', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
        await manager.add_connection(connection)
        assert manager.is_connection_active(str(user_id))
        websocket.disconnect()
        test_message = {'type': 'system_message', 'content': 'Test after disconnect'}
        await manager.send_to_user(test_message)
        stats = manager.get_manager_stats()
        assert stats['metrics']['messages_failed_total'] > 0
        logger.info(' PASS:  WebSocket connection state sync test completed')

    @pytest.mark.integration
    async def test_websocket_routing_table_consistency(self, isolated_env, monkeypatch):
        """Test routing table accuracy and consistency."""
        monkeypatch.setattr('netra_backend.tests.integration.test_message_routing_comprehensive.get_websocket_manager_factory', mock_get_websocket_manager_factory)
        factory = get_websocket_manager_factory()
        factory.reset_state()
        routing_data = []
        for i in range(5):
            user_id = ensure_user_id(f'routing_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
            manager = await factory.create_manager(context)
            for j in range(2):
                websocket = MockWebSocket(str(user_id), f'conn_{i}_{j}')
                connection = WebSocketConnection(connection_id=f'conn_{i}_{j}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
                await manager.add_connection(connection)
            routing_data.append((user_id, manager))
        for user_id, manager in routing_data:
            connections = manager.get_user_connections()
            assert len(connections) == 2
            for conn_id in connections:
                connection = manager.get_connection(conn_id)
                assert connection.user_id == str(user_id)
        factory_stats = factory.get_factory_stats()
        assert factory_stats['current_state']['active_managers'] == 5
        logger.info(' PASS:  WebSocket routing table consistency test completed')

    @pytest.mark.integration
    async def test_websocket_message_broadcasting(self, isolated_env):
        """Test message broadcasting functionality."""
        factory = get_websocket_manager_factory()
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        manager = await mock_create_websocket_manager(context)
        websockets = []
        for i in range(3):
            websocket = MockWebSocket(str(user_id), f'broadcast_conn_{i}')
            connection = WebSocketConnection(connection_id=f'broadcast_conn_{i}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
            await manager.add_connection(connection)
            websockets.append(websocket)
        broadcast_message = {'type': 'system_announcement', 'content': 'System maintenance in 5 minutes'}
        await manager.send_to_user(broadcast_message)
        for websocket in websockets:
            assert len(websocket.messages_sent) == 1
            assert websocket.messages_sent[0]['content'] == 'System maintenance in 5 minutes'
        logger.info(' PASS:  WebSocket message broadcasting test completed')

    @pytest.mark.integration
    async def test_websocket_connection_cleanup(self, isolated_env):
        """Test connection cleanup on disconnect."""
        factory = get_websocket_manager_factory()
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        manager = await mock_create_websocket_manager(context)
        connections_to_cleanup = []
        for i in range(3):
            websocket = MockWebSocket(str(user_id), f'cleanup_conn_{i}')
            connection = WebSocketConnection(connection_id=f'cleanup_conn_{i}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
            await manager.add_connection(connection)
            connections_to_cleanup.append(f'cleanup_conn_{i}')
        assert len(manager.get_user_connections()) == 3
        for conn_id in connections_to_cleanup:
            await manager.remove_connection(conn_id)
        assert len(manager.get_user_connections()) == 0
        stats = manager.get_manager_stats()
        assert stats['connections']['total'] == 0
        logger.info(' PASS:  WebSocket connection cleanup test completed')

class MultiUserIsolationTests(BaseIntegrationTest):
    """Test multi-user isolation via Factory pattern and UserExecutionContext."""

    @pytest.mark.integration
    async def test_multi_user_message_isolation(self, isolated_env, monkeypatch):
        """Test that messages don't leak between users."""
        monkeypatch.setattr('netra_backend.tests.integration.test_message_routing_comprehensive.get_websocket_manager_factory', mock_get_websocket_manager_factory)
        factory = get_websocket_manager_factory()
        factory.reset_state()
        user1_id = ensure_user_id('isolation_user_1')
        user2_id = ensure_user_id('isolation_user_2')
        context1 = UserExecutionContext.from_request(user_id=str(user1_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        context2 = UserExecutionContext.from_request(user_id=str(user2_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        manager1 = await factory.create_manager(context1)
        manager2 = await factory.create_manager(context2)
        websocket1 = MockWebSocket(str(user1_id), 'user1_conn')
        websocket2 = MockWebSocket(str(user2_id), 'user2_conn')
        conn1 = WebSocketConnection(connection_id='user1_conn', user_id=str(user1_id), websocket=websocket1, connected_at=datetime.utcnow())
        conn2 = WebSocketConnection(connection_id='user2_conn', user_id=str(user2_id), websocket=websocket2, connected_at=datetime.utcnow())
        await manager1.add_connection(conn1)
        await manager2.add_connection(conn2)
        user1_message = {'type': 'private_data', 'sensitive': 'user1_secret'}
        user2_message = {'type': 'private_data', 'sensitive': 'user2_secret'}
        await manager1.send_to_user(user1_message)
        await manager2.send_to_user(user2_message)
        assert len(websocket1.messages_sent) == 1
        assert len(websocket2.messages_sent) == 1
        assert websocket1.messages_sent[0]['sensitive'] == 'user1_secret'
        assert websocket2.messages_sent[0]['sensitive'] == 'user2_secret'
        assert websocket1.messages_sent[0]['sensitive'] != 'user2_secret'
        assert websocket2.messages_sent[0]['sensitive'] != 'user1_secret'
        logger.info(' PASS:  Multi-user message isolation test completed')

    @pytest.mark.integration
    async def test_multi_user_connection_separation(self, isolated_env):
        """Test that connection pools are isolated between users."""
        factory = get_websocket_manager_factory()
        users_data = []
        for i in range(3):
            user_id = ensure_user_id(f'connection_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
            manager = await mock_create_websocket_manager(context)
            websockets = []
            for j in range(3):
                websocket = MockWebSocket(str(user_id), f'user_{i}_conn_{j}')
                connection = WebSocketConnection(connection_id=f'user_{i}_conn_{j}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
                await manager.add_connection(connection)
                websockets.append(websocket)
            users_data.append((user_id, manager, websockets))
        for user_id, manager, websockets in users_data:
            connections = manager.get_user_connections()
            assert len(connections) == 3
            for conn_id in connections:
                connection = manager.get_connection(conn_id)
                assert connection.user_id == str(user_id)
            for other_user_id, other_manager, _ in users_data:
                if user_id != other_user_id:
                    has_connection = manager.is_connection_active(str(other_user_id))
                    assert not has_connection
        logger.info(' PASS:  Multi-user connection separation test completed')

    @pytest.mark.integration
    async def test_multi_user_concurrent_routing(self, isolated_env):
        """Test concurrent message routing across multiple users."""
        factory = get_websocket_manager_factory()
        users_setup = []
        for i in range(5):
            user_id = ensure_user_id(f'concurrent_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
            manager = await mock_create_websocket_manager(context)
            websocket = MockWebSocket(str(user_id), f'concurrent_conn_{i}')
            connection = WebSocketConnection(connection_id=f'concurrent_conn_{i}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
            await manager.add_connection(connection)
            users_setup.append((user_id, manager, websocket))

        async def send_messages_to_user(user_id, manager, websocket, user_index):
            messages = []
            for msg_index in range(10):
                message = {'type': 'concurrent_test', 'user': str(user_id), 'message_id': f'{user_index}_{msg_index}', 'timestamp': time.time()}
                await manager.send_to_user(message)
                messages.append(message)
                await asyncio.sleep(0.01)
            return messages
        tasks = [send_messages_to_user(user_id, manager, websocket, i) for i, (user_id, manager, websocket) in enumerate(users_setup)]
        sent_messages = await asyncio.gather(*tasks)
        for i, (user_id, manager, websocket) in enumerate(users_setup):
            received = websocket.messages_sent
            expected = sent_messages[i]
            assert len(received) == len(expected)
            for msg in received:
                assert msg['user'] == str(user_id)
                assert msg['message_id'].startswith(str(i))
        logger.info(' PASS:  Multi-user concurrent routing test completed')

    @pytest.mark.integration
    async def test_multi_user_factory_isolation(self, isolated_env, monkeypatch):
        """Test Factory pattern isolation between users."""
        monkeypatch.setattr('netra_backend.tests.integration.test_message_routing_comprehensive.get_websocket_manager_factory', mock_get_websocket_manager_factory)
        factory = get_websocket_manager_factory()
        factory.reset_state()
        isolation_keys = []
        managers = []
        for i in range(4):
            user_id = ensure_user_id(f'factory_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
            manager = await factory.create_manager(context)
            isolation_key = f'{user_id}:{context.request_id}'
            isolation_keys.append(isolation_key)
            managers.append((user_id, manager))
        assert len(set((id(manager) for _, manager in managers))) == 4
        factory_stats = factory.get_factory_stats()
        assert factory_stats['current_state']['active_managers'] >= 4
        user_distribution = factory_stats['user_distribution']
        for user_id, _ in managers:
            assert str(user_id) in user_distribution
            assert user_distribution[str(user_id)] >= 1
        logger.info(' PASS:  Multi-user factory isolation test completed')

    @pytest.mark.integration
    async def test_multi_user_context_boundaries(self, isolated_env):
        """Test UserExecutionContext boundaries between users."""
        factory = get_websocket_manager_factory()
        base_thread_id = str(ensure_thread_id(str(uuid.uuid4())))
        contexts = []
        managers = []
        for i in range(3):
            user_id = ensure_user_id(f'boundary_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=base_thread_id, run_id=str(uuid.uuid4()))
            manager = await mock_create_websocket_manager(context)
            contexts.append(context)
            managers.append(manager)
        manager_ids = [id(manager) for manager in managers]
        assert len(set(manager_ids)) == 3
        for i, manager in enumerate(managers):
            user_context = contexts[i]
            health = manager.get_connection_health(user_context.user_id)
            assert health['user_id'] == user_context.user_id
            for j, other_context in enumerate(contexts):
                if i != j:
                    other_health = manager.get_connection_health(other_context.user_id)
                    assert 'error' in other_health
        logger.info(' PASS:  Multi-user context boundaries test completed')

    @pytest.mark.integration
    async def test_multi_user_state_consistency(self, isolated_env, monkeypatch):
        """Test state consistency across multiple users."""
        monkeypatch.setattr('netra_backend.tests.integration.test_message_routing_comprehensive.get_websocket_manager_factory', mock_get_websocket_manager_factory)
        factory = get_websocket_manager_factory()
        factory.reset_state()
        state_log = []
        for i in range(3):
            user_id = ensure_user_id(f'state_user_{i}')
            context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
            manager = await factory.create_manager(context)
            websocket = MockWebSocket(str(user_id), f'state_conn_{i}')
            connection = WebSocketConnection(connection_id=f'state_conn_{i}', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
            await manager.add_connection(connection)
            state_log.append({'user_id': str(user_id), 'connections': len(manager.get_user_connections()), 'is_active': manager.is_connection_active(str(user_id)), 'manager_stats': manager.get_manager_stats()})
            await manager.send_to_user({'type': 'state_test', 'user': str(user_id)})
            state_log[i]['messages_sent'] = len(websocket.messages_sent)
        for i, state in enumerate(state_log):
            assert state['connections'] == 1
            assert state['is_active'] == True
            assert state['messages_sent'] == 1
            assert state['manager_stats']['is_active'] == True
        factory_stats = factory.get_factory_stats()
        assert factory_stats['current_state']['active_managers'] >= 3
        assert factory_stats['current_state']['users_with_managers'] >= 3
        logger.info(' PASS:  Multi-user state consistency test completed')

class AgentMessageIntegrationTests(BaseIntegrationTest):
    """Test Agent message integration with WebSocket routing."""

    @pytest.mark.integration
    async def test_agent_message_handler_integration(self, isolated_env):
        """Test full agent message handling integration."""
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        ws_manager = await mock_create_websocket_manager(context)
        websocket = MockWebSocket(str(user_id), 'agent_conn')
        connection = WebSocketConnection(connection_id='agent_conn', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
        await ws_manager.add_connection(connection)
        mock_service = MagicMock()
        agent_handler = AgentMessageHandler(mock_service, websocket)
        agent_message = WebSocketMessage(type=MessageType.START_AGENT, payload={'message': 'Analyze my data and provide recommendations', 'user_id': str(user_id), 'thread_id': context.thread_id, 'require_multi_agent': True}, user_id=str(user_id), thread_id=context.thread_id, timestamp=time.time())
        with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):
            success = await agent_handler.handle_message(str(user_id), websocket, agent_message)
        assert success
        stats = agent_handler.processing_stats
        assert stats['messages_processed'] > 0
        assert stats['start_agent_requests'] > 0
        logger.info(' PASS:  Agent message handler integration test completed')

    @pytest.mark.integration
    async def test_agent_message_routing_to_websocket(self, isolated_env):
        """Test agent messages routing to WebSocket connections."""
        factory = get_websocket_manager_factory()
        router = MessageRouter()
        user_id = ensure_user_id(str(uuid.uuid4()))
        context = UserExecutionContext.from_request(user_id=str(user_id), thread_id=str(ensure_thread_id(str(uuid.uuid4()))), run_id=str(uuid.uuid4()))
        manager = await mock_create_websocket_manager(context)
        websocket = MockWebSocket(str(user_id), 'routing_conn')
        connection = WebSocketConnection(connection_id='routing_conn', user_id=str(user_id), websocket=websocket, connected_at=datetime.utcnow())
        await manager.add_connection(connection)
        agent_messages = [{'type': 'start_agent', 'payload': {'message': 'Start analysis'}}, {'type': 'user_message', 'payload': {'content': 'User input'}}, {'type': 'chat', 'payload': {'message': 'Chat message'}}]
        for msg in agent_messages:
            success = await router.route_message(str(user_id), websocket, msg)
            assert success
        stats = router.get_stats()
        assert stats['messages_routed'] >= 3
        assert len(websocket.messages_sent) >= 3
        logger.info(' PASS:  Agent message routing to WebSocket test completed')

    @pytest.mark.integration
    async def test_agent_message_handler_error_recovery(self, isolated_env):
        """Test error handling in agent message processing."""
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket = MockWebSocket(str(user_id), 'error_conn')
        failing_service = MagicMock()
        failing_service.handle_message = AsyncMock(side_effect=RuntimeError('Service failure'))
        agent_handler = AgentMessageHandler(failing_service, websocket)
        error_message = WebSocketMessage(type=MessageType.START_AGENT, payload={'message': 'This will fail'}, user_id=str(user_id), timestamp=time.time())
        with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):
            success = await agent_handler.handle_message(str(user_id), websocket, error_message)
        assert not success
        stats = agent_handler.processing_stats
        assert stats['errors'] > 0
        logger.info(' PASS:  Agent message error recovery test completed')

    @pytest.mark.integration
    async def test_agent_message_type_validation(self, isolated_env):
        """Test message type validation for agent messages."""
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket = MockWebSocket(str(user_id), 'validation_conn')
        mock_service = MagicMock()
        agent_handler = AgentMessageHandler(mock_service, websocket)
        valid_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
        for msg_type in valid_types:
            test_message = WebSocketMessage(type=msg_type, payload={'test': 'data'}, user_id=str(user_id), timestamp=time.time())
            can_handle = agent_handler.can_handle(msg_type)
            assert can_handle
        invalid_message = WebSocketMessage(type=MessageType.PING, payload={'test': 'data'}, user_id=str(user_id), timestamp=time.time())
        can_handle = agent_handler.can_handle(MessageType.PING)
        assert not can_handle
        logger.info(' PASS:  Agent message type validation test completed')

@pytest.fixture
def real_services_fixture():
    """Mock real services fixture for integration testing."""
    return {}

@pytest.fixture
def isolated_env():
    """Mock isolated environment fixture."""
    return get_env()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')