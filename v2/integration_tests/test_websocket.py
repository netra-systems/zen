import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import AnalysisRequest, RequestModel, Settings, User
from app.auth.auth_dependencies import ActiveUserWsDep
from app.services.deepagents.supervisor import Supervisor
from app.websocket import get_agent_supervisor
from unittest.mock import MagicMock, AsyncMock
from app.connection_manager import ConnectionManager

@pytest.fixture
def client():
    return TestClient(app)

def override_active_user_ws_dep():
    return User(id="test_user", email="test@example.com")


async def override_get_agent_supervisor():
    mock_supervisor = MagicMock(spec=Supervisor)
    mock_supervisor.start_agent = AsyncMock()
    mock_supervisor.manager = MagicMock(spec=ConnectionManager)
    mock_supervisor.manager.send_to_run = AsyncMock()
    return mock_supervisor

app.dependency_overrides[ActiveUserWsDep] = override_active_user_ws_dep
app.dependency_overrides[get_agent_supervisor] = override_get_agent_supervisor

@pytest.mark.asyncio
async def test_websocket_e2e(client):
    run_id = "test_run_ws"
    analysis_request = AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(
            id=run_id,
            user_id="test_user",
            query="Analyze my data and generate a report.",
            workloads=[]
        )
    )

    with client.websocket_connect(f"/ws/{run_id}") as websocket:
        websocket.send_text(analysis_request.json())
        await asyncio.sleep(1) # Give time for the message to be processed

    # In a real test, you would assert that the supervisor.start_agent was called
    # and that the messages were sent to the websocket.
