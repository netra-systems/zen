import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import AnalysisRequest, Settings, RequestModel, Workload, DataSource, TimeRange
from app.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_websocket_connection(client):
    # Authenticate and get the session cookie
    response = client.get("/api/v3/auth/google", allow_redirects=False)
    assert response.status_code == 307
    redirect_url = response.headers["location"]
    
    # In a real test environment, you would mock the Google OAuth2 flow.
    # For this test, we'll simulate the callback with a development user.
    state = redirect_url.split("state=")[1].split("&")[0]
    callback_url = f"/auth/callback?state={state}&code=test_code"
    response = client.get(callback_url, allow_redirects=False)
    assert response.status_code == 307
    
    run_id = "test_run_ws"
    with client.websocket_connect(f"/ws/{run_id}") as websocket:
        # Send a sample analysis request
        settings = Settings(debug_mode=True)
        request_model = RequestModel(
            user_id="test_user",
            query="Analyze my data and suggest optimizations.",
            workloads=[
                Workload(
                    run_id=run_id,
                    query="Test workload query",
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )
        analysis_request = AnalysisRequest(settings=settings, request=request_model)
        websocket.send_text(analysis_request.json())

        # Check for the agent started message
        data = websocket.receive_json()
        assert data["event"] == "agent_started"
        assert data["run_id"] == run_id

        # Check for the agent step started messages
        for i in range(5):
            data = websocket.receive_json()
            assert data["event"] == "agent_step_started"
            assert data["run_id"] == run_id

            data = websocket.receive_json()
            assert data["event"] == "agent_step_finished"
            assert data["run_id"] == run_id
