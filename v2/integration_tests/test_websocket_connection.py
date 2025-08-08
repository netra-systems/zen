import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import User
from app.auth.auth_dependencies import ActiveUserWsDep

@pytest.fixture
def client():
    return TestClient(app)

def override_active_user_ws_dep():
    return User(id="test_user", email="test@example.com")

app.dependency_overrides[ActiveUserWsDep] = override_active_user_ws_dep


def test_websocket_connection(client):
    with client.websocket_connect("/ws/ws") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"