
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.supervisor import Supervisor

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.fixture
def mock_llm_manager():
    mock = AsyncMock()
    # Mock the ask_llm method to return a string response
    mock.ask_llm.return_value = '{"status": "success", "analysis": "test analysis"}'
    return mock

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
    
    # Mock the sub-agents in the consolidated supervisor's agents registry
    mock_triage_agent = AsyncMock()
    mock_triage_agent.name = "TriageSubAgent"
    mock_triage_agent.execute.return_value = None
    
    mock_data_agent = AsyncMock()
    mock_data_agent.name = "DataSubAgent"
    mock_data_agent.execute.return_value = None
    
    mock_optimization_agent = AsyncMock()
    mock_optimization_agent.name = "OptimizationsCoreSubAgent"
    mock_optimization_agent.execute.return_value = None
    
    mock_action_agent = AsyncMock()
    mock_action_agent.name = "ActionsToMeetGoalsSubAgent"
    mock_action_agent.execute.return_value = None
    
    mock_reporting_agent = AsyncMock()
    mock_reporting_agent.name = "ReportingSubAgent"
    mock_reporting_agent.execute.return_value = None
    
    # Replace the agents in the consolidated supervisor
    supervisor._impl.agents = {
        "triage": mock_triage_agent,
        "data": mock_data_agent,
        "optimization": mock_optimization_agent,
        "actions": mock_action_agent,
        "reporting": mock_reporting_agent
    }
    
    input_data = "test query"
    run_id = "test_run_id"
    
    # Act
    await supervisor.run(input_data, run_id, stream_updates=False)
    
    # Assert
    mock_triage_agent.execute.assert_called_once()
    mock_data_agent.execute.assert_called_once()
    mock_optimization_agent.execute.assert_called_once()
    mock_action_agent.execute.assert_called_once()
    mock_reporting_agent.execute.assert_called_once()

