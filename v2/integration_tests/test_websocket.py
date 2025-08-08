import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (AnalysisRequest, RequestModel, Workload, DataSource, TimeRange, 
                     WebSocketMessage, User, Settings, AgentStarted, AgentCompleted)
from app.config import settings
from app.auth.auth_dependencies import ActiveUserWsDep
from app.agents.supervisor import Supervisor
import uuid
from unittest.mock import AsyncMock

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_supervisor(monkeypatch):
    mock = AsyncMock(spec=Supervisor)
    mock.run.return_value = {"result": "mocked result"}
    monkeypatch.setattr("app.ws_manager.get_agent_supervisor", lambda: mock)
    return mock

def test_websocket_analysis_request(client, mock_supervisor):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[ActiveUserWsDep] = lambda: User(id=user_id, email="dev@example.com", is_superuser=False)
    
    with client.websocket_connect(f"/ws") as websocket:
        request_model = RequestModel(
            id="test_req",
            user_id=user_id,
            query="Analyze my data and suggest optimizations.",
            workloads=[
                Workload(
                    run_id="test_run",
                    query="Test workload query",
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )
        
        analysis_request_payload = AnalysisRequest(request_model=request_model)
        ws_message = WebSocketMessage(type="analysis_request", payload=analysis_request_payload)
        
        websocket.send_text(ws_message.json())

        # Check for agent_started message
        response = websocket.receive_json()
        assert response["type"] == "agent_started"
        assert response["payload"]["run_id"] == "test_req"

        # Check for agent_completed message
        response = websocket.receive_json()
        assert response["type"] == "agent_completed"
        assert response["payload"]["run_id"] == "test_req"
        assert response["payload"]["result"] == {"result": "mocked result"}

        # For a simple keep-alive, we can check for a pong response.
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response == "pong"