import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import AnalysisRequest, Settings, RequestModel, Workload, DataSource, TimeRange, WebSocketMessage
from app.config import settings
from app.auth.auth_dependencies import ActiveUserWsDep
from app.schemas import User
import uuid

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_websocket_connection(client):
    app.dependency_overrides[ActiveUserWsDep] = lambda: User(id=str(uuid.uuid4()), email="dev@example.com", is_superuser=False)
    with client.websocket_connect(f"/ws/ws") as websocket:
        # Send a sample analysis request
        settings = Settings(debug_mode=True)
        request_model = RequestModel(
            user_id="test_user",
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
        analysis_request = AnalysisRequest(settings=settings, request=request_model)
        ws_message = WebSocketMessage(type="analysis_request", payload=analysis_request.model_dump())
        websocket.send_text(ws_message.json())

        # Check for the agent started message
        data = websocket.receive_json()
        assert data["event"] == "agent_started"