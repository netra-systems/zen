import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (AnalysisRequest, RequestModel, Workload, DataSource, TimeRange, 
                     WebSocketMessage, User, Settings, AgentStarted, AgentCompleted)
from app.config import settings
from app.auth.auth_dependencies import CurrentUser
from app.services.agent_service import AgentService, get_agent_service
import uuid
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_agent_service():
    mock = MagicMock(spec=AgentService)
    mock.handle_websocket_message = AsyncMock()
    return mock

@pytest.fixture(scope="function")
def client(mock_agent_service):
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}

def test_websocket_analysis_request(client, mock_agent_service):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[CurrentUser] = lambda: User(id=user_id, email="dev@example.com")
    
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
        
        analysis_request_payload = {"request": request_model.model_dump()}
        ws_message = {"type": "start_agent", "payload": analysis_request_payload}
        
        websocket.send_json(ws_message)

    app.dependency_overrides = {}
