from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.agent_service import AgentService
from app.auth_dependencies import ActiveUserDep
from app.db.models_postgres import User

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def agent_service_mock():
    return MagicMock(spec=AgentService)

@pytest.mark.asyncio
async def test_start_agent(client, agent_service_mock):
    agent_service_mock.start_agent = AsyncMock(return_value={"run_id": "test_run"})
    app.state.agent_service = agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(email="dev@example.com", hashed_password="test")
    response = client.post("/api/v3/agent/chat/start_agent/client123", json={"settings": {"debug_mode": True}, "request": {"id": "req_123", "user_id": "user123", "query": "test message", "workloads": []}})

    assert response.status_code == 200
    assert response.json() == {"run_id": "test_run"}
    agent_service_mock.start_agent.assert_called_once()

@pytest.mark.asyncio
async def test_start_agent_with_different_messages(client, agent_service_mock):
    agent_service_mock.start_agent = AsyncMock(return_value={"run_id": "test_run"})
    app.state.agent_service = agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(email="dev@example.com", hashed_password="test")
    # First message
    response1 = client.post("/api/v3/agent/chat/start_agent/client123", json={"settings": {"debug_mode": True}, "request": {"id": "req_123", "user_id": "user123", "query": "first message", "workloads": []}})
    assert response1.status_code == 200
    assert response1.json() == {"run_id": "test_run"}

    # Second message
    response2 = client.post("/api/v3/agent/chat/start_agent/client123", json={"settings": {"debug_mode": True}, "request": {"id": "req_123", "user_id": "user123", "query": "second message", "workloads": []}})
    assert response2.status_code == 200
    assert response2.json() == {"run_id": "test_run"}

    assert agent_service_mock.start_agent.call_count == 2

@pytest.mark.asyncio
async def test_start_agent_with_empty_message(client, agent_service_mock):
    agent_service_mock.start_agent = AsyncMock(return_value={"run_id": "test_run"})
    app.state.agent_service = agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(email="dev@example.com", hashed_password="test")
    response = client.post("/api/v3/agent/chat/start_agent/client123", json={"settings": {"debug_mode": True}, "request": {"id": "req_123", "user_id": "user123", "query": "", "workloads": []}})

    assert response.status_code == 200
    assert response.json() == {"run_id": "test_run"}
    agent_service_mock.start_agent.assert_called_once()

@pytest.mark.asyncio
async def test_start_agent_service_failure(client, agent_service_mock):
    agent_service_mock.start_agent.side_effect = Exception("Agent service failed")
    app.state.agent_service = agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(email="dev@example.com", hashed_password="test")
    response = client.post("/api/v3/agent/chat/start_agent/client123", json={"settings": {"debug_mode": True}, "request": {"id": "req_123", "user_id": "user123", "query": "test message", "workloads": []}})

    assert response.status_code == 500
    assert response.json() == {"detail": "Agent service failed"}

@pytest.mark.asyncio
async def test_websocket_connection(client):
    with client.websocket_connect("/api/v3/agent/chat/test_run?token=test_token") as websocket:
        data = websocket.receive_text()
        assert data == "Message for run_id: test_run"

@pytest.mark.asyncio
async def test_start_agent_unauthenticated(client):
    app.dependency_overrides[ActiveUserDep] = lambda: exec('raise HTTPException(status_code=401, detail="Not authenticated")')
    response = client.post("/api/v3/agent/chat/start_agent/client123", json={"settings": {"debug_mode": True}, "request": {"id": "req_123", "user_id": "user123", "query": "test message", "workloads": []}})

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_start_agent_invalid_request(client):
    app.dependency_overrides[ActiveUserDep] = lambda: User(email="dev@example.com", hashed_password="test")
    response = client.post("/api/v3/agent/chat/start_agent/client123", json={"invalid": "request"})

    assert response.status_code == 422