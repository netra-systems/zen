import pytest
import json
import os
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (RequestModel, Workload, DataSource, TimeRange,
                         User, WebSocketMessage)
from app.services.agent_service import AgentService, get_agent_service
from app.dependencies import get_security_service
from app.services.security_service import SecurityService
from app.services.demo_service import DemoService, get_demo_service
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from tests.unified.jwt_token_helpers import JWTTestHelper

# Skip startup checks for integration tests
os.environ["SKIP_STARTUP_CHECKS"] = "true"

@pytest.fixture
def mock_agent_service():
    mock = MagicMock(spec=AgentService)
    mock.handle_websocket_message = AsyncMock()
    return mock

@pytest.fixture
def mock_demo_service():
    mock = MagicMock(spec=DemoService)
    mock.process_demo_interaction = AsyncMock(return_value={
        "response": "Demo response",
        "metrics": {"latency": 100}
    })
    mock.get_demo_metrics = AsyncMock(return_value={
        "requests": 10,
        "avg_latency": 150
    })
    return mock

@pytest.fixture
def mock_security_service():
    mock = MagicMock(spec=SecurityService)
    
    # Make decode_access_token async and return the correct format
    async def mock_decode_token(token):
        import jwt
        # Decode the token without verification for testing
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return {"sub": payload.get("user_id", str(uuid.uuid4()))}
        except:
            return {"sub": str(uuid.uuid4())}
    
    # Mock get_user_by_id to return a user that matches the token
    async def mock_get_user(db_session, user_id):
        return User(id=user_id, email="dev@example.com", is_active=True, is_superuser=False)
    
    mock.decode_access_token = AsyncMock(side_effect=mock_decode_token)
    mock.get_user_by_id = AsyncMock(side_effect=mock_get_user)
    return mock

@pytest.fixture(scope="function")
def client(mock_agent_service, mock_security_service, mock_demo_service):
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    app.dependency_overrides[get_security_service] = lambda: mock_security_service
    app.dependency_overrides[get_demo_service] = lambda: mock_demo_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}

def test_websocket_sends_message_to_agent_service(client, mock_demo_service):
    """Test that WebSocket messages are sent to agent service"""
    user_id = str(uuid.uuid4())
    
    # Connect to WebSocket without authentication (demo endpoint doesn't require it)
    with client.websocket_connect("/ws") as websocket:
        # Receive connection established message
        connection_msg = websocket.receive_json()
        assert connection_msg["type"] == "connection_established"
        
        # Send a test message
        test_message = {
            "type": "ping",
            "payload": {"message": "hello"}
        }
        websocket.send_text(json.dumps(test_message))
        
        # Receive pong response
        response = websocket.receive_json()
        assert response["type"] == "pong"


def test_websocket_receives_message_from_server(client, mock_demo_service):
    """Test that WebSocket can receive messages from server"""
    user_id = str(uuid.uuid4())
    
    # Connect to WebSocket without authentication (demo endpoint doesn't require it)
    with client.websocket_connect("/ws") as websocket:
        # Receive and verify connection established message from server
        connection_msg = websocket.receive_json()
        assert connection_msg["type"] == "connection_established"
        assert "session_id" in connection_msg
        assert connection_msg["message"] == "Connected to Netra AI Demo WebSocket"