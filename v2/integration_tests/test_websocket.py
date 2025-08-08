import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import AnalysisRequest, RequestModel, Settings

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_websocket_e2e(client):
    run_id = "test_run_ws"
    with client.websocket_connect(f"/ws/{run_id}") as websocket:
        # Send a message to start the agent
        analysis_request = AnalysisRequest(
            settings=Settings(debug_mode=True),
            request=RequestModel(
                id=run_id,
                user_id="test_user",
                query="Analyze my data and generate a report.",
                workloads=[]
            )
        )
        websocket.send_json(analysis_request.dict())

        # Receive updates
        messages = []
        while True:
            try:
                data = websocket.receive_json(timeout=10)
                messages.append(data)
                if data.get("event") == "agent_update" and data.get("data", {}).get("agent") == "__end__":
                    break
            except asyncio.TimeoutError:
                break

        # Verify the updates
        assert len(messages) > 0
        # Add more specific assertions here based on the expected messages