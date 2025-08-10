from fastapi import HTTPException
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agents.supervisor import Supervisor
from app.auth.auth_dependencies import ActiveUserDep
from app.schemas import User
from app.routes.agent_route import get_agent_supervisor
import uuid

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def agent_service_mock():
    return MagicMock(spec=Supervisor)

@pytest.mark.asyncio
async def test_start_agent(client, agent_service_mock):
    agent_service_mock.run = AsyncMock(return_value={"run_id": "req_123", "status": "started"})
    app.dependency_overrides[get_agent_supervisor] = lambda: agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="dev@example.com", is_active=True, is_superuser=False)
    response = client.post("/api/agent/run_agent", json={"id": "req_123", "user_id": "user123", "query": "test message", "workloads": []})

    assert response.status_code == 200
    assert response.json()["run_id"] == "req_123"
    assert response.json()["status"] == "started"
    agent_service_mock.run.assert_called_once()

@pytest.mark.asyncio
async def test_start_agent_with_different_messages(client, agent_service_mock):
    agent_service_mock.run = AsyncMock(return_value={"run_id": "test_run", "status": "started"})
    app.dependency_overrides[get_agent_supervisor] = lambda: agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="dev@example.com", is_active=True, is_superuser=False)
    # First message
    response1 = client.post("/api/agent/run_agent", json={"id": "req_123", "user_id": "user123", "query": "first message", "workloads": []})
    assert response1.status_code == 200
    assert response1.json()["run_id"] == "req_123"

    # Second message
    response2 = client.post("/api/agent/run_agent", json={"id": "req_456", "user_id": "user123", "query": "second message", "workloads": []})
    assert response2.status_code == 200
    assert response2.json()["run_id"] == "req_456"

    assert agent_service_mock.run.call_count == 2

@pytest.mark.asyncio
async def test_start_agent_with_empty_message(client, agent_service_mock):
    agent_service_mock.run = AsyncMock(return_value={"run_id": "test_run", "status": "started"})
    app.dependency_overrides[get_agent_supervisor] = lambda: agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="dev@example.com", is_active=True, is_superuser=False)
    response = client.post("/api/agent/run_agent", json={"id": "req_123", "user_id": "user123", "query": "", "workloads": []})

    assert response.status_code == 200
    assert response.json()["run_id"] == "req_123"
    agent_service_mock.run.assert_called_once()

@pytest.mark.asyncio
async def test_start_agent_service_failure(client, agent_service_mock):
    agent_service_mock.run.side_effect = Exception("Agent service failed")
    app.dependency_overrides[get_agent_supervisor] = lambda: agent_service_mock

    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="dev@example.com", is_active=True, is_superuser=False)
    response = client.post("/api/agent/run_agent", json={"id": "req_123", "user_id": "user123", "query": "test message", "workloads": []})

    assert response.status_code == 500
    assert response.json() == {"detail": "Agent service failed"}

@pytest.mark.asyncio
async def test_websocket_connection(client):
    with client.websocket_connect("/api/agent/ws/test_run?token=test_token") as websocket:
        data = websocket.receive_text()
        assert data == "Message for run_id: test_run"

@pytest.mark.asyncio
async def test_start_agent_unauthenticated(client):
    app.dependency_overrides[ActiveUserDep] = lambda: exec('raise HTTPException(status_code=401, detail="Not authenticated")')
    response = client.post("/api/agent/run_agent", json={"id": "req_123", "user_id": "user123", "query": "test message", "workloads": []})

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_start_agent_invalid_request(client):
    app.dependency_overrides[ActiveUserDep] = lambda: User(id=str(uuid.uuid4()), email="dev@example.com", is_active=True, is_superuser=False)
    response = client.post("/api/agent/run_agent", json={"invalid": "request"})

    assert response.status_code == 422