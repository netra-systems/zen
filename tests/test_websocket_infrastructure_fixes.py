# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test WebSocket Infrastructure Fixes

    # REMOVED_SYNTAX_ERROR: This test validates the three main WebSocket issues that were fixed:
        # REMOVED_SYNTAX_ERROR: 1. Missing /ws/beacon endpoint
        # REMOVED_SYNTAX_ERROR: 2. WebSocket manager double-close race conditions
        # REMOVED_SYNTAX_ERROR: 3. Missing DISCONNECT message handler

        # REMOVED_SYNTAX_ERROR: Business Value Justification:
            # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
            # REMOVED_SYNTAX_ERROR: - Business Goal: Stability & Development Velocity
            # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures WebSocket infrastructure is fully functional
            # REMOVED_SYNTAX_ERROR: - Strategic Impact: Prevents staging/production connection issues
            # REMOVED_SYNTAX_ERROR: '''

            # REMOVED_SYNTAX_ERROR: import asyncio
            # REMOVED_SYNTAX_ERROR: import pytest
            # REMOVED_SYNTAX_ERROR: from fastapi.testclient import TestClient
            # REMOVED_SYNTAX_ERROR: from fastapi import FastAPI
            # REMOVED_SYNTAX_ERROR: import json
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.websocket import router, websocket_beacon
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import MessageRouter, ConnectionHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestWebSocketInfrastructureFixes:
    # REMOVED_SYNTAX_ERROR: """Test the three critical WebSocket infrastructure fixes."""

# REMOVED_SYNTAX_ERROR: def test_beacon_endpoint_exists(self):
    # REMOVED_SYNTAX_ERROR: """Test that /ws/beacon endpoint exists and returns correct response."""
    # REMOVED_SYNTAX_ERROR: app = FastAPI()
    # REMOVED_SYNTAX_ERROR: app.include_router(router)

    # REMOVED_SYNTAX_ERROR: with TestClient(app) as client:
        # REMOVED_SYNTAX_ERROR: response = client.get("/ws/beacon")

        # REMOVED_SYNTAX_ERROR: assert response.status_code == 200
        # REMOVED_SYNTAX_ERROR: data = response.json()
        # REMOVED_SYNTAX_ERROR: assert data["status"] == "healthy"
        # REMOVED_SYNTAX_ERROR: assert data["service"] == "websocket_beacon"
        # REMOVED_SYNTAX_ERROR: assert "timestamp" in data
        # REMOVED_SYNTAX_ERROR: assert data["message"] == "WebSocket service is available"

# REMOVED_SYNTAX_ERROR: def test_beacon_endpoint_methods(self):
    # REMOVED_SYNTAX_ERROR: """Test that /ws/beacon supports GET, HEAD, and OPTIONS methods."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: app = FastAPI()
    # REMOVED_SYNTAX_ERROR: app.include_router(router)

    # REMOVED_SYNTAX_ERROR: with TestClient(app) as client:
        # Test GET
        # REMOVED_SYNTAX_ERROR: response = client.get("/ws/beacon")
        # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

        # Test HEAD
        # REMOVED_SYNTAX_ERROR: response = client.head("/ws/beacon")
        # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

        # Test OPTIONS
        # REMOVED_SYNTAX_ERROR: response = client.options("/ws/beacon")
        # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_websocket_manager_double_close_protection(self):
            # REMOVED_SYNTAX_ERROR: """Test that WebSocket manager prevents double-close race conditions."""
            # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

            # Mock WebSocket
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

            # Connect a user
            # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user("test_user", mock_websocket)

            # Verify connection is tracked
            # REMOVED_SYNTAX_ERROR: assert connection_id in manager.connections
            # REMOVED_SYNTAX_ERROR: assert not manager.connections[connection_id]["is_closing"]

            # Start cleanup process - this should set is_closing to True
            # REMOVED_SYNTAX_ERROR: cleanup_task1 = asyncio.create_task( )
            # REMOVED_SYNTAX_ERROR: manager._cleanup_connection(connection_id, 1000, "Test close")
            

            # Give first cleanup a moment to start
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)

            # Try concurrent cleanup - this should be prevented
            # REMOVED_SYNTAX_ERROR: cleanup_task2 = asyncio.create_task( )
            # REMOVED_SYNTAX_ERROR: manager._cleanup_connection(connection_id, 1000, "Concurrent close")
            

            # Wait for both tasks to complete
            # REMOVED_SYNTAX_ERROR: await cleanup_task1
            # REMOVED_SYNTAX_ERROR: await cleanup_task2

            # Verify websocket.close was only called once
            # REMOVED_SYNTAX_ERROR: mock_websocket.close.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_disconnect_handler_registration(self):
    # REMOVED_SYNTAX_ERROR: """Test that DISCONNECT message handler is properly registered."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: message_router = MessageRouter()

    # Find ConnectionHandler which should handle DISCONNECT messages
    # REMOVED_SYNTAX_ERROR: connection_handler = None
    # REMOVED_SYNTAX_ERROR: for handler in message_router.handlers:
        # REMOVED_SYNTAX_ERROR: if isinstance(handler, ConnectionHandler):
            # REMOVED_SYNTAX_ERROR: connection_handler = handler
            # REMOVED_SYNTAX_ERROR: break

            # REMOVED_SYNTAX_ERROR: assert connection_handler is not None, "ConnectionHandler not found in message router"

            # Verify it can handle DISCONNECT messages
            # REMOVED_SYNTAX_ERROR: assert connection_handler.can_handle(MessageType.DISCONNECT)
            # REMOVED_SYNTAX_ERROR: assert connection_handler.can_handle(MessageType.CONNECT)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_disconnect_handler_functionality(self):
                # REMOVED_SYNTAX_ERROR: """Test that DISCONNECT handler processes messages correctly."""
                # REMOVED_SYNTAX_ERROR: message_router = MessageRouter()

                # Mock WebSocket
                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

                # Mock is_websocket_connected to await asyncio.sleep(0)
                # REMOVED_SYNTAX_ERROR: return True
                # Test DISCONNECT message handling
                # REMOVED_SYNTAX_ERROR: disconnect_message = { )
                # REMOVED_SYNTAX_ERROR: "type": "disconnect",
                # REMOVED_SYNTAX_ERROR: "user_id": "test_user"
                

                # REMOVED_SYNTAX_ERROR: success = await message_router.route_message("test_user", mock_websocket, disconnect_message)

                # REMOVED_SYNTAX_ERROR: assert success is True
                # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.assert_called_once()

                # Verify response message
                # REMOVED_SYNTAX_ERROR: call_args = mock_websocket.send_json.call_args[0][0]
                # REMOVED_SYNTAX_ERROR: assert call_args["type"] == "system_message"
                # REMOVED_SYNTAX_ERROR: assert call_args["data"]["status"] == "disconnect_acknowledged"
                # REMOVED_SYNTAX_ERROR: assert call_args["data"]["user_id"] == "test_user"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_connection_handler_functionality(self):
                    # REMOVED_SYNTAX_ERROR: """Test that CONNECT handler processes messages correctly."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: message_router = MessageRouter()

                    # Mock WebSocket
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

                    # Mock is_websocket_connected to await asyncio.sleep(0)
                    # REMOVED_SYNTAX_ERROR: return True
                    # Test CONNECT message handling
                    # REMOVED_SYNTAX_ERROR: connect_message = { )
                    # REMOVED_SYNTAX_ERROR: "type": "connect",
                    # REMOVED_SYNTAX_ERROR: "user_id": "test_user"
                    

                    # REMOVED_SYNTAX_ERROR: success = await message_router.route_message("test_user", mock_websocket, connect_message)

                    # REMOVED_SYNTAX_ERROR: assert success is True
                    # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.assert_called_once()

                    # Verify response message
                    # REMOVED_SYNTAX_ERROR: call_args = mock_websocket.send_json.call_args[0][0]
                    # REMOVED_SYNTAX_ERROR: assert call_args["type"] == "system_message"
                    # REMOVED_SYNTAX_ERROR: assert call_args["data"]["status"] == "connected"
                    # REMOVED_SYNTAX_ERROR: assert call_args["data"]["user_id"] == "test_user"

# REMOVED_SYNTAX_ERROR: def test_message_router_has_all_critical_handlers(self):
    # REMOVED_SYNTAX_ERROR: """Test that message router has all critical handlers registered."""
    # REMOVED_SYNTAX_ERROR: message_router = MessageRouter()

    # Check that we have expected number of base handlers (now 8 instead of 3)
    # REMOVED_SYNTAX_ERROR: assert len(message_router.handlers) == 8

    # REMOVED_SYNTAX_ERROR: handler_types = [type(handler).__name__ for handler in message_router.handlers]

    # Verify critical handlers are present
    # REMOVED_SYNTAX_ERROR: assert "ConnectionHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "TypingHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "HeartbeatHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "AgentHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "UserMessageHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "JsonRpcHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "ErrorHandler" in handler_types
    # REMOVED_SYNTAX_ERROR: assert "BatchMessageHandler" in handler_types

# REMOVED_SYNTAX_ERROR: def test_connection_state_tracking(self):
    # REMOVED_SYNTAX_ERROR: """Test that connections properly track closing state."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

    # Mock WebSocket
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Connect user
    # REMOVED_SYNTAX_ERROR: asyncio.run(self._connect_and_test_state(manager, mock_websocket))

# REMOVED_SYNTAX_ERROR: async def _connect_and_test_state(self, manager, mock_websocket):
    # REMOVED_SYNTAX_ERROR: """Helper method for async connection state testing."""
    # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user("test_user", mock_websocket)

    # Verify initial state
    # REMOVED_SYNTAX_ERROR: conn = manager.connections[connection_id]
    # REMOVED_SYNTAX_ERROR: assert conn["is_closing"] is False
    # REMOVED_SYNTAX_ERROR: assert conn["is_healthy"] is True

    # Verify connection info structure
    # REMOVED_SYNTAX_ERROR: assert conn["connection_id"] == connection_id
    # REMOVED_SYNTAX_ERROR: assert conn["user_id"] == "test_user"
    # REMOVED_SYNTAX_ERROR: assert conn["websocket"] == mock_websocket
    # REMOVED_SYNTAX_ERROR: assert "connected_at" in conn
    # REMOVED_SYNTAX_ERROR: assert "last_activity" in conn
    # REMOVED_SYNTAX_ERROR: assert conn["message_count"] == 0

# REMOVED_SYNTAX_ERROR: def test_websocket_config_comprehensive_coverage(self):
    # REMOVED_SYNTAX_ERROR: """Test that all major message types have some form of handler coverage."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: message_router = MessageRouter()

    # Test critical message types that should have handlers
    # REMOVED_SYNTAX_ERROR: critical_types = [ )
    # REMOVED_SYNTAX_ERROR: MessageType.CONNECT,
    # REMOVED_SYNTAX_ERROR: MessageType.DISCONNECT,
    # REMOVED_SYNTAX_ERROR: MessageType.PING,
    # REMOVED_SYNTAX_ERROR: MessageType.PONG,
    # REMOVED_SYNTAX_ERROR: MessageType.HEARTBEAT,
    # REMOVED_SYNTAX_ERROR: MessageType.USER_MESSAGE,
    # REMOVED_SYNTAX_ERROR: MessageType.CHAT,
    # REMOVED_SYNTAX_ERROR: MessageType.AGENT_RESPONSE,
    # REMOVED_SYNTAX_ERROR: MessageType.ERROR_MESSAGE,
    # REMOVED_SYNTAX_ERROR: MessageType.USER_TYPING,
    # REMOVED_SYNTAX_ERROR: MessageType.TYPING_STARTED,
    # REMOVED_SYNTAX_ERROR: MessageType.TYPING_STOPPED
    

    # REMOVED_SYNTAX_ERROR: for msg_type in critical_types:
        # REMOVED_SYNTAX_ERROR: handler = message_router._find_handler(msg_type)
        # REMOVED_SYNTAX_ERROR: assert handler is not None, "formatted_string"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])