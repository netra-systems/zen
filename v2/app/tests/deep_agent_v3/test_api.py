import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.db.models_clickhouse import AnalysisRequest
from app.services.deep_agent_v3.main import DeepAgentV3

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    with patch('app.dependencies.get_async_db') as mock_get_db:
        mock_session = MagicMock(spec=Session)
        mock_get_db.return_value = mock_session
        yield mock_session

@pytest.fixture
def mock_llm_connector():
    with patch('app.dependencies.get_llm_connector') as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        yield mock_llm

@pytest.fixture
def mock_deep_agent_v3():
    with patch('app.routes.deep_agent.DeepAgentV3', autospec=True) as mock_agent:
        mock_instance = mock_agent.return_value
        mock_instance.run_full_analysis = AsyncMock()
        yield mock_agent

def test_create_agent_run_success(mock_db_session, mock_llm_connector, mock_deep_agent_v3):
    # Given
    analysis_request = {
        "user_id": "test_user",
        "workloads": [{"run_id": "test_run_id", "query": "test_query"}],
        "query": "test_query",
    }

    # When
    response = client.post("/api/v3/agent/create", json=analysis_request)

    # Then
    assert response.status_code == 202
    assert response.json() == {"run_id": "test_run_id", "message": "Agent run created and started in the background."}
    mock_deep_agent_v3.assert_called_once()

def test_create_agent_run_no_workloads(mock_db_session, mock_llm_connector):
    # Given
    analysis_request = {
        "user_id": "test_user",
        "workloads": [],
        "query": "test_query",
    }

    # When
    response = client.post("/api/v3/agent/create", json=analysis_request)

    # Then
    assert response.status_code == 400
    assert response.json() == {"detail": "No workloads provided in the request."}

def test_get_agent_step_not_found():
    # Given
    run_id = "non_existent_run"

    # When
    response = client.get(f"/api/v3/agent/{run_id}/step")

    # Then
    assert response.status_code == 404
    assert response.json() == {"detail": "Agent run not found."}