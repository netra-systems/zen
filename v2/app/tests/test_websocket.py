import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import User
from app.dependencies import get_current_user
import uuid

@pytest.fixture
def authenticated_client():
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[get_current_user]

def test_websocket_handshake(authenticated_client):
    with authenticated_client.websocket_connect("/ws/123") as websocket:
        assert websocket.scope["user"].email == "test@example.com"