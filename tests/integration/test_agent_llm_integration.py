import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from netra_backend.app.main import app
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.services.agent_service import AgentService

client = TestClient(app)


@pytest.fixture
def mock_supervisor():
    mock = MagicMock(spec=SupervisorAgent)
    mock.get_agent_state = AsyncMock(return_value={"status": "completed"})
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_agent_service():
    mock = MagicMock(spec=AgentService)
    mock.process_message = AsyncMock(return_value={"response": "mocked response"})
    return mock


@pytest.fixture(autouse=True)
def override_dependencies(mock_supervisor, mock_agent_service):
    app.dependency_overrides[get_agent_supervisor] = lambda: mock_supervisor
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    yield
    app.dependency_overrides = {}


def test_run_agent(mock_supervisor):
    response = client.post(
        "/api/agent/run_agent", json={"query": "test query", "id": "test_run_id"}
    )
    assert response.status_code == 200
    assert response.json() == {"run_id": "test_run_id", "status": "started"}
    mock_supervisor.run.assert_called_once()


def test_get_agent_status(mock_supervisor):
    response = client.get("/api/agent/test_run_id/status")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_process_agent_message(mock_agent_service):
    response = client.post("/api/agent/message", json={"message": "test message"})
    assert response.status_code == 200
    assert response.json() == {"response": "mocked response"}
