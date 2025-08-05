
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.db.models_clickhouse import AnalysisRequest
from app.services.deep_agent_v3.main import DeepAgentV3



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
def mock_deep_agent_v3():
    with patch('app.routes.deep_agent.DeepAgentV3', autospec=True) as mock_agent:
        mock_instance = mock_agent.return_value
        mock_instance.start_agent = AsyncMock()
        yield mock_agent

def test_cost_optimization_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()

def test_latency_optimization_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()

def test_scalability_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()

def test_code_optimization_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()

def test_model_evaluation_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()

def test_system_audit_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()

def test_multi_objective_optimization_scenario(client: TestClient, mock_db_session, mock_llm_manager, mock_deep_agent_v3):
    # Given
    request_data = {
        "user_id": "test_user",
        "query": "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
    }

    # When
    response = client.post("/api/v3/agent/start", json=request_data)

    # Then
    assert response.status_code == 202
    mock_deep_agent_v3.assert_called_once()
    agent_instance = mock_deep_agent_v3.return_value
    agent_instance.start_agent.assert_awaited_once()
