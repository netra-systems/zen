from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.main import app
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.dependencies import get_agent_supervisor, get_llm_manager
from netra_backend.app.services.agent_service import get_agent_service

client = TestClient(app)


@pytest.fixture
def mock_supervisor():
    # Mock: Agent service isolation for testing without LLM agent execution
    mock = MagicMock(spec=SupervisorAgent)
    # Mock: Agent service isolation for testing without LLM agent execution
    mock.get_agent_state = AsyncMock(return_value={"status": "completed"})
    # Mock: Generic component isolation for controlled unit testing
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_agent_service():
    # Mock: Agent service isolation for testing without LLM agent execution
    mock = MagicMock(spec=AgentService)
    # Mock: Async component isolation for testing without real async operations
    mock.process_message = AsyncMock(return_value={"response": "mocked response"})
    return mock


@pytest.fixture
def mock_llm_manager():
    # Mock: LLM manager isolation for testing without real LLM calls
    mock = MagicMock()
    return mock


@pytest.fixture(autouse=True)
def override_dependencies(mock_supervisor, mock_agent_service, mock_llm_manager):
    # Import the actual function to override
    from netra_backend.app.routes.agent_route import get_agent_supervisor as route_get_agent_supervisor
    
    app.dependency_overrides[get_agent_supervisor] = lambda: mock_supervisor
    app.dependency_overrides[route_get_agent_supervisor] = lambda: mock_supervisor
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    app.dependency_overrides[get_llm_manager] = lambda: mock_llm_manager
    yield
    app.dependency_overrides = {}


def test_run_agent(mock_supervisor):
    request_payload = {
        "id": "test_run_id",
        "user_id": "test_user",
        "query": "test query",
        "workloads": [{
            "run_id": "test_workload_run",
            "query": "test workload query",
            "data_source": {
                "source_table": "test_table"
            },
            "time_range": {
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-02T00:00:00Z"
            }
        }]
    }
    response = client.post("/api/agent/run_agent", json=request_payload)
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
