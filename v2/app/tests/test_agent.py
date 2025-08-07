
import pytest
from unittest.mock import patch, AsyncMock
import uuid
import datetime

from app.main import app
from app.db.models_postgres import User
from app.dependencies import get_current_user
from app.services.agent_service import AgentService
from fastapi.testclient import TestClient

@pytest.fixture
def authenticated_client():
    mock_user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        full_name="Test User",
        hashed_password="test_password",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        picture="http://example.com/pic.jpg"
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
@patch('app.routes.agent.get_agent_service')
async def test_start_agent_success(mock_get_agent_service, authenticated_client):
    mock_agent_service = AsyncMock(spec=AgentService)
    mock_get_agent_service.return_value = mock_agent_service
    analysis_request = {
        "settings": {"debug_mode": True},
        "request": {
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
    client_id = "test_client"

    response = authenticated_client.post(f"/api/v3/agent/chat/start_agent/{client_id}", json=analysis_request)

    assert response.status_code == 200
    mock_agent_service.start_agent.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.routes.agent.get_agent_service')
async def test_start_agent_failure(mock_get_agent_service, authenticated_client):
    mock_agent_service = AsyncMock(spec=AgentService)
    mock_agent_service.start_agent.side_effect = Exception("Agent start failed")
    mock_get_agent_service.return_value = mock_agent_service
    analysis_request = {
        "settings": {"debug_mode": True},
        "request": {
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
    client_id = "test_client"

    response = authenticated_client.post(f"/api/v3/agent/chat/start_agent/{client_id}", json=analysis_request)

    assert response.status_code == 500
    assert response.json() == {"detail": "Agent start failed"}

@pytest.mark.asyncio
async def test_websocket_endpoint():
    run_id = "test_run"
    with patch('app.services.agent_service.AgentService.handle_websocket', new_callable=AsyncMock) as mock_handle_websocket:
        with TestClient(app).websocket_connect(f"/api/v3/agent/chat/{run_id}?token=test_token") as websocket:
            pass
    mock_handle_websocket.assert_awaited_once()
