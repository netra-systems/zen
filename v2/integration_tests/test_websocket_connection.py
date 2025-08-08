import pytest
import asyncio
import websockets
from app.main import app
from app.schemas import User
from app.auth.auth_dependencies import ActiveUserWsDep

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)

def override_active_user_ws_dep():
    return User(id="test_user", email="test@example.com")

app.dependency_overrides[ActiveUserWsDep] = override_active_user_ws_dep

@pytest.mark.asyncio
async def test_websocket_connection():
    async with websockets.connect("ws://localhost:8000/ws/test_run_ws") as websocket:
        await websocket.send("ping")
        response = await websocket.recv()
        assert response == "pong"