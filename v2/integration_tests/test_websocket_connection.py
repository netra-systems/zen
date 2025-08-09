import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import User
from app.auth.auth_dependencies import get_current_user_ws
import uuid

def test_websocket_connection(client):
    token = "test_token"
    app.dependency_overrides[get_current_user_ws] = lambda: User(id=str(uuid.uuid4()), email="test@example.com")
    with client.websocket_connect(f"/ws/{token}") as websocket:
        pass
    app.dependency_overrides = {}

def test_websocket_disconnect(client):
    token = "test_token"
    app.dependency_overrides[get_current_user_ws] = lambda: User(id=str(uuid.uuid4()), email="test@example.com")
    with client.websocket_connect(f"/ws/{token}") as websocket:
        pass  # Disconnects automatically after the 'with' block
    app.dependency_overrides = {}

def test_websocket_multiple_connections(client):
    token = "test_token"
    app.dependency_overrides[get_current_user_ws] = lambda: User(id=str(uuid.uuid4()), email="test@example.com")
    with client.websocket_connect(f"/ws/{token}") as websocket1:
        with client.websocket_connect(f"/ws/{token}") as websocket2:
            pass
    app.dependency_overrides = {}


def test_websocket_unauthorized_connection(client):
    token = "test_token"
    app.dependency_overrides[get_current_user_ws] = lambda: None
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/{token}") as websocket:
            pass
    app.dependency_overrides = {}
