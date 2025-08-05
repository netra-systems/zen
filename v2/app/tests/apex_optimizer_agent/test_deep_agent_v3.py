import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.main import app
from app.db.models_clickhouse import AnalysisRequest

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_db_session():
    with patch('app.dependencies.get_db_session') as mock_get_db:
        mock_session = MagicMock(spec=Session)
        mock_get_db.return_value = mock_session
        yield mock_session

@pytest.fixture
def mock_llm_manager():
    with patch('app.dependencies.get_llm_manager') as mock_get_llm_manager:
        mock_llm_manager_instance = MagicMock()
        mock_get_llm_manager.return_value = mock_llm_manager_instance
        yield mock_llm_manager_instance

@pytest.fixture
def mock_supervisor():
    with patch('app.routes.apex_optimizer_agent_route.NetraOptimizerAgentSupervisor', autospec=True) as mock_supervisor_class:
        mock_supervisor_instance = mock_supervisor_class.return_value
        mock_supervisor_instance.start_agent = AsyncMock(return_value={"result": "success"})
        yield mock_supervisor_instance

async def test_start_agent_route(client: TestClient, mock_db_session, mock_llm_manager, mock_supervisor):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms."
    }
    analysis_request = AnalysisRequest(**request_data)

    # When
    response = client.post("/apex/start_agent", json=analysis_request.model_dump())

    # Then
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
    mock_supervisor.start_agent.assert_awaited_once_with(analysis_request)
