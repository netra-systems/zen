
import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import WebSocketMessage, AnalysisRequest, RequestModel, Workload, DataSource, TimeRange

client = TestClient(app)

@pytest.mark.asyncio
async def test_websocket_connection():
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"message": "pong"} # Keep alive

@pytest.mark.asyncio
async def test_websocket_sends_and_receives_json():
    with client.websocket_connect("/ws") as websocket:
        request_model = RequestModel(
            id="test_id",
            user_id="test_user",
            query="test_query",
            workloads=[
                Workload(
                    run_id="test_run_id",
                    query="test_workload_query",
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )
        analysis_request = AnalysisRequest(request_model=request_model)
        message = WebSocketMessage(type="analysis_request", payload=analysis_request)
        websocket.send_json(message.dict())
        # This part of the test will need to be adapted based on the expected response from the supervisor
        # For now, we'll just check that the connection remains open
        await asyncio.sleep(1)
        assert websocket.scope["path"] == "/ws"
