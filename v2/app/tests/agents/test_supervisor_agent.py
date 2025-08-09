
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.supervisor import Supervisor

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.fixture
def mock_llm_manager():
    return AsyncMock()

@pytest.fixture
def mock_websocket_manager():
    return AsyncMock()

@pytest.fixture
def mock_tool_dispatcher():
    return AsyncMock()

@pytest.mark.asyncio
async def test_supervisor_runs_sub_agents_in_order(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
    # Arrange
    supervisor = Supervisor(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher)
    
    # Mock the sub-agents
    mock_triage_agent = AsyncMock()
    mock_data_agent = AsyncMock()
    mock_optimization_agent = AsyncMock()
    mock_action_agent = AsyncMock()
    mock_reporting_agent = AsyncMock()
    
    supervisor.sub_agents = [
        mock_triage_agent,
        mock_data_agent,
        mock_optimization_agent,
        mock_action_agent,
        mock_reporting_agent
    ]
    
    input_data = {"query": "test query"}
    run_id = "test_run_id"
    
    # Act
    await supervisor.run(input_data, run_id, stream_updates=False)
    
    # Assert
    mock_triage_agent.run.assert_called_once()
    mock_data_agent.run.assert_called_once()
    mock_optimization_agent.run.assert_called_once()
    mock_action_agent.run.assert_called_once()
    mock_reporting_agent.run.assert_called_once()

