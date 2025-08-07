import pytest
from unittest.mock import patch, AsyncMock
import uuid
import datetime

from app.main import app
from app.schemas import User
from app.dependencies import get_current_user
from app.services.agent_service import AgentService
from fastapi.testclient import TestClient

@pytest.fixture
def authenticated_client():
    mock_user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
@patch('app.services.agent_service.AgentService.start_agent')
async def test_start_agent_success(mock_start_agent, authenticated_client):
    mock_start_agent.return_value = {"status": "agent_started", "run_id": "test_run"}
    analysis_request = {
        "settings": {"debug_mode": True},
        "request": {
            "id": "test_req",
            "user_id": "test_user",
            "query": "test query",
            "workloads": [
                {
                    "run_id": "test_run",
                    "query": "test query",
                    "data_source": {"source_table": "test_table"},
                    "time_range": {"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-01-02T00:00:00Z"}
                }
            ]
        }
    }

    response = authenticated_client.post("/api/v3/agent/chat/start_agent", json=analysis_request)

    assert response.status_code == 200
    assert response.json() == {"status": "agent_started", "run_id": "test_req"}
    mock_start_agent.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.services.agent_service.AgentService.start_agent')
async def test_start_agent_failure(mock_start_agent, authenticated_client):
    mock_start_agent.side_effect = HTTPException(status_code=500, detail="Agent start failed")
    analysis_request = {
        "settings": {"debug_mode": True},
        "request": {
            "id": "test_req",
            "user_id": "test_user",
            "query": "test query",
            "workloads": [
                {
                    "run_id": "test_run",
                    "query": "test query",
                    "data_source": {"source_table": "test_table"},
                    "time_range": {"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-01-02T00:00:00Z"}
                }
            ]
        }
    }

    response = authenticated_client.post("/api/v3/agent/chat/start_agent", json=analysis_request)

    assert response.status_code == 500
    assert response.json() == {"detail": "Agent start failed"}

@pytest.mark.asyncio
async def test_websocket_endpoint(authenticated_client):
    run_id = "test_run"
    with authenticated_client.websocket_connect(f"/ws/{run_id}") as websocket:
        # The connection should be accepted, but there's no message sent from the server
        # immediately upon connection in the current implementation.
        # We can just assert that the connection is accepted.
        pass