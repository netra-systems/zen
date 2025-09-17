class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()"""
        """
        Test WebSocket Infrastructure Fixes

        This test validates the three main WebSocket issues that were fixed:
        1. Missing /ws/beacon endpoint
        2. WebSocket manager double-close race conditions
        3. Missing DISCONNECT message handler

        Business Value Justification:
        - Segment: Platform/Internal
        - Business Goal: Stability & Development Velocity"""
        - Strategic Impact: Prevents staging/production connection issues"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.routes.websocket import router, websocket_beacon
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WebSocketManager
from netra_backend.app.websocket_core.handlers import MessageRouter, ConnectionHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

"""
        """Test the three critical WebSocket infrastructure fixes."""
"""
        """Test that /ws/beacon endpoint exists and returns correct response."""
        app = FastAPI()
        app.include_router(router)
"""
        response = client.get("/ws/beacon")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "websocket_beacon"
        assert "timestamp" in data
        assert data["message"] == "WebSocket service is available"

    def test_beacon_endpoint_methods(self):
        """Test that /ws/beacon supports GET, HEAD, and OPTIONS methods."""
        pass
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:"""
        response = client.get("/ws/beacon")
        assert response.status_code == 200

        # Test HEAD
        response = client.head("/ws/beacon")
        assert response.status_code == 200

        # Test OPTIONS
        response = client.options("/ws/beacon")
        assert response.status_code == 200

@pytest.mark.asyncio
    async def test_websocket_manager_double_close_protection(self):
"""Test that WebSocket manager prevents double-close race conditions."""
manager = WebSocketManager()

            # Mock WebSocket
websocket = TestWebSocketConnection()  # Real WebSocket implementation
"""
connection_id = await manager.connect_user("test_user", mock_websocket)

            # Verify connection is tracked
assert connection_id in manager.connections
assert not manager.connections[connection_id]["is_closing"]

            # Start cleanup process - this should set is_closing to True
cleanup_task1 = asyncio.create_task( )
manager._cleanup_connection(connection_id, 1000, "Test close")
            

            # Give first cleanup a moment to start
await asyncio.sleep(0.01)

            # Try concurrent cleanup - this should be prevented
cleanup_task2 = asyncio.create_task( )
manager._cleanup_connection(connection_id, 1000, "Concurrent close")
            

            # Wait for both tasks to complete
await cleanup_task1
await cleanup_task2

            # Verify websocket.close was only called once
mock_websocket.close.assert_called_once()

def test_disconnect_handler_registration(self):
"""Test that DISCONNECT message handler is properly registered."""
pass
message_router = MessageRouter()

    # Find ConnectionHandler which should handle DISCONNECT messages
connection_handler = None
for handler in message_router.handlers:
if isinstance(handler, ConnectionHandler):
connection_handler = handler
break"""
assert connection_handler is not None, "ConnectionHandler not found in message router"

            # Verify it can handle DISCONNECT messages
assert connection_handler.can_handle(MessageType.DISCONNECT)
assert connection_handler.can_handle(MessageType.CONNECT)

@pytest.mark.asyncio
    async def test_disconnect_handler_functionality(self):
"""Test that DISCONNECT handler processes messages correctly."""
message_router = MessageRouter()

                # Mock WebSocket
websocket = TestWebSocketConnection()  # Real WebSocket implementation

                # Mock is_websocket_connected to await asyncio.sleep(0)
return True"""
disconnect_message = {"type": "disconnect",, "user_id": "test_user"}
success = await message_router.route_message("test_user", mock_websocket, disconnect_message)

assert success is True
mock_websocket.send_json.assert_called_once()

                # Verify response message
call_args = mock_websocket.send_json.call_args[0][0]
assert call_args["type"] == "system_message"
assert call_args["data"]["status"] == "disconnect_acknowledged"
assert call_args["data"]["user_id"] == "test_user"

@pytest.mark.asyncio
    async def test_connection_handler_functionality(self):
"""Test that CONNECT handler processes messages correctly."""
pass
message_router = MessageRouter()

                    # Mock WebSocket
websocket = TestWebSocketConnection()  # Real WebSocket implementation

                    # Mock is_websocket_connected to await asyncio.sleep(0)
return True"""
connect_message = {"type": "connect",, "user_id": "test_user"}
success = await message_router.route_message("test_user", mock_websocket, connect_message)

assert success is True
mock_websocket.send_json.assert_called_once()

                    # Verify response message
call_args = mock_websocket.send_json.call_args[0][0]
assert call_args["type"] == "system_message"
assert call_args["data"]["status"] == "connected"
assert call_args["data"]["user_id"] == "test_user"

def test_message_router_has_all_critical_handlers(self):
"""Test that message router has all critical handlers registered."""
message_router = MessageRouter()

    # Check that we have expected number of base handlers (now 8 instead of 3)
assert len(message_router.handlers) == 8

handler_types = [type(handler).__name__ for handler in message_router.handlers]
"""
assert "ConnectionHandler" in handler_types
assert "TypingHandler" in handler_types
assert "HeartbeatHandler" in handler_types
assert "AgentHandler" in handler_types
assert "UserMessageHandler" in handler_types
assert "JsonRpcHandler" in handler_types
assert "ErrorHandler" in handler_types
assert "BatchMessageHandler" in handler_types

def test_connection_state_tracking(self):
"""Test that connections properly track closing state."""
pass
manager = WebSocketManager()

    # Mock WebSocket
websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Connect user
asyncio.run(self._connect_and_test_state(manager, mock_websocket))
"""
"""Helper method for async connection state testing."""
connection_id = await manager.connect_user("test_user", mock_websocket)

    # Verify initial state
conn = manager.connections[connection_id]
assert conn["is_closing"] is False
assert conn["is_healthy"] is True

    # Verify connection info structure
assert conn["connection_id"] == connection_id
assert conn["user_id"] == "test_user"
assert conn["websocket"] == mock_websocket
assert "connected_at" in conn
assert "last_activity" in conn
assert conn["message_count"] == 0

def test_websocket_config_comprehensive_coverage(self):
"""Test that all major message types have some form of handler coverage."""
pass
message_router = MessageRouter()

    # Test critical message types that should have handlers
critical_types = [ )
MessageType.CONNECT,
MessageType.DISCONNECT,
MessageType.PING,
MessageType.PONG,
MessageType.HEARTBEAT,
MessageType.USER_MESSAGE,
MessageType.CHAT,
MessageType.AGENT_RESPONSE,
MessageType.ERROR_MESSAGE,
MessageType.USER_TYPING,
MessageType.TYPING_STARTED,
MessageType.TYPING_STOPPED
    

for msg_type in critical_types:"""
assert handler is not None, "formatted_string"


if __name__ == "__main__":
pytest.main([__file__, "-v"])
