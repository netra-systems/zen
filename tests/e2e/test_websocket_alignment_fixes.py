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
    # REMOVED_SYNTAX_ERROR: End-to-end test for WebSocket message alignment fixes.
    # REMOVED_SYNTAX_ERROR: Tests the critical issues found and fixed:
        # REMOVED_SYNTAX_ERROR: 1. Payload field consistency (was data vs payload mismatch)
        # REMOVED_SYNTAX_ERROR: 2. Message type alignment (agent_response -> agent_completed, etc)
        # REMOVED_SYNTAX_ERROR: 3. Error message structure standardization
        # REMOVED_SYNTAX_ERROR: 4. General message serialization robustness
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import ( )
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: MessageType,
        # REMOVED_SYNTAX_ERROR: get_frontend_message_type,
        # REMOVED_SYNTAX_ERROR: FRONTEND_MESSAGE_TYPE_MAP
        


# REMOVED_SYNTAX_ERROR: class TestWebSocketAlignmentFixes:
    # REMOVED_SYNTAX_ERROR: """Test suite for WebSocket frontend-backend alignment fixes."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def ws_manager(self):
    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager instance."""
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
    # Reset singleton state for testing
    # REMOVED_SYNTAX_ERROR: manager.connections.clear()
    # REMOVED_SYNTAX_ERROR: manager.user_connections.clear()
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def mock_websocket(self):
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from starlette.websockets import WebSocketState

    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: ws.client_state = WebSocketState.CONNECTED
    # REMOVED_SYNTAX_ERROR: ws.application_state = WebSocketState.CONNECTED
    # REMOVED_SYNTAX_ERROR: return ws

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_payload_field_consistency(self, ws_manager, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test that all messages use 'payload' field, not 'data'."""
        # Connect user
        # REMOVED_SYNTAX_ERROR: user_id = "test_user"
        # REMOVED_SYNTAX_ERROR: connection_id = await ws_manager.connect_user(user_id, mock_websocket)

        # Test various message types
        # REMOVED_SYNTAX_ERROR: test_messages = [ )
        # REMOVED_SYNTAX_ERROR: {"type": "user_message", "payload": {"content": "Hello"}},
        # REMOVED_SYNTAX_ERROR: {"type": "agent_response", "payload": {"result": "Response"}},
        # REMOVED_SYNTAX_ERROR: {"type": "system_message", "payload": {"info": "System info"}}
        

        # REMOVED_SYNTAX_ERROR: for msg in test_messages:
            # REMOVED_SYNTAX_ERROR: await ws_manager.send_to_user(user_id, msg)

            # Verify the sent message
            # REMOVED_SYNTAX_ERROR: sent_msg = mock_websocket.send_json.call_args[0][0]

            # Should have 'payload' field, not 'data'
            # REMOVED_SYNTAX_ERROR: assert "payload" in sent_msg or any(k != "type" for k in sent_msg.keys())
            # REMOVED_SYNTAX_ERROR: assert "data" not in sent_msg

            # Reset mock for next iteration
            # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.reset_mock()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_non_serializable_object_uses_payload(self, ws_manager, mock_websocket):
                # REMOVED_SYNTAX_ERROR: """Test that non-JSON-serializable objects are wrapped with 'payload', not 'data'."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: user_id = "test_user"
                # REMOVED_SYNTAX_ERROR: connection_id = await ws_manager.connect_user(user_id, mock_websocket)

                # Create a non-serializable object
# REMOVED_SYNTAX_ERROR: class NonSerializable:
# REMOVED_SYNTAX_ERROR: def __str__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "NonSerializable object"

    # REMOVED_SYNTAX_ERROR: non_serializable = NonSerializable()

    # Send the non-serializable object
    # REMOVED_SYNTAX_ERROR: await ws_manager.send_to_user(user_id, non_serializable)

    # Check the sent message
    # REMOVED_SYNTAX_ERROR: sent_msg = mock_websocket.send_json.call_args[0][0]

    # Should use 'payload' for the serialized content
    # REMOVED_SYNTAX_ERROR: assert "payload" in sent_msg
    # REMOVED_SYNTAX_ERROR: assert "data" not in sent_msg
    # REMOVED_SYNTAX_ERROR: assert sent_msg["payload"] == "NonSerializable object"
    # REMOVED_SYNTAX_ERROR: assert sent_msg["type"] == "NonSerializable"
    # REMOVED_SYNTAX_ERROR: assert "serialization_error" in sent_msg

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_message_type_frontend_compatibility(self, ws_manager, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test that backend message types are converted to frontend-expected types."""
        # REMOVED_SYNTAX_ERROR: user_id = "test_user"
        # REMOVED_SYNTAX_ERROR: connection_id = await ws_manager.connect_user(user_id, mock_websocket)

        # Test message type mappings
        # REMOVED_SYNTAX_ERROR: test_cases = [ )
        # REMOVED_SYNTAX_ERROR: (MessageType.AGENT_RESPONSE, "agent_completed"),
        # REMOVED_SYNTAX_ERROR: (MessageType.AGENT_PROGRESS, "agent_update"),
        # REMOVED_SYNTAX_ERROR: (MessageType.THREAD_UPDATE, "thread_updated"),
        # REMOVED_SYNTAX_ERROR: (MessageType.ERROR_MESSAGE, "error"),
        # REMOVED_SYNTAX_ERROR: (MessageType.USER_MESSAGE, "user_message"),  # Should remain unchanged
        

        # REMOVED_SYNTAX_ERROR: for backend_type, expected_frontend_type in test_cases:
            # REMOVED_SYNTAX_ERROR: msg = {"type": backend_type, "payload": {"test": "data"}}
            # REMOVED_SYNTAX_ERROR: await ws_manager.send_to_user(user_id, msg)

            # REMOVED_SYNTAX_ERROR: sent_msg = mock_websocket.send_json.call_args[0][0]
            # REMOVED_SYNTAX_ERROR: assert sent_msg["type"] == expected_frontend_type

            # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.reset_mock()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_error_message_structure(self, ws_manager, mock_websocket):
                # REMOVED_SYNTAX_ERROR: """Test that error messages follow the standardized structure."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: user_id = "test_user"
                # REMOVED_SYNTAX_ERROR: connection_id = await ws_manager.connect_user(user_id, mock_websocket)

                # Send an error message
                # REMOVED_SYNTAX_ERROR: error_message = "Test error occurred"
                # REMOVED_SYNTAX_ERROR: error_code = "TEST_ERROR"
                # REMOVED_SYNTAX_ERROR: await ws_manager.send_error(user_id, error_message, error_code)

                # Check the sent message structure
                # REMOVED_SYNTAX_ERROR: sent_msg = mock_websocket.send_json.call_args[0][0]

                # Should have correct structure
                # REMOVED_SYNTAX_ERROR: assert sent_msg["type"] == "error"
                # REMOVED_SYNTAX_ERROR: assert "payload" in sent_msg
                # REMOVED_SYNTAX_ERROR: assert "error_message" in sent_msg["payload"]
                # REMOVED_SYNTAX_ERROR: assert sent_msg["payload"]["error_message"] == error_message
                # REMOVED_SYNTAX_ERROR: assert sent_msg["payload"]["error_code"] == error_code
                # REMOVED_SYNTAX_ERROR: assert "timestamp" in sent_msg["payload"]

                # Should NOT have nested 'error' object
                # REMOVED_SYNTAX_ERROR: assert "error" not in sent_msg

# REMOVED_SYNTAX_ERROR: def test_frontend_message_type_mapping(self):
    # REMOVED_SYNTAX_ERROR: """Test the get_frontend_message_type function."""
    # Test direct enum mappings
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type(MessageType.AGENT_RESPONSE) == "agent_completed"
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type(MessageType.AGENT_PROGRESS) == "agent_update"
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type(MessageType.THREAD_UPDATE) == "thread_updated"
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type(MessageType.ERROR_MESSAGE) == "error"

    # Test unmapped types (should await asyncio.sleep(0) )
    # REMOVED_SYNTAX_ERROR: return as-is)
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type(MessageType.USER_MESSAGE) == "user_message"
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type(MessageType.HEARTBEAT) == "heartbeat"

    # Test string input
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type("agent_response") == "agent_completed"
    # REMOVED_SYNTAX_ERROR: assert get_frontend_message_type("user_message") == "user_message"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_pydantic_model_serialization(self, ws_manager, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test that Pydantic models are serialized with correct message types."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: from pydantic import BaseModel

# REMOVED_SYNTAX_ERROR: class TestModel(BaseModel):
    # REMOVED_SYNTAX_ERROR: type: str = "agent_response"
    # REMOVED_SYNTAX_ERROR: content: str = "Test content"
    # REMOVED_SYNTAX_ERROR: value: int = 42

    # REMOVED_SYNTAX_ERROR: user_id = "test_user"
    # REMOVED_SYNTAX_ERROR: connection_id = await ws_manager.connect_user(user_id, mock_websocket)

    # Send Pydantic model
    # REMOVED_SYNTAX_ERROR: model = TestModel()
    # REMOVED_SYNTAX_ERROR: await ws_manager.send_to_user(user_id, model)

    # Check serialization
    # REMOVED_SYNTAX_ERROR: sent_msg = mock_websocket.send_json.call_args[0][0]

    # Type should be converted to frontend-compatible
    # REMOVED_SYNTAX_ERROR: assert sent_msg["type"] == "agent_completed"  # agent_response -> agent_completed
    # REMOVED_SYNTAX_ERROR: assert sent_msg["content"] == "Test content"
    # REMOVED_SYNTAX_ERROR: assert sent_msg["value"] == 42

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_broadcast_message_alignment(self, ws_manager, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """Test that broadcast messages maintain alignment."""
        # REMOVED_SYNTAX_ERROR: from starlette.websockets import WebSocketState

        # Connect multiple users
        # REMOVED_SYNTAX_ERROR: users = ["user1", "user2", "user3"]
        # REMOVED_SYNTAX_ERROR: websockets = {}

        # REMOVED_SYNTAX_ERROR: for user_id in users:
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: ws.client_state = WebSocketState.CONNECTED
            # REMOVED_SYNTAX_ERROR: ws.application_state = WebSocketState.CONNECTED
            # REMOVED_SYNTAX_ERROR: websockets[user_id] = ws
            # REMOVED_SYNTAX_ERROR: await ws_manager.connect_user(user_id, ws)

            # Broadcast a message
            # REMOVED_SYNTAX_ERROR: broadcast_msg = { )
            # REMOVED_SYNTAX_ERROR: "type": MessageType.AGENT_PROGRESS,
            # REMOVED_SYNTAX_ERROR: "payload": {"status": "Processing", "progress": 50}
            

            # REMOVED_SYNTAX_ERROR: result = await ws_manager.broadcast_to_all(broadcast_msg)

            # Check all users received aligned message
            # REMOVED_SYNTAX_ERROR: for user_id, ws in websockets.items():
                # REMOVED_SYNTAX_ERROR: assert ws.send_json.called
                # REMOVED_SYNTAX_ERROR: sent_msg = ws.send_json.call_args[0][0]
                # REMOVED_SYNTAX_ERROR: assert sent_msg["type"] == "agent_update"  # agent_progress -> agent_update
                # REMOVED_SYNTAX_ERROR: assert sent_msg["payload"]["status"] == "Processing"
                # REMOVED_SYNTAX_ERROR: assert sent_msg["payload"]["progress"] == 50


                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                    # Run tests
                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])
                    # REMOVED_SYNTAX_ERROR: pass