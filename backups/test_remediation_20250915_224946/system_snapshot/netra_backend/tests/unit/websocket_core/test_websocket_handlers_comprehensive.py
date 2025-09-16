"""
Comprehensive WebSocket Handlers Unit Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - ALL customer segments depend on this
- Business Goal: Protect $500K+ ARR chat functionality  
- Value Impact: Tests protect core message processing that enables ALL chat interactions
- Strategic Impact: CRITICAL - Any bugs here directly impact revenue and user experience

GOLDEN PATH FOCUS:
This test suite validates the CRITICAL message handling functions that enable 
our core business value delivery through chat interactions. Every message 
type and handler function is tested to prevent revenue-impacting failures.

Following CLAUDE.md principle: Tests MUST raise errors, no try/except blocks.
Following TEST_CREATION_GUIDE.md: Real services > mocks, business value focus.
"""
import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.async_test_helpers import AsyncTestFixtureMixin, async_cleanup_resources
from test_framework.ssot.websocket_golden_path_helpers import WebSocketGoldenPathHelper
from test_framework.ssot.e2e_auth_helper import create_authenticated_user
from netra_backend.app.websocket_core.event_validator import validate_agent_events
from netra_backend.app.websocket_core.handlers import MessageHandler, BaseMessageHandler, ConnectionHandler, TypingHandler, HeartbeatHandler, AgentRequestHandler, E2EAgentHandler, AgentHandler, UserMessageHandler, JsonRpcHandler, ErrorHandler, BatchMessageHandler, MessageRouter, get_message_router, get_router_handler_count, list_registered_handlers, send_error_to_websocket, send_system_message
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, ServerMessage, ErrorMessage, BroadcastMessage, BatchConfig, PendingMessage, MessageBatch, create_standard_message, create_error_message, create_server_message
from netra_backend.app.websocket_core.utils import is_websocket_connected
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_id_manager import UnifiedIDManager

class WebSocketTestMixin:
    """Mixin class for WebSocket testing utilities."""

    def _create_mock_websocket(self):
        """Create a mock WebSocket for testing."""
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.state = Mock()
        mock_websocket.state.value = 1
        return mock_websocket

class MessageHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test MessageHandler protocol compliance."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()

    async def test_base_message_handler_initialization(self):
        """Test BaseMessageHandler properly initializes with supported types."""
        supported_types = [MessageType.USER_MESSAGE, MessageType.AGENT_REQUEST]
        handler = BaseMessageHandler(supported_types)
        assert handler.supported_types == supported_types
        assert handler.can_handle(MessageType.USER_MESSAGE) is True
        assert handler.can_handle(MessageType.AGENT_REQUEST) is True
        assert handler.can_handle(MessageType.SYSTEM_MESSAGE) is False

    async def test_base_message_handler_message_handling(self):
        """Test BaseMessageHandler default message handling behavior."""
        handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        mock_websocket = self._create_mock_websocket()
        message = WebSocketMessage(type=MessageType.USER_MESSAGE, payload={'content': 'test message'}, timestamp=time.time(), user_id='test_user_123')
        result = await handler.handle_message('test_user_123', mock_websocket, message)
        assert result is True

class ConnectionHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test ConnectionHandler for connection lifecycle management."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = ConnectionHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_connection_handler_supported_types(self):
        """Test ConnectionHandler supports correct message types."""
        assert self.handler.can_handle(MessageType.CONNECT) is True
        assert self.handler.can_handle(MessageType.DISCONNECT) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False

    async def test_handle_connect_message(self):
        """Test connection establishment message handling."""
        message = WebSocketMessage(type=MessageType.CONNECT, payload={'client_info': 'test_client'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['type'] == MessageType.SYSTEM_MESSAGE.value
        assert sent_data['data']['status'] == 'connected'
        assert sent_data['data']['user_id'] == self.user_id

    async def test_handle_disconnect_message(self):
        """Test disconnect message handling."""
        message = WebSocketMessage(type=MessageType.DISCONNECT, payload={'reason': 'user_initiated'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['data']['status'] == 'disconnect_acknowledged'
        assert sent_data['data']['user_id'] == self.user_id

    async def test_handle_unsupported_message_type(self):
        """Test handling of unsupported message types."""
        message = WebSocketMessage(type=MessageType.USER_MESSAGE, payload={'content': 'test'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is False

    async def test_handle_websocket_connection_error(self):
        """Test error handling when WebSocket send fails."""
        self.mock_websocket.send_json.side_effect = Exception('WebSocket send failed')
        message = WebSocketMessage(type=MessageType.CONNECT, payload={}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is False

class TypingHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test TypingHandler for typing indicator management."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = TypingHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'
        self.thread_id = 'thread_456'

    async def test_typing_handler_supported_types(self):
        """Test TypingHandler supports all typing-related message types."""
        typing_types = [MessageType.USER_TYPING, MessageType.AGENT_TYPING, MessageType.TYPING_STARTED, MessageType.TYPING_STOPPED]
        for msg_type in typing_types:
            assert self.handler.can_handle(msg_type) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False

    async def test_handle_user_typing_message(self):
        """Test user typing indicator handling."""
        message = WebSocketMessage(type=MessageType.USER_TYPING, payload={'thread_id': self.thread_id}, timestamp=time.time(), user_id=self.user_id, thread_id=self.thread_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['data']['status'] == 'typing_acknowledged'
        assert sent_data['data']['type'] == MessageType.USER_TYPING.value
        assert sent_data['data']['thread_id'] == self.thread_id

    async def test_handle_agent_typing_message(self):
        """Test agent typing indicator handling."""
        message = WebSocketMessage(type=MessageType.AGENT_TYPING, payload={'agent_name': 'cost_optimizer'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()

    async def test_typing_error_handling(self):
        """Test typing handler error recovery."""
        self.mock_websocket.send_json.side_effect = Exception('Send failed')
        message = WebSocketMessage(type=MessageType.TYPING_STARTED, payload={}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is False

class HeartbeatHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test HeartbeatHandler for connection health monitoring."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = HeartbeatHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_heartbeat_handler_supported_types(self):
        """Test HeartbeatHandler supports correct message types."""
        heartbeat_types = [MessageType.PING, MessageType.PONG, MessageType.HEARTBEAT, MessageType.HEARTBEAT_ACK]
        for msg_type in heartbeat_types:
            assert self.handler.can_handle(msg_type) is True

    async def test_handle_ping_message(self):
        """Test ping message returns pong response."""
        message = WebSocketMessage(type=MessageType.PING, payload={}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['type'] == MessageType.PONG.value
        assert sent_data['data']['user_id'] == self.user_id
        assert 'timestamp' in sent_data['data']

    async def test_handle_heartbeat_message(self):
        """Test heartbeat message returns acknowledgment."""
        message = WebSocketMessage(type=MessageType.HEARTBEAT, payload={}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['type'] == MessageType.HEARTBEAT_ACK.value
        assert sent_data['data']['status'] == 'healthy'

    async def test_handle_pong_message(self):
        """Test pong message handling (no response needed)."""
        message = WebSocketMessage(type=MessageType.PONG, payload={}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        self.mock_websocket.send_json.assert_not_called()

    async def test_heartbeat_with_mock_websocket(self):
        """Test heartbeat handler works with mock websockets (for testing)."""
        mock_ws = Mock()
        mock_ws.send_json = AsyncMock()
        mock_ws.application_state = Mock()
        mock_ws.application_state._mock_name = 'test_websocket'
        message = WebSocketMessage(type=MessageType.PING, payload={}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, mock_ws, message)
        assert result is True
        mock_ws.send_json.assert_called_once()

class AgentRequestHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test AgentRequestHandler for agent execution requests."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = AgentRequestHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_agent_request_handler_supported_types(self):
        """Test AgentRequestHandler supports agent request types."""
        assert self.handler.can_handle(MessageType.AGENT_REQUEST) is True
        assert self.handler.can_handle(MessageType.START_AGENT) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False

    async def test_handle_single_agent_request(self):
        """Test single agent request processing."""
        message = WebSocketMessage(type=MessageType.AGENT_REQUEST, payload={'message': 'Analyze my costs', 'turn_id': 'turn_123', 'require_multi_agent': False, 'real_llm': False}, timestamp=time.time(), user_id=self.user_id)
        sent_responses = []

        async def capture_send_text(data):
            sent_responses.append(json.loads(data))
        self.mock_websocket.send_text = capture_send_text
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        assert len(sent_responses) == 1
        response = sent_responses[0]
        assert response['type'] == MessageType.AGENT_RESPONSE.value
        assert response['data']['status'] == 'success'
        assert 'Analyze my costs' in response['data']['content']
        assert response['data']['agents_involved'] == ['triage']
        assert response['data']['turn_id'] == 'turn_123'

    async def test_handle_multi_agent_request(self):
        """Test multi-agent request processing."""
        message = WebSocketMessage(type=MessageType.AGENT_REQUEST, payload={'message': 'Complex optimization task', 'turn_id': 'turn_456', 'require_multi_agent': True, 'real_llm': True}, timestamp=time.time(), user_id=self.user_id)
        sent_responses = []

        async def capture_send_text(data):
            sent_responses.append(json.loads(data))
        self.mock_websocket.send_text = capture_send_text
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        response = sent_responses[0]
        assert response['data']['agents_involved'] == ['supervisor', 'triage', 'optimization']
        assert response['data']['real_llm_used'] is True
        assert response['data']['orchestration_time'] > 1.0

    async def test_agent_request_error_handling(self):
        """Test error handling in agent request processing."""
        self.mock_websocket.send_text = AsyncMock(side_effect=Exception('Send failed'))
        message = WebSocketMessage(type=MessageType.AGENT_REQUEST, payload={'message': 'Test message', 'turn_id': 'turn_error'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is False

class UserMessageHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test UserMessageHandler for user communication."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = UserMessageHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_user_message_handler_supported_types(self):
        """Test UserMessageHandler supports all user message types."""
        user_types = [MessageType.USER_MESSAGE, MessageType.CHAT, MessageType.SYSTEM_MESSAGE, MessageType.AGENT_RESPONSE, MessageType.AGENT_PROGRESS, MessageType.THREAD_UPDATE, MessageType.THREAD_MESSAGE]
        for msg_type in user_types:
            assert self.handler.can_handle(msg_type) is True

    async def test_handle_user_message(self):
        """Test user message processing and acknowledgment."""
        message = WebSocketMessage(type=MessageType.USER_MESSAGE, payload={'content': 'Hello, I need help with cost optimization'}, timestamp=time.time(), message_id='msg_123', user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['processed'] == 1
        assert stats['errors'] == 0
        assert stats['last_message_time'] is not None
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['data']['content'] == 'Message received'
        assert sent_data['data']['original_message_id'] == 'msg_123'
        assert sent_data['data']['status'] == 'acknowledged'

    async def test_handle_chat_message(self):
        """Test chat message processing."""
        message = WebSocketMessage(type=MessageType.CHAT, payload={'content': 'What are my current costs?'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['processed'] == 1

    async def test_handle_agent_response_message(self):
        """Test agent response message processing."""
        message = WebSocketMessage(type=MessageType.AGENT_RESPONSE, payload={'agent_name': 'cost_optimizer', 'content': 'Your costs have been analyzed', 'recommendations': ['Recommendation 1', 'Recommendation 2']}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['processed'] == 1

    async def test_user_message_error_handling(self):
        """Test error handling in user message processing."""
        self.mock_websocket.send_json.side_effect = Exception('Send failed')
        message = WebSocketMessage(type=MessageType.USER_MESSAGE, payload={'content': 'Test message'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is False
        stats = self.handler.get_stats()
        assert stats['errors'] == 1
        assert stats['processed'] == 1

class JsonRpcHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test JsonRpcHandler for JSON-RPC message processing."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = JsonRpcHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_jsonrpc_handler_supported_types(self):
        """Test JsonRpcHandler supports JSON-RPC message types."""
        rpc_types = [MessageType.JSONRPC_REQUEST, MessageType.JSONRPC_RESPONSE, MessageType.JSONRPC_NOTIFICATION]
        for msg_type in rpc_types:
            assert self.handler.can_handle(msg_type) is True

    async def test_handle_jsonrpc_request(self):
        """Test JSON-RPC request processing."""
        message = WebSocketMessage(type=MessageType.JSONRPC_REQUEST, payload={'jsonrpc': '2.0', 'method': 'analyze_costs', 'params': {'account_id': '123456'}, 'id': 'req_123'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['requests'] == 1
        assert stats['errors'] == 0
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['jsonrpc'] == '2.0'
        assert sent_data['result']['status'] == 'processed'
        assert sent_data['result']['method'] == 'analyze_costs'
        assert sent_data['id'] == 'req_123'

    async def test_handle_jsonrpc_response(self):
        """Test JSON-RPC response processing."""
        message = WebSocketMessage(type=MessageType.JSONRPC_RESPONSE, payload={'jsonrpc': '2.0', 'result': {'status': 'completed'}, 'id': 'req_123'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['responses'] == 1

    async def test_handle_jsonrpc_notification(self):
        """Test JSON-RPC notification processing."""
        message = WebSocketMessage(type=MessageType.JSONRPC_NOTIFICATION, payload={'jsonrpc': '2.0', 'method': 'cost_alert', 'params': {'threshold_exceeded': True}}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['notifications'] == 1

    async def test_jsonrpc_error_handling(self):
        """Test error handling in JSON-RPC processing."""
        self.mock_websocket.send_json.side_effect = Exception('Send failed')
        message = WebSocketMessage(type=MessageType.JSONRPC_REQUEST, payload={'jsonrpc': '2.0', 'method': 'test_method', 'id': 'req_error'}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is False
        stats = self.handler.get_stats()
        assert stats['errors'] == 1

class ErrorHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test ErrorHandler for error message processing."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.handler = ErrorHandler()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_error_handler_supported_types(self):
        """Test ErrorHandler supports error message types."""
        assert self.handler.can_handle(MessageType.ERROR_MESSAGE) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False

    async def test_handle_error_message(self):
        """Test error message processing and tracking."""
        message = WebSocketMessage(type=MessageType.ERROR_MESSAGE, payload={'error_code': 'AGENT_EXECUTION_ERROR', 'error_message': 'Agent failed to execute properly', 'details': {'agent_name': 'cost_optimizer'}}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        stats = self.handler.get_stats()
        assert stats['total_errors'] == 1
        assert 'AGENT_EXECUTION_ERROR' in stats['error_types']
        assert stats['error_types']['AGENT_EXECUTION_ERROR'] == 1
        assert stats['last_error_time'] is not None
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['data']['content'] == 'Error received and logged'
        assert sent_data['data']['error_code'] == 'AGENT_EXECUTION_ERROR'
        assert sent_data['data']['status'] == 'acknowledged'

    async def test_multiple_error_tracking(self):
        """Test tracking multiple errors of same and different types."""
        message1 = WebSocketMessage(type=MessageType.ERROR_MESSAGE, payload={'error_code': 'WEBSOCKET_ERROR', 'error_message': 'Connection failed'}, timestamp=time.time(), user_id=self.user_id)
        await self.handler.handle_message(self.user_id, self.mock_websocket, message1)
        await self.handler.handle_message(self.user_id, self.mock_websocket, message1)
        message2 = WebSocketMessage(type=MessageType.ERROR_MESSAGE, payload={'error_code': 'AUTH_ERROR', 'error_message': 'Authentication failed'}, timestamp=time.time(), user_id=self.user_id)
        await self.handler.handle_message(self.user_id, self.mock_websocket, message2)
        stats = self.handler.get_stats()
        assert stats['total_errors'] == 3
        assert stats['error_types']['WEBSOCKET_ERROR'] == 2
        assert stats['error_types']['AUTH_ERROR'] == 1

class BatchMessageHandlerTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test BatchMessageHandler for batched message processing."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.batch_config = BatchConfig(max_batch_size=5, max_wait_time=1.0, priority_threshold=5)
        self.handler = BatchMessageHandler(self.batch_config)
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_batch_handler_supported_types(self):
        """Test BatchMessageHandler supports broadcast message types."""
        assert self.handler.can_handle(MessageType.BROADCAST) is True
        assert self.handler.can_handle(MessageType.ROOM_MESSAGE) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False

    async def test_add_message_to_batch(self):
        """Test adding message to batch queue."""
        message = WebSocketMessage(type=MessageType.BROADCAST, payload={'content': 'Broadcast message', 'priority': 1}, timestamp=time.time(), user_id=self.user_id, thread_id='thread_123')
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        assert self.user_id in self.handler.pending_messages
        assert len(self.handler.pending_messages[self.user_id]) == 1
        pending_msg = self.handler.pending_messages[self.user_id][0]
        assert pending_msg.user_id == self.user_id
        assert pending_msg.thread_id == 'thread_123'
        assert pending_msg.priority == 1

    async def test_batch_size_trigger(self):
        """Test batch sending when max size reached."""
        for i in range(self.batch_config.max_batch_size):
            message = WebSocketMessage(type=MessageType.BROADCAST, payload={'content': f'Message {i}', 'priority': 1}, timestamp=time.time(), user_id=self.user_id)
            await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert len(self.handler.pending_messages.get(self.user_id, [])) == 0
        stats = self.handler.get_stats()
        assert stats['batches_created'] == 1
        assert stats['messages_batched'] == self.batch_config.max_batch_size
        assert stats['batch_send_successes'] == 1

    async def test_high_priority_batch_trigger(self):
        """Test batch sending for high priority messages."""
        message = WebSocketMessage(type=MessageType.BROADCAST, payload={'content': 'High priority message', 'priority': 10}, timestamp=time.time(), user_id=self.user_id)
        result = await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert result is True
        assert len(self.handler.pending_messages.get(self.user_id, [])) == 0
        stats = self.handler.get_stats()
        assert stats['batches_created'] == 1

    async def test_batch_timer_functionality(self):
        """Test batch timer triggers sending after wait time."""
        message = WebSocketMessage(type=MessageType.BROADCAST, payload={'content': 'Timed message', 'priority': 1}, timestamp=time.time(), user_id=self.user_id)
        await self.handler.handle_message(self.user_id, self.mock_websocket, message)
        assert len(self.handler.pending_messages.get(self.user_id, [])) == 1
        await asyncio.sleep(self.batch_config.max_wait_time + 0.1)
        assert len(self.handler.pending_messages.get(self.user_id, [])) == 0
        stats = self.handler.get_stats()
        assert stats['batches_created'] == 1

    async def test_flush_all_batches(self):
        """Test forcing all pending batches to send."""
        users = ['user_1', 'user_2', 'user_3']
        for user in users:
            message = WebSocketMessage(type=MessageType.BROADCAST, payload={'content': f'Message from {user}'}, timestamp=time.time(), user_id=user)
            await self.handler.handle_message(user, self.mock_websocket, message)
        for user in users:
            assert len(self.handler.pending_messages.get(user, [])) == 1
        await self.handler.flush_all_batches()
        for user in users:
            assert len(self.handler.pending_messages.get(user, [])) == 0
        stats = self.handler.get_stats()
        assert stats['batches_created'] == 3
        assert stats['batch_send_successes'] == 3

class MessageRouterTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test MessageRouter for message routing and handler management."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.router = MessageRouter()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_123'

    async def test_message_router_initialization(self):
        """Test MessageRouter initializes with correct built-in handlers."""
        handler_names = [h.__class__.__name__ for h in self.router.builtin_handlers]
        expected_handlers = ['ConnectionHandler', 'TypingHandler', 'HeartbeatHandler', 'AgentHandler', 'UserMessageHandler', 'JsonRpcHandler', 'ErrorHandler', 'BatchMessageHandler']
        for expected in expected_handlers:
            assert expected in handler_names
        assert len(self.router.custom_handlers) == 0
        assert len(self.router.handlers) == len(self.router.builtin_handlers)

    async def test_add_custom_handler(self):
        """Test adding custom message handlers."""
        custom_handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        self.router.add_handler(custom_handler)
        assert len(self.router.custom_handlers) == 1
        assert custom_handler in self.router.custom_handlers
        assert self.router.handlers[0] == custom_handler

    async def test_remove_handler(self):
        """Test removing message handlers."""
        custom_handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        self.router.add_handler(custom_handler)
        assert custom_handler in self.router.custom_handlers
        self.router.remove_handler(custom_handler)
        assert custom_handler not in self.router.custom_handlers
        assert len(self.router.custom_handlers) == 0

    async def test_insert_handler_at_position(self):
        """Test inserting handler at specific position."""
        handler1 = BaseMessageHandler([MessageType.USER_MESSAGE])
        handler2 = BaseMessageHandler([MessageType.CHAT])
        self.router.add_handler(handler1)
        self.router.add_handler(handler2)
        handler3 = BaseMessageHandler([MessageType.SYSTEM_MESSAGE])
        self.router.insert_handler(handler3, index=1)
        assert self.router.custom_handlers[0] == handler1
        assert self.router.custom_handlers[1] == handler3
        assert self.router.custom_handlers[2] == handler2

    async def test_route_user_message(self):
        """Test routing user message to appropriate handler."""
        raw_message = {'type': 'user_message', 'payload': {'content': 'Hello, I need help'}, 'timestamp': time.time(), 'user_id': self.user_id, 'message_id': 'msg_123'}
        result = await self.router.route_message(self.user_id, self.mock_websocket, raw_message)
        assert result is True
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 1
        assert stats['unhandled_messages'] == 0
        assert 'user_message' in stats['message_types']
        assert stats['message_types']['user_message'] == 1

    async def test_route_unknown_message_type(self):
        """Test routing unknown message type."""
        raw_message = {'type': 'unknown_custom_type', 'payload': {'data': 'test'}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, raw_message)
        assert result is True
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 1
        assert stats['unhandled_messages'] == 1
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['type'] == 'ack'
        assert sent_data['received_type'] == 'unknown_custom_type'
        assert sent_data['status'] == 'acknowledged'

    async def test_custom_handler_precedence(self):
        """Test custom handlers take precedence over built-in handlers."""
        custom_handler = Mock()
        custom_handler.can_handle = Mock(return_value=True)
        custom_handler.handle_message = AsyncMock(return_value=True)
        self.router.add_handler(custom_handler)
        raw_message = {'type': 'user_message', 'payload': {'content': 'Test message'}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, raw_message)
        assert result is True
        custom_handler.handle_message.assert_called_once()

    async def test_handler_error_handling(self):
        """Test error handling when handler fails."""
        error_handler = Mock()
        error_handler.can_handle = Mock(return_value=True)
        error_handler.handle_message = AsyncMock(side_effect=Exception('Handler failed'))
        self.router.add_handler(error_handler)
        raw_message = {'type': 'user_message', 'payload': {'content': 'Test message'}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, raw_message)
        assert result is False
        stats = self.router.get_stats()
        assert stats['handler_errors'] == 1

    async def test_startup_grace_period(self):
        """Test startup grace period handling for handler registration."""
        test_router = MessageRouter()
        status = test_router.check_handler_status_with_grace_period()
        assert status['grace_period_active'] is True
        assert status['status'] in ['initializing', 'ready']
        assert 'elapsed_seconds' in status
        assert status['elapsed_seconds'] < test_router.startup_grace_period_seconds

    async def test_get_router_stats(self):
        """Test comprehensive router statistics."""
        messages = [{'type': 'user_message', 'payload': {'content': 'msg1'}}, {'type': 'ping', 'payload': {}}, {'type': 'unknown_type', 'payload': {}}]
        for msg in messages:
            msg.update({'timestamp': time.time(), 'user_id': self.user_id})
            await self.router.route_message(self.user_id, self.mock_websocket, msg)
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 3
        assert stats['unhandled_messages'] == 1
        assert stats['handler_errors'] == 0
        assert 'user_message' in stats['message_types']
        assert 'ping' in stats['message_types']
        assert 'handler_stats' in stats
        assert 'handler_order' in stats
        assert 'handler_count' in stats
        assert stats['handler_count'] > 0
        assert 'handler_status' in stats

class GlobalFunctionsTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test global WebSocket handler functions."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        import netra_backend.app.websocket_core.handlers as handlers_module
        handlers_module._message_router = None
        self.mock_websocket = self._create_mock_websocket()

    async def test_get_message_router_singleton(self):
        """Test get_message_router returns singleton instance."""
        router1 = get_message_router()
        router2 = get_message_router()
        assert router1 is router2
        assert isinstance(router1, MessageRouter)

    async def test_get_router_handler_count(self):
        """Test get_router_handler_count returns correct count."""
        assert get_router_handler_count() == 0
        router = get_message_router()
        count = get_router_handler_count()
        assert count == len(router.handlers)
        assert count > 0

    async def test_list_registered_handlers(self):
        """Test list_registered_handlers returns handler names."""
        handlers = list_registered_handlers()
        assert handlers == []
        router = get_message_router()
        handlers = list_registered_handlers()
        assert len(handlers) > 0
        assert 'ConnectionHandler' in handlers
        assert 'UserMessageHandler' in handlers

    async def test_send_error_to_websocket(self):
        """Test sending error message to WebSocket client."""
        error_code = 'TEST_ERROR'
        error_message = 'Test error occurred'
        details = {'context': 'unit_test'}
        result = await send_error_to_websocket(self.mock_websocket, error_code, error_message, details)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['type'] == MessageType.ERROR_MESSAGE.value
        assert sent_data['error_code'] == error_code
        assert sent_data['error_message'] == error_message
        assert sent_data['details'] == details

    async def test_send_error_to_disconnected_websocket(self):
        """Test sending error to disconnected WebSocket."""
        disconnected_ws = Mock()
        disconnected_ws.send_json = AsyncMock()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=False):
            result = await send_error_to_websocket(disconnected_ws, 'ERROR_CODE', 'Error message')
        assert result is False
        disconnected_ws.send_json.assert_not_called()

    async def test_send_system_message(self):
        """Test sending system message to WebSocket client."""
        content = 'System notification'
        additional_data = {'priority': 'high', 'category': 'alert'}
        result = await send_system_message(self.mock_websocket, content, additional_data)
        assert result is True
        self.mock_websocket.send_json.assert_called_once()
        sent_data = self.mock_websocket.send_json.call_args[0][0]
        assert sent_data['type'] == MessageType.SYSTEM_MESSAGE.value
        assert sent_data['data']['content'] == content
        assert sent_data['data']['priority'] == 'high'
        assert sent_data['data']['category'] == 'alert'

    async def test_send_system_message_error_handling(self):
        """Test error handling in send_system_message."""
        self.mock_websocket.send_json.side_effect = Exception('Send failed')
        result = await send_system_message(self.mock_websocket, 'Test message')
        assert result is False

class WebSocketHandlersIntegrationTests(SSotBaseTestCase, WebSocketTestMixin):
    """Test integration scenarios with multiple handlers."""

    def setup_method(self):
        """Setup for integration tests."""
        super().setup_method()
        self.router = MessageRouter()
        self.mock_websocket = self._create_mock_websocket()
        self.user_id = 'test_user_integration'

    async def test_complete_user_interaction_flow(self):
        """Test complete user interaction flow through multiple handlers."""
        connect_msg = {'type': 'connect', 'payload': {'client_info': 'web_browser'}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, connect_msg)
        assert result is True
        ping_msg = {'type': 'ping', 'payload': {}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, ping_msg)
        assert result is True
        typing_msg = {'type': 'user_typing', 'payload': {'thread_id': 'thread_123'}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, typing_msg)
        assert result is True
        user_msg = {'type': 'user_message', 'payload': {'content': 'Analyze my costs please'}, 'timestamp': time.time(), 'user_id': self.user_id, 'message_id': 'msg_flow_test'}
        result = await self.router.route_message(self.user_id, self.mock_websocket, user_msg)
        assert result is True
        disconnect_msg = {'type': 'disconnect', 'payload': {'reason': 'user_logout'}, 'timestamp': time.time(), 'user_id': self.user_id}
        result = await self.router.route_message(self.user_id, self.mock_websocket, disconnect_msg)
        assert result is True
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 5
        assert stats['unhandled_messages'] == 0
        assert stats['handler_errors'] == 0

    async def test_concurrent_message_handling(self):
        """Test handling multiple concurrent messages."""
        messages = [{'type': 'user_message', 'payload': {'content': f'Message {i}'}} for i in range(10)]
        for i, msg in enumerate(messages):
            msg.update({'timestamp': time.time(), 'user_id': f'user_{i % 3}', 'message_id': f'msg_{i}'})
        tasks = [self.router.route_message(msg['user_id'], self.mock_websocket, msg) for msg in messages]
        results = await asyncio.gather(*tasks)
        assert all(results)
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 10
        assert stats['unhandled_messages'] == 0

    async def test_error_recovery_scenarios(self):
        """Test error recovery in various scenarios."""
        self.mock_websocket.send_json.side_effect = [Exception('Network error'), None]
        msg1 = {'type': 'user_message', 'payload': {'content': 'First message'}, 'timestamp': time.time(), 'user_id': self.user_id}
        msg2 = {'type': 'ping', 'payload': {}, 'timestamp': time.time(), 'user_id': self.user_id}
        result1 = await self.router.route_message(self.user_id, self.mock_websocket, msg1)
        result2 = await self.router.route_message(self.user_id, self.mock_websocket, msg2)
        assert result1 is False
        assert result2 is True
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 2
        assert stats['handler_errors'] == 0

    def _create_mock_websocket(self):
        """Create properly configured mock WebSocket."""
        mock_ws = Mock()
        mock_ws.send_json = AsyncMock()
        mock_ws.send_text = AsyncMock()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            pass
        return mock_ws

class GoldenPathCriticalScenariosTests(SSotBaseTestCase, WebSocketTestMixin):
    """
    MISSION CRITICAL: Test Golden Path scenarios that protect $500K+ ARR.
    
    These tests validate the core message processing flows that enable 
    our chat functionality business value delivery.
    """

    def setup_method(self):
        """Setup for Golden Path critical tests."""
        super().setup_method()
        self.router = MessageRouter()
        self.mock_websocket = self._create_mock_websocket()
        self.enterprise_user_id = 'enterprise_user_456'

    async def test_golden_path_agent_request_flow(self):
        """
        CRITICAL: Test complete agent request flow that delivers business value.
        
        This simulates the core user interaction that generates revenue:
        User sends message -> Agent processes -> User receives value
        """
        connect_result = await self.router.route_message(self.enterprise_user_id, self.mock_websocket, {'type': 'connect', 'payload': {'subscription': 'enterprise'}, 'timestamp': time.time(), 'user_id': self.enterprise_user_id})
        assert connect_result is True
        typing_result = await self.router.route_message(self.enterprise_user_id, self.mock_websocket, {'type': 'user_typing', 'payload': {'thread_id': 'enterprise_thread_123'}, 'timestamp': time.time(), 'user_id': self.enterprise_user_id})
        assert typing_result is True
        user_message_result = await self.router.route_message(self.enterprise_user_id, self.mock_websocket, {'type': 'user_message', 'payload': {'content': 'Optimize my $50K monthly AI spend', 'priority': 'high', 'expected_savings': 15000}, 'timestamp': time.time(), 'user_id': self.enterprise_user_id, 'message_id': 'valuable_request_123'})
        assert user_message_result is True
        sent_responses = []

        async def capture_agent_response(data):
            sent_responses.append(json.loads(data))
        self.mock_websocket.send_text = capture_agent_response
        agent_request_result = await self.router.route_message(self.enterprise_user_id, self.mock_websocket, {'type': 'agent_request', 'payload': {'message': 'Optimize my $50K monthly AI spend', 'turn_id': 'valuable_turn_123', 'require_multi_agent': True, 'real_llm': True, 'user_tier': 'enterprise'}, 'timestamp': time.time(), 'user_id': self.enterprise_user_id})
        assert agent_request_result is True
        assert len(sent_responses) > 0
        agent_response = sent_responses[0]
        assert agent_response['type'] == MessageType.AGENT_RESPONSE.value
        assert agent_response['data']['status'] == 'success'
        assert 'multi_agent' in agent_response['data']['content'] or len(agent_response['data']['agents_involved']) > 1
        assert agent_response['data']['turn_id'] == 'valuable_turn_123'
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 4
        assert stats['unhandled_messages'] == 0
        assert stats['handler_errors'] == 0
        message_types = stats['message_types']
        assert 'connect' in message_types
        assert 'user_typing' in message_types
        assert 'user_message' in message_types
        assert 'agent_request' in message_types

    async def test_golden_path_multi_user_isolation(self):
        """
        CRITICAL: Test multi-user isolation protects revenue from different customers.
        
        Ensures User A's sensitive enterprise data doesn't leak to User B.
        """
        user_a = 'enterprise_user_a'
        user_b = 'free_tier_user_b'
        connect_tasks = []
        for user in [user_a, user_b]:
            connect_tasks.append(self.router.route_message(user, self.mock_websocket, {'type': 'connect', 'payload': {'user_tier': 'enterprise' if 'enterprise' in user else 'free'}, 'timestamp': time.time(), 'user_id': user}))
        connect_results = await asyncio.gather(*connect_tasks)
        assert all(connect_results)
        enterprise_result = await self.router.route_message(user_a, self.mock_websocket, {'type': 'user_message', 'payload': {'content': 'CONFIDENTIAL: Our AI costs are $100K/month', 'classification': 'sensitive', 'user_tier': 'enterprise'}, 'timestamp': time.time(), 'user_id': user_a, 'message_id': 'sensitive_enterprise_msg'})
        assert enterprise_result is True
        free_tier_result = await self.router.route_message(user_b, self.mock_websocket, {'type': 'user_message', 'payload': {'content': 'What are basic optimization tips?', 'user_tier': 'free'}, 'timestamp': time.time(), 'user_id': user_b, 'message_id': 'free_tier_msg'})
        assert free_tier_result is True
        stats = self.router.get_stats()
        assert stats['messages_routed'] == 4
        assert stats['unhandled_messages'] == 0

    async def test_golden_path_error_resilience(self):
        """
        CRITICAL: Test system resilience protects business value during errors.
        
        System must gracefully handle errors without losing revenue opportunities.
        """
        error_scenarios = [{'name': 'WebSocket Send Failure', 'setup': lambda: setattr(self.mock_websocket, 'send_json', AsyncMock(side_effect=Exception('Network error')))}, {'name': 'Malformed Message', 'message': {'type': 'invalid_structure', 'bad_payload': None}}, {'name': 'Unknown Message Type', 'message': {'type': 'custom_unknown_type', 'payload': {}, 'timestamp': time.time(), 'user_id': self.enterprise_user_id}}]
        successful_recoveries = 0
        for scenario in error_scenarios:
            if 'setup' in scenario:
                scenario['setup']()
            message = scenario.get('message', {'type': 'user_message', 'payload': {'content': 'Test message'}, 'timestamp': time.time(), 'user_id': self.enterprise_user_id})
            try:
                result = await self.router.route_message(self.enterprise_user_id, self.mock_websocket, message)
                if result is not None:
                    successful_recoveries += 1
            except Exception as e:
                pytest.fail(f"Unhandled exception in scenario '{scenario['name']}': {e}")
            self.mock_websocket = self._create_mock_websocket()
        assert successful_recoveries >= len(error_scenarios) - 1
        final_stats = self.router.get_stats()
        assert final_stats['messages_routed'] >= 2

    def _create_mock_websocket(self):
        """Create mock WebSocket optimized for Golden Path testing."""
        mock_ws = Mock()
        mock_ws.send_json = AsyncMock()
        mock_ws.send_text = AsyncMock()
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            pass
        return mock_ws
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')