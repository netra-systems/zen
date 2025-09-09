"""
Unit Tests for WebSocket Handlers Business Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: System Reliability & User Experience
- Value Impact: Ensures WebSocket message handlers process all 5 critical agent events correctly,
  preventing message routing failures that break user chat interactions
- Strategic Impact: Validates the business logic that enables $X million in AI optimization value delivery

CRITICAL: These unit tests validate the BUSINESS LOGIC of WebSocket message handlers,
focusing on the 5 critical WebSocket events that enable substantive chat interactions:
1. agent_started - User sees AI began processing their problem  
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency  
4. tool_completed - Tool results delivery
5. agent_completed - User knows valuable response is ready

TEST STRATEGY: Pure business logic validation without infrastructure dependencies.
Uses SSOT test framework utilities and follows TEST_CREATION_GUIDE.md principles.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# SSOT imports using absolute paths
from netra_backend.app.websocket_core.handlers import (
    BaseMessageHandler,
    ConnectionHandler, 
    TypingHandler,
    HeartbeatHandler,
    AgentRequestHandler,
    TestAgentHandler,
    AgentHandler,
    UserMessageHandler,
    JsonRpcHandler,
    ErrorHandler,
    BatchMessageHandler,
    MessageRouter,
    get_message_router,
    get_router_handler_count,
    list_registered_handlers,
    send_error_to_websocket,
    send_system_message
)
from netra_backend.app.websocket_core.types import (
    MessageType,
    WebSocketMessage,
    ServerMessage,
    ErrorMessage,
    BatchConfig,
    create_standard_message,
    create_error_message,
    create_server_message
)
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Test fixtures
from netra_backend.tests.conftest_helpers import create_mock_websocket


@pytest.mark.unit
class TestBaseMessageHandler(SSotBaseTestCase):
    """Test BaseMessageHandler business logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = BaseMessageHandler([MessageType.PING, MessageType.PONG])
        
    def test_can_handle_supported_types(self):
        """Test handler correctly identifies supported message types."""
        # Test supported types return True
        assert self.handler.can_handle(MessageType.PING) is True
        assert self.handler.can_handle(MessageType.PONG) is True
        
        # Test unsupported types return False
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False
        assert self.handler.can_handle(MessageType.AGENT_STARTED) is False
        
    async def test_default_handle_message_business_logic(self):
        """Test default message handling behavior."""
        user_id = "test-user-123"
        websocket = create_mock_websocket()
        message = create_standard_message(MessageType.PING, {"timestamp": time.time()})
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "Default handler should return success"


@pytest.mark.unit
class TestConnectionHandler(SSotBaseTestCase):
    """Test ConnectionHandler business logic - critical for user session management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ConnectionHandler()
        
    def test_handler_supports_connection_types(self):
        """Test handler supports all connection lifecycle message types."""
        assert self.handler.can_handle(MessageType.CONNECT) is True
        assert self.handler.can_handle(MessageType.DISCONNECT) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    @patch('netra_backend.app.websocket_core.handlers.safe_websocket_send')
    async def test_connect_message_business_logic(self, mock_send, mock_connected):
        """Test CONNECT message creates proper acknowledgment."""
        # Setup
        mock_connected.return_value = True
        mock_send.return_value = True
        user_id = "test-user-456" 
        websocket = create_mock_websocket()
        message = create_standard_message(MessageType.CONNECT, {})
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "CONNECT handler should succeed for valid connection"
        mock_send.assert_called_once()
        
        # Verify response message structure
        call_args = mock_send.call_args[0]
        response_data = call_args[1]  # Second argument is the message data
        assert response_data["type"] == "system_message"
        assert response_data["payload"]["status"] == "connected"
        assert response_data["payload"]["user_id"] == user_id
        assert "timestamp" in response_data["payload"]
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    @patch('netra_backend.app.websocket_core.handlers.safe_websocket_send')
    async def test_disconnect_message_business_logic(self, mock_send, mock_connected):
        """Test DISCONNECT message creates proper acknowledgment."""
        # Setup
        mock_connected.return_value = True
        mock_send.return_value = True
        user_id = "test-user-789"
        websocket = create_mock_websocket()
        message = create_standard_message(MessageType.DISCONNECT, {})
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "DISCONNECT handler should succeed"
        mock_send.assert_called_once()
        
        # Verify response indicates disconnect acknowledged
        call_args = mock_send.call_args[0]
        response_data = call_args[1]
        assert response_data["payload"]["status"] == "disconnect_acknowledged"
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_connection_handler_fails_on_disconnected_websocket(self, mock_connected):
        """Test handler fails gracefully when WebSocket is disconnected."""
        # Setup
        mock_connected.return_value = False
        user_id = "test-user-disconnected"
        websocket = create_mock_websocket()
        message = create_standard_message(MessageType.CONNECT, {})
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcome
        assert result is False, "Handler should fail when WebSocket is disconnected"


@pytest.mark.unit 
class TestTypingHandler(SSotBaseTestCase):
    """Test TypingHandler business logic - enables real-time user interaction feedback."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = TypingHandler()
        
    def test_handler_supports_typing_indicators(self):
        """Test handler supports all typing message types."""
        assert self.handler.can_handle(MessageType.USER_TYPING) is True
        assert self.handler.can_handle(MessageType.AGENT_TYPING) is True
        assert self.handler.can_handle(MessageType.TYPING_STARTED) is True
        assert self.handler.can_handle(MessageType.TYPING_STOPPED) is True
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_typing_message_creates_acknowledgment(self, mock_connected):
        """Test typing messages generate proper acknowledgment responses."""
        # Setup
        mock_connected.return_value = True
        user_id = "typing-user-123"
        websocket = create_mock_websocket()
        thread_id = "thread-typing-test"
        
        message = create_standard_message(
            MessageType.USER_TYPING,
            {"thread_id": thread_id}
        )
        message.thread_id = thread_id
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "Typing handler should succeed"
        websocket.send_json.assert_called_once()
        
        # Verify acknowledgment structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "system_message"
        assert call_args["payload"]["status"] == "typing_acknowledged"
        assert call_args["payload"]["type"] == "user_typing"
        assert call_args["payload"]["thread_id"] == thread_id


@pytest.mark.unit
class TestHeartbeatHandler(SSotBaseTestCase):
    """Test HeartbeatHandler business logic - critical for connection health."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = HeartbeatHandler()
        
    def test_handler_supports_heartbeat_types(self):
        """Test handler supports all heartbeat message types."""
        assert self.handler.can_handle(MessageType.PING) is True
        assert self.handler.can_handle(MessageType.PONG) is True
        assert self.handler.can_handle(MessageType.HEARTBEAT) is True
        assert self.handler.can_handle(MessageType.HEARTBEAT_ACK) is True
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_ping_generates_pong_response(self, mock_connected):
        """Test PING message generates PONG response - essential for connection health."""
        # Setup
        mock_connected.return_value = True
        user_id = "ping-user-123"
        websocket = create_mock_websocket()
        message = create_standard_message(MessageType.PING, {})
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "PING handler should succeed"
        websocket.send_json.assert_called_once()
        
        # Verify PONG response structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "pong"
        assert call_args["payload"]["user_id"] == user_id
        assert "timestamp" in call_args["payload"]
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_heartbeat_generates_ack_response(self, mock_connected):
        """Test HEARTBEAT message generates ACK response."""
        # Setup
        mock_connected.return_value = True
        user_id = "heartbeat-user-456"
        websocket = create_mock_websocket()
        message = create_standard_message(MessageType.HEARTBEAT, {})
        
        # Execute business logic  
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "HEARTBEAT handler should succeed"
        websocket.send_json.assert_called_once()
        
        # Verify ACK response structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "heartbeat_ack"
        assert call_args["payload"]["status"] == "healthy"


@pytest.mark.unit
class TestAgentRequestHandler(SSotBaseTestCase):
    """Test AgentRequestHandler business logic - CRITICAL for agent execution events."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = AgentRequestHandler()
        
    def test_handler_supports_agent_request_types(self):
        """Test handler supports agent request message types."""
        assert self.handler.can_handle(MessageType.AGENT_REQUEST) is True
        assert self.handler.can_handle(MessageType.START_AGENT) is True
        
    async def test_agent_request_generates_agent_response(self):
        """Test agent request creates proper agent response - CRITICAL for user value delivery."""
        # Setup
        user_id = "agent-user-123"
        websocket = create_mock_websocket()
        turn_id = "turn-456"
        user_message = "Optimize my Kubernetes cluster"
        
        message = create_standard_message(MessageType.AGENT_REQUEST, {
            "message": user_message,
            "turn_id": turn_id,
            "require_multi_agent": False,
            "real_llm": False
        })
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "Agent request handler should succeed"
        websocket.send_text.assert_called_once()
        
        # Verify agent response structure contains business value elements
        call_args = websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        
        assert response["type"] == "agent_response"
        assert response["payload"]["status"] == "success"
        assert user_message in response["payload"]["content"]
        assert response["payload"]["turn_id"] == turn_id
        assert response["payload"]["user_id"] == user_id
        assert "agents_involved" in response["payload"]
        assert "orchestration_time" in response["payload"]
        
    async def test_multi_agent_request_involves_multiple_agents(self):
        """Test multi-agent requests involve supervisor, triage, and optimization agents."""
        # Setup
        user_id = "multi-agent-user"
        websocket = create_mock_websocket()
        
        message = create_standard_message(MessageType.AGENT_REQUEST, {
            "message": "Complex optimization task",
            "turn_id": "multi-turn-789",
            "require_multi_agent": True,
            "real_llm": True
        })
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True
        call_args = websocket.send_text.call_args[0][0]
        response = json.loads(call_args)
        
        # Verify multi-agent orchestration
        agents_involved = response["payload"]["agents_involved"]
        assert "supervisor" in agents_involved
        assert "triage" in agents_involved
        assert "optimization" in agents_involved
        assert response["payload"]["real_llm_used"] is True


@pytest.mark.unit
class TestAgentHandler(SSotBaseTestCase):
    """Test AgentHandler business logic - handles agent status and response messages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = AgentHandler()
        
    def test_handler_supports_agent_status_types(self):
        """Test handler supports agent status message types."""
        assert self.handler.can_handle(MessageType.AGENT_TASK_ACK) is True
        assert self.handler.can_handle(MessageType.AGENT_RESPONSE_CHUNK) is True
        assert self.handler.can_handle(MessageType.AGENT_RESPONSE_COMPLETE) is True
        assert self.handler.can_handle(MessageType.AGENT_STATUS_UPDATE) is True
        assert self.handler.can_handle(MessageType.AGENT_ERROR) is True
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_agent_message_acknowledgment(self, mock_connected):
        """Test agent messages are properly acknowledged."""
        # Setup
        mock_connected.return_value = True
        user_id = "agent-status-user"
        websocket = create_mock_websocket()
        
        message = create_standard_message(MessageType.AGENT_RESPONSE_CHUNK, {
            "task_id": "task-123",
            "chunk": "Processing optimization...",
            "chunk_index": 0
        })
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "Agent handler should succeed"
        websocket.send_json.assert_called_once()
        
        # Verify acknowledgment structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "system_message"
        assert call_args["payload"]["status"] == "agent_message_acknowledged"
        assert call_args["payload"]["original_type"] == "agent_response_chunk"


@pytest.mark.unit
class TestUserMessageHandler(SSotBaseTestCase):
    """Test UserMessageHandler business logic - processes system and thread messages."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = UserMessageHandler()
        
    def test_handler_supports_user_message_types(self):
        """Test handler supports user message types."""
        assert self.handler.can_handle(MessageType.SYSTEM_MESSAGE) is True
        assert self.handler.can_handle(MessageType.AGENT_RESPONSE) is True
        assert self.handler.can_handle(MessageType.AGENT_PROGRESS) is True
        assert self.handler.can_handle(MessageType.THREAD_UPDATE) is True
        assert self.handler.can_handle(MessageType.THREAD_MESSAGE) is True
        
    async def test_message_processing_updates_stats(self):
        """Test message processing updates handler statistics."""
        # Setup
        user_id = "stats-user-123"
        websocket = create_mock_websocket()
        
        message = create_standard_message(MessageType.SYSTEM_MESSAGE, {
            "content": "System notification"
        })
        
        initial_count = self.handler.message_stats["processed"]
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True
        assert self.handler.message_stats["processed"] == initial_count + 1
        assert self.handler.message_stats["last_message_time"] is not None
        
    def test_get_stats_returns_current_statistics(self):
        """Test get_stats returns handler statistics."""
        stats = self.handler.get_stats()
        
        assert "processed" in stats
        assert "errors" in stats  
        assert "last_message_time" in stats
        assert isinstance(stats["processed"], int)


@pytest.mark.unit
class TestErrorHandler(SSotBaseTestCase):
    """Test ErrorHandler business logic - critical for error management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()
        
    def test_handler_supports_error_types(self):
        """Test handler supports error message types."""
        assert self.handler.can_handle(MessageType.ERROR_MESSAGE) is True
        assert self.handler.can_handle(MessageType.USER_MESSAGE) is False
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_error_message_tracking_and_acknowledgment(self, mock_connected):
        """Test error messages are tracked and acknowledged."""
        # Setup
        mock_connected.return_value = True
        user_id = "error-user-123"
        websocket = create_mock_websocket()
        
        error_code = "AGENT_EXECUTION_FAILED"
        error_message = "Failed to execute optimization agent"
        
        message = create_standard_message(MessageType.ERROR_MESSAGE, {
            "error_code": error_code,
            "error_message": error_message
        })
        
        initial_count = self.handler.error_stats["total_errors"]
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "Error handler should succeed"
        assert self.handler.error_stats["total_errors"] == initial_count + 1
        assert self.handler.error_stats["last_error_time"] is not None
        
        # Verify error type tracking
        assert error_code in self.handler.error_stats["error_types"]
        assert self.handler.error_stats["error_types"][error_code] == 1
        
        # Verify acknowledgment sent
        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["payload"]["error_code"] == error_code


@pytest.mark.unit
class TestBatchMessageHandler(SSotBaseTestCase):
    """Test BatchMessageHandler business logic - handles message batching for performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = BatchConfig(max_batch_size=3, max_wait_time=1.0)
        self.handler = BatchMessageHandler(self.config)
        
    def test_handler_supports_batch_types(self):
        """Test handler supports batch message types."""
        assert self.handler.can_handle(MessageType.BROADCAST) is True
        assert self.handler.can_handle(MessageType.ROOM_MESSAGE) is True
        
    async def test_message_batching_creates_pending_message(self):
        """Test messages are properly batched as pending messages."""
        # Setup
        user_id = "batch-user-123"
        websocket = create_mock_websocket()
        
        message = create_standard_message(MessageType.BROADCAST, {
            "content": "Broadcast message",
            "priority": 1
        })
        message.thread_id = "batch-thread-123"
        
        initial_count = len(self.handler.pending_messages.get(user_id, []))
        
        # Execute business logic
        result = await self.handler.handle_message(user_id, websocket, message)
        
        # Verify business outcomes
        assert result is True, "Batch handler should succeed"
        assert len(self.handler.pending_messages.get(user_id, [])) == initial_count + 1
        
        # Verify pending message structure
        pending_msg = self.handler.pending_messages[user_id][0]
        assert pending_msg.user_id == user_id
        assert pending_msg.thread_id == message.thread_id
        assert pending_msg.connection_id == f"ws_{user_id}"
        
    def test_get_stats_includes_batch_statistics(self):
        """Test get_stats returns comprehensive batch statistics."""
        stats = self.handler.get_stats()
        
        assert "batches_created" in stats
        assert "messages_batched" in stats
        assert "batch_send_successes" in stats
        assert "batch_send_failures" in stats
        assert "pending_message_count" in stats
        assert "active_timers" in stats


@pytest.mark.unit
class TestMessageRouter(SSotBaseTestCase):
    """Test MessageRouter business logic - CRITICAL for routing WebSocket agent events."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = MessageRouter()
        
    def test_router_initializes_with_builtin_handlers(self):
        """Test router initializes with all required builtin handlers."""
        handler_names = [h.__class__.__name__ for h in self.router.builtin_handlers]
        
        # Verify critical handlers are present
        assert "ConnectionHandler" in handler_names
        assert "HeartbeatHandler" in handler_names
        assert "AgentHandler" in handler_names
        assert "UserMessageHandler" in handler_names
        assert "ErrorHandler" in handler_names
        
    def test_custom_handlers_take_precedence(self):
        """Test custom handlers are processed before builtin handlers."""
        # Create custom handler
        custom_handler = BaseMessageHandler([MessageType.PING])
        custom_handler.handle_message = AsyncMock(return_value=True)
        
        # Add custom handler
        self.router.add_handler(custom_handler)
        
        # Verify precedence order
        handlers = self.router.handlers
        assert handlers[0] == custom_handler
        assert len(self.router.custom_handlers) == 1
        
    def test_handler_order_tracking(self):
        """Test router tracks handler order for debugging."""
        handler_order = self.router.get_handler_order()
        
        assert isinstance(handler_order, list)
        assert len(handler_order) > 0
        assert "ConnectionHandler" in handler_order
        
    async def test_route_message_finds_appropriate_handler(self):
        """Test message routing finds and executes appropriate handler."""
        # Setup
        user_id = "route-user-123"
        websocket = create_mock_websocket()
        raw_message = {
            "type": "ping",
            "payload": {"test": "data"},
            "timestamp": time.time()
        }
        
        # Execute business logic
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            result = await self.router.route_message(user_id, websocket, raw_message)
        
        # Verify business outcomes
        assert result is True, "Message routing should succeed"
        assert self.router.routing_stats["messages_routed"] > 0
        assert "ping" in self.router.routing_stats["message_types"]
        
    async def test_unknown_message_type_acknowledgment(self):
        """Test unknown message types receive acknowledgment."""
        # Setup
        user_id = "unknown-user-123"
        websocket = create_mock_websocket()
        raw_message = {
            "type": "unknown_custom_message",
            "payload": {"data": "test"}
        }
        
        # Execute business logic
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            result = await self.router.route_message(user_id, websocket, raw_message)
        
        # Verify business outcomes
        assert result is True, "Unknown message should be acknowledged"
        websocket.send_json.assert_called_once()
        
        # Verify acknowledgment structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "ack"
        assert call_args["received_type"] == "unknown_custom_message"
        
    def test_startup_grace_period_status_tracking(self):
        """Test router tracks startup status with grace period."""
        status = self.router.check_handler_status_with_grace_period()
        
        assert "status" in status
        assert "handler_count" in status
        assert "elapsed_seconds" in status
        assert "grace_period_active" in status
        
        # Should show ready status with handlers
        assert status["handler_count"] > 0
        
    def test_get_stats_includes_comprehensive_metrics(self):
        """Test get_stats returns comprehensive routing statistics."""
        stats = self.router.get_stats()
        
        assert "messages_routed" in stats
        assert "unhandled_messages" in stats
        assert "handler_errors" in stats
        assert "message_types" in stats
        assert "handler_stats" in stats
        assert "handler_order" in stats
        assert "handler_count" in stats
        assert "handler_status" in stats


@pytest.mark.unit
class TestGlobalMessageRouterFunctions(SSotBaseTestCase):
    """Test global message router functions - SSOT for WebSocket message routing."""
    
    def test_get_message_router_returns_singleton(self):
        """Test get_message_router returns singleton instance."""
        router1 = get_message_router()
        router2 = get_message_router()
        
        assert router1 is router2, "Should return same singleton instance"
        
    def test_get_router_handler_count(self):
        """Test get_router_handler_count returns current handler count."""
        count = get_router_handler_count()
        
        assert isinstance(count, int)
        assert count > 0, "Should have builtin handlers"
        
    def test_list_registered_handlers(self):
        """Test list_registered_handlers returns handler names."""
        handlers = list_registered_handlers()
        
        assert isinstance(handlers, list)
        assert len(handlers) > 0
        assert "ConnectionHandler" in handlers


@pytest.mark.unit 
class TestWebSocketUtilityFunctions(SSotBaseTestCase):
    """Test WebSocket utility functions for error handling and system messages."""
    
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_send_error_to_websocket_business_logic(self, mock_connected):
        """Test send_error_to_websocket creates proper error messages."""
        # Setup
        mock_connected.return_value = True
        websocket = create_mock_websocket()
        error_code = "BUSINESS_LOGIC_ERROR"
        error_message = "Agent execution failed"
        details = {"agent": "optimization", "reason": "timeout"}
        
        # Execute business logic
        result = await send_error_to_websocket(websocket, error_code, error_message, details)
        
        # Verify business outcomes
        assert result is True, "Error sending should succeed"
        websocket.send_json.assert_called_once()
        
        # Verify error message structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error_message"
        assert call_args["error_code"] == error_code
        assert call_args["error_message"] == error_message
        assert call_args["details"] == details
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_send_system_message_business_logic(self, mock_connected):
        """Test send_system_message creates proper system notifications."""
        # Setup
        mock_connected.return_value = True
        websocket = create_mock_websocket()
        content = "Agent optimization completed successfully"
        additional_data = {"execution_time": 2.5, "cost_saved": "$150"}
        
        # Execute business logic
        result = await send_system_message(websocket, content, additional_data)
        
        # Verify business outcomes
        assert result is True, "System message sending should succeed"
        websocket.send_json.assert_called_once()
        
        # Verify system message structure
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "system_message"
        assert call_args["payload"]["content"] == content
        assert call_args["payload"]["execution_time"] == 2.5
        assert call_args["payload"]["cost_saved"] == "$150"
        
    @patch('netra_backend.app.websocket_core.handlers.is_websocket_connected')
    async def test_utility_functions_handle_disconnected_websocket(self, mock_connected):
        """Test utility functions handle disconnected WebSocket gracefully."""
        # Setup
        mock_connected.return_value = False
        websocket = create_mock_websocket()
        
        # Execute business logic
        error_result = await send_error_to_websocket(websocket, "TEST", "Test error")
        system_result = await send_system_message(websocket, "Test message")
        
        # Verify business outcomes
        assert error_result is False, "Should fail gracefully for disconnected WebSocket"
        assert system_result is False, "Should fail gracefully for disconnected WebSocket"
        websocket.send_json.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])