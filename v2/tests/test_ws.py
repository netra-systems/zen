import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.schemas import WebSocketMessage, AnalysisRequest, User

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_supervisor():
    supervisor = AsyncMock()
    supervisor.start_agent = AsyncMock()
    return supervisor

@pytest.fixture(autouse=True)
def override_dependencies(mock_supervisor):
    app.dependency_overrides[get_agent_supervisor] = lambda: mock_supervisor
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_websocket_connection(client):
    with client.websocket_connect("/ws?token=test_token") as websocket:
        assert websocket.scope["user"].email == "test@example.com"

@pytest.mark.asyncio
async def test_websocket_invalid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=invalid_token") as websocket:
            pass

@pytest.mark.asyncio
async def test_websocket_analysis_request(client, mock_supervisor):
    with client.websocket_connect("/ws?token=test_token") as websocket:
        analysis_request_payload = {"prompt": "test prompt"}
        ws_message = WebSocketMessage(type="analysis_request", payload=analysis_request_payload)
        websocket.send_text(ws_message.json())
        mock_supervisor.start_agent.assert_called_once()

@pytest.mark.asyncio
async def test_websocket_unknown_message(client):
    with client.websocket_connect("/ws?token=test_token") as websocket:
        ws_message = WebSocketMessage(type="unknown_type", payload={})
        websocket.send_text(ws_message.json())
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Unknown message type" in response["payload"]["message"]

@pytest.mark.asyncio
async def test_websocket_invalid_json(client):
    with client.websocket_connect("/ws?token=test_token") as websocket:
        websocket.send_text("invalid json")
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Invalid JSON format" in response["payload"]["message"]
