"""
Unit Tests for WebSocket Handlers Business Logic

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Core infrastructure that serves all user tiers
- Business Goal: Ensure reliable WebSocket communication that enables AI chat interactions
- Value Impact: Tests critical handlers for connection, typing, heartbeat, and agent communication
- Strategic Impact: Foundation for $120K+ MRR - without working WebSocket handlers, chat has no value

This test suite validates the core business logic of WebSocket message handlers:
1. ConnectionHandler - User connection lifecycle (connect/disconnect acknowledgments)
2. TypingHandler - Real-time typing indicators for chat experience  
3. HeartbeatHandler - Connection health monitoring (ping/pong, heartbeat/ack)
4. AgentRequestHandler - Agent execution requests from E2E tests
5. TestAgentHandler - E2E test agent communication patterns
6. MessageRouter - Message routing to appropriate handlers with priority

CRITICAL: These handlers enable the 5 essential WebSocket events that deliver chat business value:
- agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

Following TEST_CREATION_GUIDE.md:
- Real business logic validation (not mocks)
- SSOT patterns from test_framework/
- Proper test categorization (@pytest.mark.unit)
- Tests that FAIL HARD when broken (no try/except blocks)
- Focus on business value delivery, not infrastructure testing
"""
import asyncio
import json
import pytest
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List
from netra_backend.app.websocket_core.handlers import BaseMessageHandler, ConnectionHandler, TypingHandler, HeartbeatHandler, AgentRequestHandler, E2EAgentHandler, AgentHandler, UserMessageHandler, JsonRpcHandler, ErrorHandler, BatchMessageHandler, MessageRouter, MessageHandler, send_error_to_websocket, send_system_message, get_message_router, get_router_handler_count, list_registered_handlers
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, ServerMessage, ErrorMessage, BatchConfig, create_standard_message, create_error_message, create_server_message
from netra_backend.app.websocket_core.utils import is_websocket_connected
from test_framework.base import BaseUnitTest

class ConnectionHandlerBusinessLogicTests(BaseUnitTest):
    """Test ConnectionHandler business logic for user connection lifecycle."""

    def setUp(self):
        """Set up ConnectionHandler for testing."""
        self.handler = ConnectionHandler()
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = 'websocket_mock'
        self.mock_websocket.send_json = AsyncMock()
        self.websocket_connected_patcher = patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True)
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_connection_handler_supports_required_message_types(self):
        """Test ConnectionHandler supports CONNECT and DISCONNECT message types."""
        supported_types = self.handler.supported_types
        assert MessageType.CONNECT in supported_types, 'Must support CONNECT messages'
        assert MessageType.DISCONNECT in supported_types, 'Must support DISCONNECT messages'
        assert len(supported_types) == 2, 'Should only support connection-related messages'

    @pytest.mark.unit
    def test_connection_handler_can_handle_connect_message(self):
        """Test ConnectionHandler correctly identifies CONNECT messages."""
        can_handle_connect = self.handler.can_handle(MessageType.CONNECT)
        can_handle_disconnect = self.handler.can_handle(MessageType.DISCONNECT)
        cannot_handle_other = self.handler.can_handle(MessageType.USER_MESSAGE)
        assert can_handle_connect is True, 'Must handle CONNECT messages'
        assert can_handle_disconnect is True, 'Must handle DISCONNECT messages'
        assert cannot_handle_other is False, 'Must not handle non-connection messages'

    @pytest.mark.unit
    async def test_connection_handler_processes_connect_message_successfully(self):
        """Test ConnectionHandler processes CONNECT message with proper acknowledgment."""
        user_id = 'test-user-123'
        connect_message = WebSocketMessage(type=MessageType.CONNECT, payload={'status': 'connecting'}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, connect_message)
        assert result is True, 'CONNECT message handling must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'system_message', 'Must send system message response'
        assert call_args['payload']['status'] == 'connected', 'Must confirm connection status'
        assert call_args['payload']['user_id'] == user_id, 'Must include user ID in response'
        assert 'timestamp' in call_args['payload'], 'Must include timestamp'

    @pytest.mark.unit
    async def test_connection_handler_processes_disconnect_message_successfully(self):
        """Test ConnectionHandler processes DISCONNECT message with proper acknowledgment."""
        user_id = 'test-user-456'
        disconnect_message = WebSocketMessage(type=MessageType.DISCONNECT, payload={'reason': 'user_initiated'}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, disconnect_message)
        assert result is True, 'DISCONNECT message handling must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'system_message', 'Must send system message response'
        assert call_args['payload']['status'] == 'disconnect_acknowledged', 'Must acknowledge disconnect'
        assert call_args['payload']['user_id'] == user_id, 'Must include user ID in response'

    @pytest.mark.unit
    async def test_connection_handler_fails_on_websocket_disconnected(self):
        """Test ConnectionHandler fails properly when WebSocket is disconnected."""
        self.websocket_connected_patcher.stop()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=False):
            user_id = 'test-user-789'
            connect_message = WebSocketMessage(type=MessageType.CONNECT, payload={'status': 'connecting'}, timestamp=time.time(), user_id=user_id)
            result = await self.handler.handle_message(user_id, self.mock_websocket, connect_message)
            assert result is False, 'Must fail when WebSocket is disconnected'
            self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.unit
    async def test_connection_handler_handles_websocket_send_failure(self):
        """Test ConnectionHandler handles WebSocket send failures gracefully."""
        user_id = 'test-user-send-fail'
        connect_message = WebSocketMessage(type=MessageType.CONNECT, payload={'status': 'connecting'}, timestamp=time.time(), user_id=user_id)
        with patch('netra_backend.app.websocket_core.handlers.safe_websocket_send', return_value=False):
            result = await self.handler.handle_message(user_id, self.mock_websocket, connect_message)
            assert result is False, 'Must return False when WebSocket send fails'

    @pytest.mark.unit
    async def test_connection_handler_handles_unexpected_message_type(self):
        """Test ConnectionHandler rejects unsupported message types."""
        user_id = 'test-user-invalid'
        invalid_message = WebSocketMessage(type=MessageType.USER_MESSAGE, payload={'text': 'Hello'}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, invalid_message)
        assert result is False, 'Must reject unsupported message types'
        self.mock_websocket.send_json.assert_not_called()

class TypingHandlerBusinessLogicTests(BaseUnitTest):
    """Test TypingHandler business logic for real-time typing indicators."""

    def setUp(self):
        """Set up TypingHandler for testing."""
        self.handler = TypingHandler()
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = 'websocket_mock'
        self.mock_websocket.send_json = AsyncMock()
        self.websocket_connected_patcher = patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True)
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_typing_handler_supports_all_typing_message_types(self):
        """Test TypingHandler supports all required typing indicator message types."""
        supported_types = self.handler.supported_types
        expected_types = [MessageType.USER_TYPING, MessageType.AGENT_TYPING, MessageType.TYPING_STARTED, MessageType.TYPING_STOPPED]
        for message_type in expected_types:
            assert message_type in supported_types, f'Must support {message_type} for typing indicators'

    @pytest.mark.unit
    async def test_typing_handler_processes_user_typing_with_thread_context(self):
        """Test TypingHandler processes USER_TYPING with proper thread context."""
        user_id = 'test-user-typing'
        thread_id = 'thread-123'
        typing_message = WebSocketMessage(type=MessageType.USER_TYPING, payload={'thread_id': thread_id, 'status': 'typing'}, timestamp=time.time(), user_id=user_id, thread_id=thread_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, typing_message)
        assert result is True, 'USER_TYPING message handling must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'system_message', 'Must send system message response'
        assert call_args['payload']['status'] == 'typing_acknowledged', 'Must acknowledge typing'
        assert call_args['payload']['thread_id'] == thread_id, 'Must preserve thread context'
        assert call_args['payload']['user_id'] == user_id, 'Must include user ID'

    @pytest.mark.unit
    async def test_typing_handler_processes_agent_typing_indicator(self):
        """Test TypingHandler processes AGENT_TYPING for AI response indicators."""
        user_id = 'test-user-agent-typing'
        thread_id = 'thread-agent-456'
        agent_typing_message = WebSocketMessage(type=MessageType.AGENT_TYPING, payload={'thread_id': thread_id, 'agent': 'optimization_agent'}, timestamp=time.time(), user_id=user_id, thread_id=thread_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, agent_typing_message)
        assert result is True, 'AGENT_TYPING message handling must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['payload']['type'] == 'agent_typing', 'Must acknowledge agent typing'
        assert call_args['payload']['thread_id'] == thread_id, 'Must preserve thread context'

    @pytest.mark.unit
    async def test_typing_handler_extracts_thread_id_from_multiple_sources(self):
        """Test TypingHandler can extract thread_id from message or payload."""
        user_id = 'test-user-flexible'
        thread_id_in_payload = 'thread-payload-789'
        typing_message = WebSocketMessage(type=MessageType.TYPING_STARTED, payload={'thread_id': thread_id_in_payload, 'text': 'Starting to type...'}, timestamp=time.time(), user_id=user_id, thread_id=None)
        result = await self.handler.handle_message(user_id, self.mock_websocket, typing_message)
        assert result is True, 'Must handle thread_id in payload'
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['payload']['thread_id'] == thread_id_in_payload, 'Must extract thread_id from payload'

class HeartbeatHandlerBusinessLogicTests(BaseUnitTest):
    """Test HeartbeatHandler business logic for connection health monitoring."""

    def setUp(self):
        """Set up HeartbeatHandler for testing."""
        self.handler = HeartbeatHandler()
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = 'websocket_mock'
        self.mock_websocket.send_json = AsyncMock()
        self.websocket_connected_patcher = patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True)
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_heartbeat_handler_supports_all_heartbeat_message_types(self):
        """Test HeartbeatHandler supports all connection health message types."""
        supported_types = self.handler.supported_types
        expected_types = [MessageType.PING, MessageType.PONG, MessageType.HEARTBEAT, MessageType.HEARTBEAT_ACK]
        for message_type in expected_types:
            assert message_type in supported_types, f'Must support {message_type} for connection health'

    @pytest.mark.unit
    async def test_heartbeat_handler_responds_to_ping_with_pong(self):
        """Test HeartbeatHandler responds to PING with PONG message."""
        user_id = 'test-user-ping'
        ping_message = WebSocketMessage(type=MessageType.PING, payload={'client_time': time.time()}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, ping_message)
        assert result is True, 'PING message handling must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'pong', 'Must respond to PING with PONG'
        assert call_args['payload']['user_id'] == user_id, 'Must include user ID in PONG'
        assert 'timestamp' in call_args['payload'], 'Must include server timestamp'

    @pytest.mark.unit
    async def test_heartbeat_handler_responds_to_heartbeat_with_ack(self):
        """Test HeartbeatHandler responds to HEARTBEAT with HEARTBEAT_ACK."""
        user_id = 'test-user-heartbeat'
        heartbeat_message = WebSocketMessage(type=MessageType.HEARTBEAT, payload={'client_health': 'ok'}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, heartbeat_message)
        assert result is True, 'HEARTBEAT message handling must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'heartbeat_ack', 'Must respond to HEARTBEAT with HEARTBEAT_ACK'
        assert call_args['payload']['status'] == 'healthy', 'Must confirm server health'
        assert 'timestamp' in call_args['payload'], 'Must include server timestamp'

    @pytest.mark.unit
    async def test_heartbeat_handler_acknowledges_pong_silently(self):
        """Test HeartbeatHandler acknowledges PONG without response."""
        user_id = 'test-user-pong'
        pong_message = WebSocketMessage(type=MessageType.PONG, payload={'client_response_time': 0.05}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, pong_message)
        assert result is True, 'PONG message handling must succeed'
        self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.unit
    async def test_heartbeat_handler_handles_disconnected_websocket(self):
        """Test HeartbeatHandler fails gracefully when WebSocket is disconnected."""
        self.websocket_connected_patcher.stop()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=False):
            user_id = 'test-user-disconnected'
            ping_message = WebSocketMessage(type=MessageType.PING, payload={}, timestamp=time.time(), user_id=user_id)
            result = await self.handler.handle_message(user_id, self.mock_websocket, ping_message)
            assert result is False, 'Must fail when WebSocket is disconnected'

class MessageRouterBusinessLogicTests(BaseUnitTest):
    """Test MessageRouter business logic for message routing and handler management."""

    def setUp(self):
        """Set up MessageRouter for testing."""
        self.router = MessageRouter()
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = 'websocket_mock'
        self.mock_websocket.send_json = AsyncMock()
        self.websocket_connected_patcher = patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True)
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_message_router_initializes_with_built_in_handlers(self):
        """Test MessageRouter initializes with all required built-in handlers."""
        handler_names = [handler.__class__.__name__ for handler in self.router.builtin_handlers]
        expected_handlers = ['ConnectionHandler', 'TypingHandler', 'HeartbeatHandler', 'AgentHandler', 'UserMessageHandler', 'JsonRpcHandler', 'ErrorHandler', 'BatchMessageHandler']
        for expected_handler in expected_handlers:
            assert expected_handler in handler_names, f'Must include {expected_handler} in built-in handlers'
        assert hasattr(self.router, 'startup_time'), 'Must track startup time for grace period handling'
        assert self.router.startup_grace_period_seconds == 10.0, 'Must have 10-second grace period'

    @pytest.mark.unit
    def test_message_router_handler_precedence_custom_over_builtin(self):
        """Test MessageRouter gives custom handlers precedence over built-in handlers."""

        class CustomConnectionHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.CONNECT])

            async def handle_message(self, user_id, websocket, message):
                return 'custom_handled'
        custom_handler = CustomConnectionHandler()
        self.router.add_handler(custom_handler)
        all_handlers = self.router.handlers
        custom_handlers = self.router.custom_handlers
        builtin_handlers = self.router.builtin_handlers
        assert len(custom_handlers) == 1, 'Must have one custom handler'
        assert all_handlers[0] == custom_handler, 'Custom handler must be first in precedence'
        assert all_handlers[1:] == builtin_handlers, 'Built-in handlers must follow custom handlers'

    @pytest.mark.unit
    async def test_message_router_routes_message_to_correct_handler(self):
        """Test MessageRouter routes messages to appropriate handlers based on type."""
        user_id = 'test-user-routing'
        connect_raw_message = {'type': 'connect', 'payload': {'status': 'connecting'}, 'timestamp': time.time(), 'user_id': user_id}
        result = await self.router.route_message(user_id, self.mock_websocket, connect_raw_message)
        assert result is True, 'Message routing must succeed'
        stats = self.router.get_stats()
        assert stats['messages_routed'] >= 1, 'Must track routed messages'
        assert 'connect' in str(stats['message_types']), 'Must track message type statistics'

    @pytest.mark.unit
    async def test_message_router_handles_unknown_message_types_gracefully(self):
        """Test MessageRouter handles unknown message types with proper acknowledgment."""
        user_id = 'test-user-unknown'
        unknown_message = {'type': 'unknown_message_type_xyz', 'payload': {'data': 'test'}, 'timestamp': time.time()}
        result = await self.router.route_message(user_id, self.mock_websocket, unknown_message)
        assert result is True, 'Unknown message routing must succeed with acknowledgment'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args['type'] == 'ack', 'Must send acknowledgment for unknown messages'
        assert call_args['received_type'] == 'unknown_message_type_xyz', 'Must echo received type'
        assert call_args['user_id'] == user_id, 'Must include user ID'
        assert call_args['status'] == 'acknowledged', 'Must confirm acknowledgment'
        stats = self.router.get_stats()
        assert stats['unhandled_messages'] >= 1, 'Must track unhandled messages'

    @pytest.mark.unit
    def test_message_router_grace_period_status_during_startup(self):
        """Test MessageRouter reports appropriate status during startup grace period."""
        fresh_router = MessageRouter()
        fresh_router.startup_time = time.time()
        status = fresh_router.check_handler_status_with_grace_period()
        assert status['grace_period_active'] is True, 'Must indicate grace period is active'
        assert status['status'] in ['initializing', 'ready'], 'Status must be initializing or ready'
        assert 'elapsed_seconds' in status, 'Must report elapsed time'
        assert status['handler_count'] >= 0, 'Must report handler count'

    @pytest.mark.unit
    def test_message_router_error_status_after_grace_period_with_zero_handlers(self):
        """Test MessageRouter reports error status after grace period with zero handlers."""
        empty_router = MessageRouter()
        empty_router.builtin_handlers = []
        empty_router.custom_handlers = []
        empty_router.startup_time = time.time() - 15.0
        status = empty_router.check_handler_status_with_grace_period()
        assert status['status'] == 'error', 'Must report error status with zero handlers'
        assert status['grace_period_active'] is False, 'Grace period must be inactive'
        assert status['handler_count'] == 0, 'Must report zero handlers'
        assert 'No handlers registered' in status['message'], 'Must explain the error'

    @pytest.mark.unit
    async def test_message_router_prepares_jsonrpc_messages_correctly(self):
        """Test MessageRouter correctly processes JSON-RPC messages."""
        user_id = 'test-user-jsonrpc'
        jsonrpc_message = {'jsonrpc': '2.0', 'method': 'tool_execution', 'params': {'tool': 'optimize_costs', 'input': 'analyze AWS'}, 'id': 'req-123'}
        result = await self.router.route_message(user_id, self.mock_websocket, jsonrpc_message)
        assert result is True, 'JSON-RPC message routing must succeed'
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert 'jsonrpc' in call_args, 'Must respond with JSON-RPC format'
        assert call_args['id'] == 'req-123', 'Must preserve request ID'

    @pytest.mark.unit
    def test_message_router_tracks_comprehensive_statistics(self):
        """Test MessageRouter tracks comprehensive statistics for monitoring."""

        class StatsHandlerTests(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.test_stat = 'active'

            async def handle_message(self, user_id, websocket, message):
                return True

            def get_stats(self):
                return {'test_stat': self.test_stat}
        stats_handler = StatsHandlerTests()
        self.router.add_handler(stats_handler)
        stats = self.router.get_stats()
        required_stats = ['messages_routed', 'unhandled_messages', 'handler_errors', 'message_types', 'handler_stats', 'handler_order', 'handler_count', 'handler_status']
        for required_stat in required_stats:
            assert required_stat in stats, f'Must track {required_stat} statistic'
        assert 'StatsHandlerTests' in stats['handler_stats'], 'Must include custom handler stats'
        assert stats['handler_stats']['StatsHandlerTests']['test_stat'] == 'active', 'Must preserve handler stats'
        assert len(stats['handler_order']) > 0, 'Must track handler execution order'
        assert '[0] StatsHandlerTests' in stats['handler_order'], 'Must show custom handler precedence'

class AgentRequestHandlerBusinessLogicTests(BaseUnitTest):
    """Test AgentRequestHandler business logic for E2E test agent communication."""

    def setUp(self):
        """Set up AgentRequestHandler for testing."""
        self.handler = AgentRequestHandler()
        self.mock_websocket = Mock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

    @pytest.mark.unit
    def test_agent_request_handler_supports_agent_message_types(self):
        """Test AgentRequestHandler supports AGENT_REQUEST and START_AGENT types."""
        supported_types = self.handler.supported_types
        assert MessageType.AGENT_REQUEST in supported_types, 'Must support AGENT_REQUEST'
        assert MessageType.START_AGENT in supported_types, 'Must support START_AGENT'

    @pytest.mark.unit
    async def test_agent_request_handler_processes_single_agent_request(self):
        """Test AgentRequestHandler processes single agent requests correctly."""
        user_id = 'test-user-single-agent'
        agent_request = WebSocketMessage(type=MessageType.AGENT_REQUEST, payload={'message': 'Optimize my cloud costs', 'turn_id': 'turn-123', 'require_multi_agent': False, 'real_llm': False}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, agent_request)
        assert result is True, 'Single agent request handling must succeed'
        self.mock_websocket.send_text.assert_called_once()
        response_text = self.mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_text)
        assert response_data['type'] == 'agent_response', 'Must send agent_response type'
        assert response_data['payload']['status'] == 'success', 'Must indicate successful processing'
        assert 'Optimize my cloud costs' in response_data['payload']['content'], 'Must echo user message'
        assert response_data['payload']['agents_involved'] == ['triage'], 'Single agent should use triage'
        assert response_data['payload']['turn_id'] == 'turn-123', 'Must preserve turn_id'

    @pytest.mark.unit
    async def test_agent_request_handler_processes_multi_agent_request(self):
        """Test AgentRequestHandler processes multi-agent collaboration requests."""
        user_id = 'test-user-multi-agent'
        multi_agent_request = WebSocketMessage(type=MessageType.AGENT_REQUEST, payload={'message': 'Comprehensive cost optimization analysis with recommendations', 'turn_id': 'turn-456', 'require_multi_agent': True, 'real_llm': True}, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, multi_agent_request)
        assert result is True, 'Multi-agent request handling must succeed'
        response_text = self.mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_text)
        assert response_data['payload']['agents_involved'] == ['supervisor', 'triage', 'optimization'], 'Multi-agent should involve all three agents'
        assert 'Multi-agent collaboration completed' in response_data['payload']['content'], 'Must indicate multi-agent processing'
        assert response_data['payload']['real_llm_used'] is True, 'Must track real LLM usage'
        assert response_data['payload']['orchestration_time'] > 1.0, 'Multi-agent should take longer'

    @pytest.mark.unit
    async def test_agent_request_handler_handles_processing_errors_gracefully(self):
        """Test AgentRequestHandler handles processing errors with proper error responses."""
        user_id = 'test-user-error'
        error_request = WebSocketMessage(type=MessageType.AGENT_REQUEST, payload=None, timestamp=time.time(), user_id=user_id)
        result = await self.handler.handle_message(user_id, self.mock_websocket, error_request)
        assert result is False, 'Must return False for processing errors'
        self.mock_websocket.send_text.assert_called_once()
        response_text = self.mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_text)
        assert response_data['type'] == 'error_message', 'Must send error_message type'
        assert response_data['error_code'] == 'AGENT_REQUEST_ERROR', 'Must use appropriate error code'
        assert 'Failed to process agent request' in response_data['error_message'], 'Must explain error'

class GlobalMessageRouterFunctionsTests(BaseUnitTest):
    """Test global message router functions and utilities."""

    @pytest.mark.unit
    def test_get_message_router_returns_singleton_instance(self):
        """Test get_message_router returns consistent singleton instance."""
        router1 = get_message_router()
        router2 = get_message_router()
        assert router1 is router2, 'Must return same singleton instance'
        assert isinstance(router1, MessageRouter), 'Must return MessageRouter instance'

    @pytest.mark.unit
    def test_get_router_handler_count_tracks_handlers_accurately(self):
        """Test get_router_handler_count returns accurate handler count."""
        initial_count = get_router_handler_count()
        assert initial_count >= 0, 'Handler count must be non-negative'
        router = get_message_router()

        class CountHandlerTests(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])

            async def handle_message(self, user_id, websocket, message):
                return True
        test_handler = CountHandlerTests()
        router.add_handler(test_handler)
        updated_count = get_router_handler_count()
        assert updated_count == initial_count + 1, 'Handler count must increase when handler added'

    @pytest.mark.unit
    def test_list_registered_handlers_returns_handler_names(self):
        """Test list_registered_handlers returns list of handler class names."""
        handler_names = list_registered_handlers()
        assert isinstance(handler_names, list), 'Must return list of handler names'
        assert len(handler_names) > 0, 'Must have at least some built-in handlers'
        expected_builtin_handlers = ['ConnectionHandler', 'TypingHandler', 'HeartbeatHandler', 'UserMessageHandler']
        for expected_handler in expected_builtin_handlers:
            assert expected_handler in handler_names, f'Must list {expected_handler}'

    @pytest.mark.unit
    async def test_send_error_to_websocket_utility_function(self):
        """Test send_error_to_websocket utility sends properly formatted errors."""
        mock_websocket = Mock()
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = 'websocket_mock'
        mock_websocket.send_json = AsyncMock()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            result = await send_error_to_websocket(mock_websocket, 'TEST_ERROR', 'This is a test error message', {'additional_data': 'test_value'})
            assert result is True, 'Error sending must succeed'
            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]
            assert call_args['type'] == 'error_message', 'Must use error_message type'
            assert call_args['error_code'] == 'TEST_ERROR', 'Must preserve error code'
            assert call_args['error_message'] == 'This is a test error message', 'Must preserve error message'
            assert call_args['details']['additional_data'] == 'test_value', 'Must include additional details'

    @pytest.mark.unit
    async def test_send_system_message_utility_function(self):
        """Test send_system_message utility sends properly formatted system messages."""
        mock_websocket = Mock()
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = 'websocket_mock'
        mock_websocket.send_json = AsyncMock()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            result = await send_system_message(mock_websocket, 'System initialization complete', {'status': 'ready', 'version': '1.0.0'})
            assert result is True, 'System message sending must succeed'
            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]
            assert call_args['type'] == 'system_message', 'Must use system_message type'
            assert call_args['payload']['content'] == 'System initialization complete', 'Must preserve content'
            assert call_args['payload']['status'] == 'ready', 'Must include additional data'
            assert call_args['payload']['version'] == '1.0.0', 'Must preserve additional data'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')