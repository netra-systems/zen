import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import User
from app.auth.auth_dependencies import ActiveUserDep
import uuid

def test_websocket_connection(client):
    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="test@example.com")
    with client.websocket_connect("/ws") as websocket:
        pass
    app.dependency_overrides = {}

def test_websocket_disconnect(client):
    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="test@example.com")
    with client.websocket_connect("/ws") as websocket:
        pass  # Disconnects automatically after the 'with' block
    app.dependency_overrides = {}

def test_websocket_multiple_connections(client):
    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="test@example.com")
    with client.websocket_connect("/ws") as websocket1:
        with client.websocket_connect("/ws") as websocket2:
            pass
    app.dependency_overrides = {}
