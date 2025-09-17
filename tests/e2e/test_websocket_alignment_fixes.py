class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message.
        if self._closed:
            raise RuntimeError(WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):
        Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        End-to-end test for WebSocket message alignment fixes.
        Tests the critical issues found and fixed:
        1. Payload field consistency (was data vs payload mismatch)
        2. Message type alignment (agent_response -> agent_completed, etc)
        3. Error message structure standardization
        4. General message serialization robustness
        '''

        import asyncio
        import json
        import pytest
        from typing import Dict, Any
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
        from netra_backend.app.websocket_core.types import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        MessageType,
        get_frontend_message_type,
        FRONTEND_MESSAGE_TYPE_MAP
        


class TestWebSocketAlignmentFixes:
        "Test suite for WebSocket frontend-backend alignment fixes.

        @pytest.fixture
    async def ws_manager(self):
        ""Create WebSocket manager instance.
        manager = WebSocketManager()
    # Reset singleton state for testing
        manager.connections.clear()
        manager.user_connections.clear()
        await asyncio.sleep(0)
        return manager

        @pytest.fixture
    def mock_websocket(self):
        Create mock WebSocket connection.""
        pass
        from starlette.websockets import WebSocketState

        websocket = TestWebSocketConnection()
        ws.client_state = WebSocketState.CONNECTED
        ws.application_state = WebSocketState.CONNECTED
        return ws

@pytest.mark.asyncio
    async def test_payload_field_consistency(self, ws_manager, mock_websocket):
        Test that all messages use 'payload' field, not 'data'.""

        # Connect user
user_id = test_user
connection_id = await ws_manager.connect_user(user_id, mock_websocket)

        # Test various message types
test_messages = ]
{type: "user_message, payload": {content: Hello}},
{"type: agent_response", payload: {result: Response}},"
{type": system_message, payload: {info: System info"}}"
        

for msg in test_messages:
    await ws_manager.send_to_user(user_id, msg)


            # Verify the sent message
sent_msg = mock_websocket.send_json.call_args[0][0]

            # Should have 'payload' field, not 'data'
assert payload in sent_msg or any(k != type for k in sent_msg.keys())
assert data not in sent_msg"

            # Reset mock for next iteration
mock_websocket.send_json.reset_mock()

@pytest.mark.asyncio
    async def test_non_serializable_object_uses_payload(self, ws_manager, mock_websocket):
        "Test that non-JSON-serializable objects are wrapped with 'payload', not 'data'.

pass
user_id = "test_user"
connection_id = await ws_manager.connect_user(user_id, mock_websocket)

                # Create a non-serializable object
class NonSerializable:
    def __str__(self):
        pass
        await asyncio.sleep(0)
        return NonSerializable object

        non_serializable = NonSerializable()

    # Send the non-serializable object
        await ws_manager.send_to_user(user_id, non_serializable)

    # Check the sent message
        sent_msg = mock_websocket.send_json.call_args[0][0]

    # Should use 'payload' for the serialized content
        assert payload in sent_msg"
        assert data" not in sent_msg
        assert sent_msg[payload] == NonSerializable object
        assert sent_msg["type] == NonSerializable"
        assert serialization_error in sent_msg

@pytest.mark.asyncio
    async def test_message_type_frontend_compatibility(self, ws_manager, mock_websocket):
        "Test that backend message types are converted to frontend-expected types."

user_id = test_user
connection_id = await ws_manager.connect_user(user_id, mock_websocket)

        # Test message type mappings
test_cases = ]
(MessageType.AGENT_RESPONSE, agent_completed"),"
(MessageType.AGENT_PROGRESS, agent_update),
(MessageType.THREAD_UPDATE, thread_updated),"
(MessageType.ERROR_MESSAGE, "error),
(MessageType.USER_MESSAGE, user_message),  # Should remain unchanged
        

for backend_type, expected_frontend_type in test_cases:
    msg = {"type: backend_type, payload": {test: data}}

await ws_manager.send_to_user(user_id, msg)

sent_msg = mock_websocket.send_json.call_args[0][0]
assert sent_msg[type] == expected_frontend_type"

mock_websocket.send_json.reset_mock()

@pytest.mark.asyncio
    async def test_error_message_structure(self, ws_manager, mock_websocket):
        "Test that error messages follow the standardized structure.

pass
user_id = "test_user"
connection_id = await ws_manager.connect_user(user_id, mock_websocket)

                # Send an error message
error_message = Test error occurred
error_code = TEST_ERROR"
await ws_manager.send_error(user_id, error_message, error_code)

                # Check the sent message structure
sent_msg = mock_websocket.send_json.call_args[0][0]

                # Should have correct structure
assert sent_msg[type"] == error
assert payload in sent_msg
assert "error_message in sent_msg[payload"]
assert sent_msg[payload][error_message] == error_message
assert sent_msg[payload][error_code"] == error_code
assert "timestamp in sent_msg[payload]

                # Should NOT have nested 'error' object
assert error not in sent_msg

def test_frontend_message_type_mapping(self):
    ""Test the get_frontend_message_type function.

    # Test direct enum mappings
assert get_frontend_message_type(MessageType.AGENT_RESPONSE) == agent_completed"
assert get_frontend_message_type(MessageType.AGENT_PROGRESS) == agent_update"
assert get_frontend_message_type(MessageType.THREAD_UPDATE) == thread_updated
assert get_frontend_message_type(MessageType.ERROR_MESSAGE) == error""

    # Test unmapped types (should await asyncio.sleep(0) )
return as-is)
assert get_frontend_message_type(MessageType.USER_MESSAGE) == user_message
assert get_frontend_message_type(MessageType.HEARTBEAT) == heartbeat"

    # Test string input
assert get_frontend_message_type("agent_response) == agent_completed
assert get_frontend_message_type(user_message) == user_message

@pytest.mark.asyncio
    async def test_pydantic_model_serialization(self, ws_manager, mock_websocket):
        "Test that Pydantic models are serialized with correct message types."

pass
from pydantic import BaseModel

class TestModel(BaseModel):
    type: str = agent_response"
    content: str = "Test content
    value: int = 42

    user_id = test_user
    connection_id = await ws_manager.connect_user(user_id, mock_websocket)

    # Send Pydantic model
    model = TestModel()
    await ws_manager.send_to_user(user_id, model)

    # Check serialization
    sent_msg = mock_websocket.send_json.call_args[0][0]

    # Type should be converted to frontend-compatible
    assert sent_msg["type] == agent_completed"  # agent_response -> agent_completed
    assert sent_msg[content] == Test content
    assert sent_msg[value] == 42"

@pytest.mark.asyncio
    async def test_broadcast_message_alignment(self, ws_manager, mock_websocket):
        "Test that broadcast messages maintain alignment.

from starlette.websockets import WebSocketState

        # Connect multiple users
users = ["user1, user2", user3]
websockets = {}

for user_id in users:
    websocket = TestWebSocketConnection()

ws.client_state = WebSocketState.CONNECTED
ws.application_state = WebSocketState.CONNECTED
websockets[user_id] = ws
await ws_manager.connect_user(user_id, ws)

            # Broadcast a message
broadcast_msg = {
type: MessageType.AGENT_PROGRESS,"
"payload: {status: Processing, progress: 50}
            

result = await ws_manager.broadcast_to_all(broadcast_msg)

            # Check all users received aligned message
for user_id, ws in websockets.items():
    assert ws.send_json.called

sent_msg = ws.send_json.call_args[0][0]
assert sent_msg["type] == agent_update"  # agent_progress -> agent_update
assert sent_msg[payload][status] == Processing"
assert sent_msg[payload"][progress] == 50


if __name__ == __main__:
                    # Run tests
pytest.main([__file__, "-v"]
pass
