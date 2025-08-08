import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (AnalysisRequest, RequestModel, Workload, DataSource, TimeRange, 
                     WebSocketMessage, User, Settings)
from app.config import settings
from app.auth.auth_dependencies import ActiveUserWsDep
import uuid

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_websocket_analysis_request(client):
    user_id = str(uuid.uuid4())
    app.dependency_overrides[ActiveUserWsDep] = lambda: User(id=user_id, email="dev@example.com", is_superuser=False)
    
    with client.websocket_connect(f"/ws") as websocket:
        request_model = RequestModel(
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

        # This test only verifies that the message can be sent without errors.
        # To check for a response, we would need a running agent supervisor, 
        # which is outside the scope of this integration test.
        # For a simple keep-alive, we can check for a pong response.
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response == "pong"
