import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import RequestModel, Workload, DataSource, TimeRange

client = TestClient(app)

@pytest.mark.asyncio
async def test_websocket_connection():
    with client.websocket_connect("/ws/ws?token=testtoken") as websocket:
        # The first message is a keep-alive ping/pong, so we handle that.
        # In a real test, you might want to mock the supervisor and check its calls.
        pass

@pytest.mark.asyncio
async def test_analysis_request():
    with client.websocket_connect("/ws/ws?token=testtoken") as websocket:
        request_model = RequestModel(
            id="test_run_123",
            user_id="test_user",
            query="test query",
            workloads=[
                Workload(
                    run_id="test_run_123",
                    query="test query",
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )
        message = {
            "type": "analysis_request",
            "payload": {"request_model": request_model.dict()}
        }
        websocket.send_json(message)
        # In a real test, you would mock the supervisor and assert it was called
        # with the correct arguments.
        # For now, we just check that the websocket doesn't close unexpectedly.
        # This is a very basic test.
        await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_invalid_message_format():
    with client.websocket_connect("/ws/ws?token=testtoken") as websocket:
        websocket.send_json({"type": "invalid_type"})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Unknown message type" in response["payload"]["message"]

@pytest.mark.asyncio
async def test_validation_error():
    with client.websocket_connect("/ws/ws?token=testtoken") as websocket:
        websocket.send_json({"type": "analysis_request", "payload": {}})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Invalid message format" in response["payload"]["message"]