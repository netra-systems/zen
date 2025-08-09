import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse
from app.main import app
from app.ws_manager import manager
from app.auth.auth_dependencies import ActiveUserWsDep, get_dev_user
from app.schemas import User
import uuid
from fastapi import HTTPException
from app.config import settings

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

@pytest.mark.asyncio
async def test_websocket_unauthorized(client):
    async def raise_forbidden():
        raise HTTPException(status_code=403, detail="Forbidden")
    app.dependency_overrides[ActiveUserWsDep] = raise_forbidden
    with pytest.raises(WebSocketDenialResponse):
        with client.websocket_connect(f"/ws?user_id=unauthorized") as websocket:
            pass

@pytest.mark.asyncio
async def test_websocket_dev_login(client):
    original_env = settings.environment
    settings.environment = "development"
    app.dependency_overrides[ActiveUserWsDep] = get_dev_user
    with client.websocket_connect(f"/ws") as websocket:
        assert "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" in manager.active_connections
    settings.environment = original_env
