import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ws_manager import manager
from app.auth.auth_dependencies import ActiveUserWsDep
from app.schemas import User
import uuid

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def active_user():
    return User(id=str(uuid.uuid4()), email="test@example.com", is_superuser=False)

@pytest.mark.asyncio
async def test_websocket_connection(client, active_user):
    app.dependency_overrides[ActiveUserWsDep] = lambda: active_user
    with client.websocket_connect(f"/ws?user_id={active_user.id}") as websocket:
        user_id = str(active_user.id)
        assert user_id in manager.active_connections

@pytest.mark.asyncio
async def test_websocket_disconnect(client, active_user):
    app.dependency_overrides[ActiveUserWsDep] = lambda: active_user
    with client.websocket_connect(f"/ws?user_id={active_user.id}") as websocket:
        user_id = str(active_user.id)
        assert user_id in manager.active_connections
    assert user_id not in manager.active_connections