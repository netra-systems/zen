import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import User, WebSocketMessage, WebSocketError
from app.auth.auth_dependencies import ActiveUserWsDep
import uuid

@pytest.fixture
def client():
    return TestClient(app)

def override_active_user_ws_dep():
    return User(id=str(uuid.uuid4()), email="test@example.com")

app.dependency_overrides[ActiveUserWsDep] = override_active_user_ws_dep

def test_websocket_connection(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"

def test_websocket_disconnect(client):
    with client.websocket_connect("/ws") as websocket:
        pass  # Disconnects automatically after the 'with' block

def test_websocket_multiple_connections(client):
    with client.websocket_connect("/ws") as websocket1:
        with client.websocket_connect("/ws") as websocket2:
            websocket1.send_text("ping")
            data1 = websocket1.receive_text()
            assert data1 == "pong"

            websocket2.send_text("ping")
            data2 = websocket2.receive_text()
            assert data2 == "pong"

def test_websocket_invalid_json(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("invalid message")
        response = websocket.receive_json()
        ws_message = WebSocketMessage.parse_obj(response)
        assert ws_message.type == "error"
        assert isinstance(ws_message.payload, WebSocketError)
        assert "Invalid JSON format" in ws_message.payload.message

def test_websocket_invalid_message_type(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "invalid_type", "payload": {}})
        response = websocket.receive_json()
        ws_message = WebSocketMessage.parse_obj(response)
        assert ws_message.type == "error"
        assert isinstance(ws_message.payload, WebSocketError)
        assert "Unknown message type" in ws_message.payload.message
