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

from netra_backend.app.websocket_core.handlers import (
    # Core message handlers
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
    # Message protocol
    MessageHandler,
    # Utility functions
    send_error_to_websocket,
    send_system_message,
    get_message_router,
    get_router_handler_count,
    list_registered_handlers
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
from netra_backend.app.websocket_core.utils import is_websocket_connected
from test_framework.base import BaseUnitTest


class TestConnectionHandlerBusinessLogic(BaseUnitTest):
    """Test ConnectionHandler business logic for user connection lifecycle."""
    
    def setUp(self):
        """Set up ConnectionHandler for testing."""
        self.handler = ConnectionHandler()
        
        # Create mock WebSocket with proper state handling
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = "websocket_mock"  # For test detection
        self.mock_websocket.send_json = AsyncMock()
        
        # Mock is_websocket_connected to return True for tests
        self.websocket_connected_patcher = patch(
            'netra_backend.app.websocket_core.handlers.is_websocket_connected', 
            return_value=True
        )
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_connection_handler_supports_required_message_types(self):
        """Test ConnectionHandler supports CONNECT and DISCONNECT message types."""
        # Business value: Connection lifecycle management is fundamental to chat
        supported_types = self.handler.supported_types
        
        assert MessageType.CONNECT in supported_types, "Must support CONNECT messages"
        assert MessageType.DISCONNECT in supported_types, "Must support DISCONNECT messages"
        assert len(supported_types) == 2, "Should only support connection-related messages"

    @pytest.mark.unit  
    def test_connection_handler_can_handle_connect_message(self):
        """Test ConnectionHandler correctly identifies CONNECT messages."""
        # Business value: Proper message routing ensures connection events are handled
        can_handle_connect = self.handler.can_handle(MessageType.CONNECT)
        can_handle_disconnect = self.handler.can_handle(MessageType.DISCONNECT)
        cannot_handle_other = self.handler.can_handle(MessageType.USER_MESSAGE)
        
        assert can_handle_connect is True, "Must handle CONNECT messages"
        assert can_handle_disconnect is True, "Must handle DISCONNECT messages" 
        assert cannot_handle_other is False, "Must not handle non-connection messages"

    @pytest.mark.unit
    async def test_connection_handler_processes_connect_message_successfully(self):
        """Test ConnectionHandler processes CONNECT message with proper acknowledgment."""
        # Business value: Users must receive connection confirmation for chat to work
        user_id = "test-user-123"
        connect_message = WebSocketMessage(
            type=MessageType.CONNECT,
            payload={"status": "connecting"},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute connection handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, connect_message)
        
        # Validate business logic
        assert result is True, "CONNECT message handling must succeed"
        
        # Verify acknowledgment was sent
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "system_message", "Must send system message response"
        assert call_args["payload"]["status"] == "connected", "Must confirm connection status"
        assert call_args["payload"]["user_id"] == user_id, "Must include user ID in response"
        assert "timestamp" in call_args["payload"], "Must include timestamp"

    @pytest.mark.unit
    async def test_connection_handler_processes_disconnect_message_successfully(self):
        """Test ConnectionHandler processes DISCONNECT message with proper acknowledgment."""
        # Business value: Clean disconnect handling prevents connection leaks and improves UX
        user_id = "test-user-456"
        disconnect_message = WebSocketMessage(
            type=MessageType.DISCONNECT,
            payload={"reason": "user_initiated"},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute disconnect handling  
        result = await self.handler.handle_message(user_id, self.mock_websocket, disconnect_message)
        
        # Validate business logic
        assert result is True, "DISCONNECT message handling must succeed"
        
        # Verify acknowledgment was sent
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "system_message", "Must send system message response"
        assert call_args["payload"]["status"] == "disconnect_acknowledged", "Must acknowledge disconnect"
        assert call_args["payload"]["user_id"] == user_id, "Must include user ID in response"

    @pytest.mark.unit
    async def test_connection_handler_fails_on_websocket_disconnected(self):
        """Test ConnectionHandler fails properly when WebSocket is disconnected."""
        # Business value: Fail-fast behavior prevents silent failures and improves debugging
        self.websocket_connected_patcher.stop()  # Remove the patch
        
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=False):
            user_id = "test-user-789"
            connect_message = WebSocketMessage(
                type=MessageType.CONNECT,
                payload={"status": "connecting"},
                timestamp=time.time(),
                user_id=user_id
            )
            
            # Execute connection handling on disconnected WebSocket
            result = await self.handler.handle_message(user_id, self.mock_websocket, connect_message)
            
            # Validate failure handling
            assert result is False, "Must fail when WebSocket is disconnected"
            
            # Verify no message was sent to disconnected WebSocket
            self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.unit
    async def test_connection_handler_handles_websocket_send_failure(self):
        """Test ConnectionHandler handles WebSocket send failures gracefully."""
        # Business value: Robust error handling prevents connection handler crashes
        user_id = "test-user-send-fail"
        connect_message = WebSocketMessage(
            type=MessageType.CONNECT,
            payload={"status": "connecting"},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Mock WebSocket send to fail
        with patch('netra_backend.app.websocket_core.handlers.safe_websocket_send', return_value=False):
            result = await self.handler.handle_message(user_id, self.mock_websocket, connect_message)
            
            # Validate failure is properly reported
            assert result is False, "Must return False when WebSocket send fails"

    @pytest.mark.unit
    async def test_connection_handler_handles_unexpected_message_type(self):
        """Test ConnectionHandler rejects unsupported message types."""
        # Business value: Message type validation prevents handler confusion
        user_id = "test-user-invalid"
        invalid_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,  # Not supported by ConnectionHandler
            payload={"text": "Hello"},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute with unsupported message type
        result = await self.handler.handle_message(user_id, self.mock_websocket, invalid_message)
        
        # Validate rejection
        assert result is False, "Must reject unsupported message types"
        
        # Verify no response was sent for invalid message
        self.mock_websocket.send_json.assert_not_called()


class TestTypingHandlerBusinessLogic(BaseUnitTest):
    """Test TypingHandler business logic for real-time typing indicators."""
    
    def setUp(self):
        """Set up TypingHandler for testing."""
        self.handler = TypingHandler()
        
        # Create mock WebSocket
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = "websocket_mock"
        self.mock_websocket.send_json = AsyncMock()
        
        # Mock is_websocket_connected
        self.websocket_connected_patcher = patch(
            'netra_backend.app.websocket_core.handlers.is_websocket_connected',
            return_value=True
        )
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_typing_handler_supports_all_typing_message_types(self):
        """Test TypingHandler supports all required typing indicator message types."""
        # Business value: Typing indicators improve chat UX by showing activity
        supported_types = self.handler.supported_types
        
        expected_types = [
            MessageType.USER_TYPING,
            MessageType.AGENT_TYPING, 
            MessageType.TYPING_STARTED,
            MessageType.TYPING_STOPPED
        ]
        
        for message_type in expected_types:
            assert message_type in supported_types, f"Must support {message_type} for typing indicators"

    @pytest.mark.unit
    async def test_typing_handler_processes_user_typing_with_thread_context(self):
        """Test TypingHandler processes USER_TYPING with proper thread context."""
        # Business value: Thread-aware typing indicators maintain conversation context
        user_id = "test-user-typing"
        thread_id = "thread-123" 
        
        typing_message = WebSocketMessage(
            type=MessageType.USER_TYPING,
            payload={"thread_id": thread_id, "status": "typing"},
            timestamp=time.time(),
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Execute typing handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, typing_message)
        
        # Validate business logic
        assert result is True, "USER_TYPING message handling must succeed"
        
        # Verify acknowledgment includes thread context
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "system_message", "Must send system message response"
        assert call_args["payload"]["status"] == "typing_acknowledged", "Must acknowledge typing"
        assert call_args["payload"]["thread_id"] == thread_id, "Must preserve thread context"
        assert call_args["payload"]["user_id"] == user_id, "Must include user ID"

    @pytest.mark.unit
    async def test_typing_handler_processes_agent_typing_indicator(self):
        """Test TypingHandler processes AGENT_TYPING for AI response indicators."""
        # Business value: Agent typing indicators show AI is processing user requests
        user_id = "test-user-agent-typing"
        thread_id = "thread-agent-456"
        
        agent_typing_message = WebSocketMessage(
            type=MessageType.AGENT_TYPING,
            payload={"thread_id": thread_id, "agent": "optimization_agent"},
            timestamp=time.time(),
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Execute agent typing handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, agent_typing_message)
        
        # Validate business logic
        assert result is True, "AGENT_TYPING message handling must succeed"
        
        # Verify proper acknowledgment
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["payload"]["type"] == "agent_typing", "Must acknowledge agent typing"
        assert call_args["payload"]["thread_id"] == thread_id, "Must preserve thread context"

    @pytest.mark.unit
    async def test_typing_handler_extracts_thread_id_from_multiple_sources(self):
        """Test TypingHandler can extract thread_id from message or payload."""
        # Business value: Flexible thread_id extraction ensures typing works across different message formats
        user_id = "test-user-flexible"
        thread_id_in_payload = "thread-payload-789"
        
        # Test with thread_id in payload only
        typing_message = WebSocketMessage(
            type=MessageType.TYPING_STARTED,
            payload={"thread_id": thread_id_in_payload, "text": "Starting to type..."},
            timestamp=time.time(),
            user_id=user_id,
            thread_id=None  # Not in message level
        )
        
        result = await self.handler.handle_message(user_id, self.mock_websocket, typing_message)
        
        assert result is True, "Must handle thread_id in payload"
        
        # Verify thread_id was extracted from payload
        call_args = self.mock_websocket.send_json.call_args[0][0]
        assert call_args["payload"]["thread_id"] == thread_id_in_payload, "Must extract thread_id from payload"


class TestHeartbeatHandlerBusinessLogic(BaseUnitTest):
    """Test HeartbeatHandler business logic for connection health monitoring."""
    
    def setUp(self):
        """Set up HeartbeatHandler for testing."""
        self.handler = HeartbeatHandler()
        
        # Create mock WebSocket
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = "websocket_mock"
        self.mock_websocket.send_json = AsyncMock()
        
        # Mock is_websocket_connected
        self.websocket_connected_patcher = patch(
            'netra_backend.app.websocket_core.handlers.is_websocket_connected',
            return_value=True
        )
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_heartbeat_handler_supports_all_heartbeat_message_types(self):
        """Test HeartbeatHandler supports all connection health message types."""
        # Business value: Comprehensive heartbeat support prevents connection drops
        supported_types = self.handler.supported_types
        
        expected_types = [
            MessageType.PING,
            MessageType.PONG,
            MessageType.HEARTBEAT,
            MessageType.HEARTBEAT_ACK
        ]
        
        for message_type in expected_types:
            assert message_type in supported_types, f"Must support {message_type} for connection health"

    @pytest.mark.unit
    async def test_heartbeat_handler_responds_to_ping_with_pong(self):
        """Test HeartbeatHandler responds to PING with PONG message."""
        # Business value: Ping/pong keeps connections alive and detects network issues
        user_id = "test-user-ping"
        
        ping_message = WebSocketMessage(
            type=MessageType.PING,
            payload={"client_time": time.time()},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute ping handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, ping_message)
        
        # Validate business logic
        assert result is True, "PING message handling must succeed"
        
        # Verify PONG response
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "pong", "Must respond to PING with PONG"
        assert call_args["payload"]["user_id"] == user_id, "Must include user ID in PONG"
        assert "timestamp" in call_args["payload"], "Must include server timestamp"

    @pytest.mark.unit
    async def test_heartbeat_handler_responds_to_heartbeat_with_ack(self):
        """Test HeartbeatHandler responds to HEARTBEAT with HEARTBEAT_ACK."""
        # Business value: Heartbeat mechanism ensures connection health monitoring
        user_id = "test-user-heartbeat"
        
        heartbeat_message = WebSocketMessage(
            type=MessageType.HEARTBEAT,
            payload={"client_health": "ok"},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute heartbeat handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, heartbeat_message)
        
        # Validate business logic
        assert result is True, "HEARTBEAT message handling must succeed"
        
        # Verify HEARTBEAT_ACK response
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "heartbeat_ack", "Must respond to HEARTBEAT with HEARTBEAT_ACK"
        assert call_args["payload"]["status"] == "healthy", "Must confirm server health"
        assert "timestamp" in call_args["payload"], "Must include server timestamp"

    @pytest.mark.unit
    async def test_heartbeat_handler_acknowledges_pong_silently(self):
        """Test HeartbeatHandler acknowledges PONG without response."""
        # Business value: PONG acknowledgment completes ping/pong cycle without extra traffic
        user_id = "test-user-pong"
        
        pong_message = WebSocketMessage(
            type=MessageType.PONG,
            payload={"client_response_time": 0.05},
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute pong handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, pong_message)
        
        # Validate silent acknowledgment
        assert result is True, "PONG message handling must succeed"
        
        # Verify no response is sent for PONG (silent acknowledgment)
        self.mock_websocket.send_json.assert_not_called()

    @pytest.mark.unit
    async def test_heartbeat_handler_handles_disconnected_websocket(self):
        """Test HeartbeatHandler fails gracefully when WebSocket is disconnected."""
        # Business value: Graceful failure prevents handler crashes on connection loss
        self.websocket_connected_patcher.stop()
        
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=False):
            user_id = "test-user-disconnected"
            
            ping_message = WebSocketMessage(
                type=MessageType.PING,
                payload={},
                timestamp=time.time(),
                user_id=user_id
            )
            
            # Execute on disconnected WebSocket
            result = await self.handler.handle_message(user_id, self.mock_websocket, ping_message)
            
            # Validate failure handling
            assert result is False, "Must fail when WebSocket is disconnected"


class TestMessageRouterBusinessLogic(BaseUnitTest):
    """Test MessageRouter business logic for message routing and handler management."""
    
    def setUp(self):
        """Set up MessageRouter for testing."""
        self.router = MessageRouter()
        
        # Create mock WebSocket
        self.mock_websocket = Mock()
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = "websocket_mock"
        self.mock_websocket.send_json = AsyncMock()
        
        # Mock is_websocket_connected
        self.websocket_connected_patcher = patch(
            'netra_backend.app.websocket_core.handlers.is_websocket_connected',
            return_value=True
        )
        self.websocket_connected_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.websocket_connected_patcher.stop()

    @pytest.mark.unit
    def test_message_router_initializes_with_built_in_handlers(self):
        """Test MessageRouter initializes with all required built-in handlers."""
        # Business value: Built-in handlers ensure core WebSocket functionality works out-of-box
        handler_names = [handler.__class__.__name__ for handler in self.router.builtin_handlers]
        
        expected_handlers = [
            "ConnectionHandler",
            "TypingHandler", 
            "HeartbeatHandler",
            "AgentHandler",
            "UserMessageHandler",
            "JsonRpcHandler",
            "ErrorHandler",
            "BatchMessageHandler"
        ]
        
        for expected_handler in expected_handlers:
            assert expected_handler in handler_names, f"Must include {expected_handler} in built-in handlers"
        
        # Verify router tracks startup time for grace period
        assert hasattr(self.router, 'startup_time'), "Must track startup time for grace period handling"
        assert self.router.startup_grace_period_seconds == 10.0, "Must have 10-second grace period"

    @pytest.mark.unit
    def test_message_router_handler_precedence_custom_over_builtin(self):
        """Test MessageRouter gives custom handlers precedence over built-in handlers."""
        # Business value: Custom handler precedence allows system customization
        
        # Create custom handler that handles same type as built-in handler
        class CustomConnectionHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.CONNECT])
                
            async def handle_message(self, user_id, websocket, message):
                return "custom_handled"
        
        custom_handler = CustomConnectionHandler()
        self.router.add_handler(custom_handler)
        
        # Verify handler order - custom handlers first
        all_handlers = self.router.handlers
        custom_handlers = self.router.custom_handlers
        builtin_handlers = self.router.builtin_handlers
        
        assert len(custom_handlers) == 1, "Must have one custom handler"
        assert all_handlers[0] == custom_handler, "Custom handler must be first in precedence"
        assert all_handlers[1:] == builtin_handlers, "Built-in handlers must follow custom handlers"

    @pytest.mark.unit
    async def test_message_router_routes_message_to_correct_handler(self):
        """Test MessageRouter routes messages to appropriate handlers based on type."""
        # Business value: Correct message routing ensures handlers receive relevant messages
        user_id = "test-user-routing"
        
        # Test CONNECT message routing
        connect_raw_message = {
            "type": "connect",
            "payload": {"status": "connecting"},
            "timestamp": time.time(),
            "user_id": user_id
        }
        
        # Execute message routing
        result = await self.router.route_message(user_id, self.mock_websocket, connect_raw_message)
        
        # Validate routing success
        assert result is True, "Message routing must succeed"
        
        # Verify routing statistics are tracked
        stats = self.router.get_stats()
        assert stats["messages_routed"] >= 1, "Must track routed messages"
        assert "connect" in str(stats["message_types"]), "Must track message type statistics"

    @pytest.mark.unit
    async def test_message_router_handles_unknown_message_types_gracefully(self):
        """Test MessageRouter handles unknown message types with proper acknowledgment."""
        # Business value: Graceful handling of unknown messages prevents system crashes
        user_id = "test-user-unknown"
        
        unknown_message = {
            "type": "unknown_message_type_xyz",
            "payload": {"data": "test"},
            "timestamp": time.time()
        }
        
        # Execute with unknown message type
        result = await self.router.route_message(user_id, self.mock_websocket, unknown_message)
        
        # Validate graceful handling
        assert result is True, "Unknown message routing must succeed with acknowledgment"
        
        # Verify acknowledgment was sent
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "ack", "Must send acknowledgment for unknown messages"
        assert call_args["received_type"] == "unknown_message_type_xyz", "Must echo received type"
        assert call_args["user_id"] == user_id, "Must include user ID"
        assert call_args["status"] == "acknowledged", "Must confirm acknowledgment"
        
        # Verify statistics track unhandled messages
        stats = self.router.get_stats()
        assert stats["unhandled_messages"] >= 1, "Must track unhandled messages"

    @pytest.mark.unit
    def test_message_router_grace_period_status_during_startup(self):
        """Test MessageRouter reports appropriate status during startup grace period."""
        # Business value: Grace period prevents false alarms during system startup
        
        # Test status during grace period (simulated fresh router)
        fresh_router = MessageRouter()
        fresh_router.startup_time = time.time()  # Just started
        
        status = fresh_router.check_handler_status_with_grace_period()
        
        assert status["grace_period_active"] is True, "Must indicate grace period is active"
        assert status["status"] in ["initializing", "ready"], "Status must be initializing or ready"
        assert "elapsed_seconds" in status, "Must report elapsed time"
        assert status["handler_count"] >= 0, "Must report handler count"

    @pytest.mark.unit
    def test_message_router_error_status_after_grace_period_with_zero_handlers(self):
        """Test MessageRouter reports error status after grace period with zero handlers."""
        # Business value: Post-grace-period validation catches configuration issues
        
        # Create router with no handlers and expired grace period
        empty_router = MessageRouter()
        empty_router.builtin_handlers = []  # Remove all handlers
        empty_router.custom_handlers = []
        empty_router.startup_time = time.time() - 15.0  # 15 seconds ago (past grace period)
        
        status = empty_router.check_handler_status_with_grace_period()
        
        assert status["status"] == "error", "Must report error status with zero handlers"
        assert status["grace_period_active"] is False, "Grace period must be inactive"
        assert status["handler_count"] == 0, "Must report zero handlers"
        assert "No handlers registered" in status["message"], "Must explain the error"

    @pytest.mark.unit
    async def test_message_router_prepares_jsonrpc_messages_correctly(self):
        """Test MessageRouter correctly processes JSON-RPC messages."""
        # Business value: JSON-RPC support enables MCP compatibility for enhanced agent capabilities
        user_id = "test-user-jsonrpc"
        
        jsonrpc_message = {
            "jsonrpc": "2.0",
            "method": "tool_execution",
            "params": {"tool": "optimize_costs", "input": "analyze AWS"},
            "id": "req-123"
        }
        
        # Execute JSON-RPC message routing
        result = await self.router.route_message(user_id, self.mock_websocket, jsonrpc_message)
        
        # Validate JSON-RPC handling
        assert result is True, "JSON-RPC message routing must succeed"
        
        # Verify response was sent (JsonRpcHandler should respond to requests)
        self.mock_websocket.send_json.assert_called_once()
        call_args = self.mock_websocket.send_json.call_args[0][0]
        
        assert "jsonrpc" in call_args, "Must respond with JSON-RPC format"
        assert call_args["id"] == "req-123", "Must preserve request ID"

    @pytest.mark.unit
    def test_message_router_tracks_comprehensive_statistics(self):
        """Test MessageRouter tracks comprehensive statistics for monitoring."""
        # Business value: Statistics enable monitoring and debugging of WebSocket performance
        
        # Add custom handler to test handler stats
        class TestStatsHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.test_stat = "active"
                
            async def handle_message(self, user_id, websocket, message):
                return True
                
            def get_stats(self):
                return {"test_stat": self.test_stat}
        
        stats_handler = TestStatsHandler()
        self.router.add_handler(stats_handler)
        
        # Get comprehensive statistics
        stats = self.router.get_stats()
        
        # Validate comprehensive tracking
        required_stats = [
            "messages_routed",
            "unhandled_messages", 
            "handler_errors",
            "message_types",
            "handler_stats",
            "handler_order",
            "handler_count",
            "handler_status"
        ]
        
        for required_stat in required_stats:
            assert required_stat in stats, f"Must track {required_stat} statistic"
        
        # Verify handler-specific stats are included
        assert "TestStatsHandler" in stats["handler_stats"], "Must include custom handler stats"
        assert stats["handler_stats"]["TestStatsHandler"]["test_stat"] == "active", "Must preserve handler stats"
        
        # Verify handler order tracking
        assert len(stats["handler_order"]) > 0, "Must track handler execution order"
        assert "[0] TestStatsHandler" in stats["handler_order"], "Must show custom handler precedence"


class TestAgentRequestHandlerBusinessLogic(BaseUnitTest):
    """Test AgentRequestHandler business logic for E2E test agent communication."""
    
    def setUp(self):
        """Set up AgentRequestHandler for testing."""
        self.handler = AgentRequestHandler()
        
        # Create mock WebSocket
        self.mock_websocket = Mock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

    @pytest.mark.unit
    def test_agent_request_handler_supports_agent_message_types(self):
        """Test AgentRequestHandler supports AGENT_REQUEST and START_AGENT types."""
        # Business value: Proper agent request support enables E2E testing of agent workflows
        supported_types = self.handler.supported_types
        
        assert MessageType.AGENT_REQUEST in supported_types, "Must support AGENT_REQUEST"
        assert MessageType.START_AGENT in supported_types, "Must support START_AGENT"

    @pytest.mark.unit
    async def test_agent_request_handler_processes_single_agent_request(self):
        """Test AgentRequestHandler processes single agent requests correctly."""
        # Business value: Single agent processing handles majority of user queries efficiently
        user_id = "test-user-single-agent"
        
        agent_request = WebSocketMessage(
            type=MessageType.AGENT_REQUEST,
            payload={
                "message": "Optimize my cloud costs",
                "turn_id": "turn-123", 
                "require_multi_agent": False,
                "real_llm": False
            },
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute agent request handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, agent_request)
        
        # Validate business logic
        assert result is True, "Single agent request handling must succeed"
        
        # Verify agent response was sent
        self.mock_websocket.send_text.assert_called_once()
        response_text = self.mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_text)
        
        assert response_data["type"] == "agent_response", "Must send agent_response type"
        assert response_data["payload"]["status"] == "success", "Must indicate successful processing"
        assert "Optimize my cloud costs" in response_data["payload"]["content"], "Must echo user message"
        assert response_data["payload"]["agents_involved"] == ["triage"], "Single agent should use triage"
        assert response_data["payload"]["turn_id"] == "turn-123", "Must preserve turn_id"

    @pytest.mark.unit
    async def test_agent_request_handler_processes_multi_agent_request(self):
        """Test AgentRequestHandler processes multi-agent collaboration requests."""
        # Business value: Multi-agent collaboration handles complex optimization scenarios
        user_id = "test-user-multi-agent"
        
        multi_agent_request = WebSocketMessage(
            type=MessageType.AGENT_REQUEST,
            payload={
                "message": "Comprehensive cost optimization analysis with recommendations",
                "turn_id": "turn-456",
                "require_multi_agent": True,
                "real_llm": True
            },
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute multi-agent request handling
        result = await self.handler.handle_message(user_id, self.mock_websocket, multi_agent_request)
        
        # Validate business logic
        assert result is True, "Multi-agent request handling must succeed"
        
        # Verify multi-agent response
        response_text = self.mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_text)
        
        assert response_data["payload"]["agents_involved"] == ["supervisor", "triage", "optimization"], "Multi-agent should involve all three agents"
        assert "Multi-agent collaboration completed" in response_data["payload"]["content"], "Must indicate multi-agent processing"
        assert response_data["payload"]["real_llm_used"] is True, "Must track real LLM usage"
        assert response_data["payload"]["orchestration_time"] > 1.0, "Multi-agent should take longer"

    @pytest.mark.unit  
    async def test_agent_request_handler_handles_processing_errors_gracefully(self):
        """Test AgentRequestHandler handles processing errors with proper error responses."""
        # Business value: Graceful error handling prevents agent request failures from crashing chat
        user_id = "test-user-error"
        
        # Create message that will cause processing error (invalid payload)
        error_request = WebSocketMessage(
            type=MessageType.AGENT_REQUEST,
            payload=None,  # This will cause KeyError when accessing .get()
            timestamp=time.time(),
            user_id=user_id
        )
        
        # Execute error-inducing request
        result = await self.handler.handle_message(user_id, self.mock_websocket, error_request)
        
        # Validate error handling
        assert result is False, "Must return False for processing errors"
        
        # Verify error response was sent
        self.mock_websocket.send_text.assert_called_once()
        response_text = self.mock_websocket.send_text.call_args[0][0]
        response_data = json.loads(response_text)
        
        assert response_data["type"] == "error_message", "Must send error_message type"
        assert response_data["error_code"] == "AGENT_REQUEST_ERROR", "Must use appropriate error code"
        assert "Failed to process agent request" in response_data["error_message"], "Must explain error"


class TestGlobalMessageRouterFunctions(BaseUnitTest):
    """Test global message router functions and utilities."""
    
    @pytest.mark.unit
    def test_get_message_router_returns_singleton_instance(self):
        """Test get_message_router returns consistent singleton instance."""
        # Business value: Singleton pattern ensures consistent message routing across system
        
        # Get router multiple times
        router1 = get_message_router()
        router2 = get_message_router()
        
        # Verify same instance
        assert router1 is router2, "Must return same singleton instance"
        assert isinstance(router1, MessageRouter), "Must return MessageRouter instance"

    @pytest.mark.unit
    def test_get_router_handler_count_tracks_handlers_accurately(self):
        """Test get_router_handler_count returns accurate handler count."""
        # Business value: Handler count monitoring helps detect configuration issues
        
        # Get initial count
        initial_count = get_router_handler_count()
        assert initial_count >= 0, "Handler count must be non-negative"
        
        # Add custom handler and verify count increases
        router = get_message_router()
        
        class TestCountHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                
            async def handle_message(self, user_id, websocket, message):
                return True
        
        test_handler = TestCountHandler()
        router.add_handler(test_handler)
        
        updated_count = get_router_handler_count()
        assert updated_count == initial_count + 1, "Handler count must increase when handler added"

    @pytest.mark.unit
    def test_list_registered_handlers_returns_handler_names(self):
        """Test list_registered_handlers returns list of handler class names."""
        # Business value: Handler listing enables debugging and system monitoring
        
        handler_names = list_registered_handlers()
        
        assert isinstance(handler_names, list), "Must return list of handler names"
        assert len(handler_names) > 0, "Must have at least some built-in handlers"
        
        # Verify expected built-in handlers are present
        expected_builtin_handlers = [
            "ConnectionHandler",
            "TypingHandler", 
            "HeartbeatHandler",
            "UserMessageHandler"
        ]
        
        for expected_handler in expected_builtin_handlers:
            assert expected_handler in handler_names, f"Must list {expected_handler}"

    @pytest.mark.unit
    async def test_send_error_to_websocket_utility_function(self):
        """Test send_error_to_websocket utility sends properly formatted errors."""
        # Business value: Standardized error messaging improves user experience
        
        mock_websocket = Mock()
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = "websocket_mock"
        mock_websocket.send_json = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            # Send error message
            result = await send_error_to_websocket(
                mock_websocket,
                "TEST_ERROR",
                "This is a test error message",
                {"additional_data": "test_value"}
            )
            
            # Validate error sending
            assert result is True, "Error sending must succeed"
            
            # Verify error message format
            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]
            
            assert call_args["type"] == "error_message", "Must use error_message type"
            assert call_args["error_code"] == "TEST_ERROR", "Must preserve error code"
            assert call_args["error_message"] == "This is a test error message", "Must preserve error message"
            assert call_args["details"]["additional_data"] == "test_value", "Must include additional details"

    @pytest.mark.unit
    async def test_send_system_message_utility_function(self):
        """Test send_system_message utility sends properly formatted system messages."""
        # Business value: Standardized system messaging ensures consistent user notifications
        
        mock_websocket = Mock()
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = "websocket_mock"
        mock_websocket.send_json = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.handlers.is_websocket_connected', return_value=True):
            # Send system message
            result = await send_system_message(
                mock_websocket,
                "System initialization complete",
                {"status": "ready", "version": "1.0.0"}
            )
            
            # Validate system message sending
            assert result is True, "System message sending must succeed"
            
            # Verify system message format
            mock_websocket.send_json.assert_called_once()
            call_args = mock_websocket.send_json.call_args[0][0]
            
            assert call_args["type"] == "system_message", "Must use system_message type"
            assert call_args["payload"]["content"] == "System initialization complete", "Must preserve content"
            assert call_args["payload"]["status"] == "ready", "Must include additional data"
            assert call_args["payload"]["version"] == "1.0.0", "Must preserve additional data"


if __name__ == "__main__":
    # Run tests with proper WebSocket business logic validation
    pytest.main([__file__, "-v", "--tb=short"])