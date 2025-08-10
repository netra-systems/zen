
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.fixture
def mock_llm_manager():
    llm_manager = MagicMock(spec=LLMManager)
    llm_manager.ask_llm = AsyncMock()
    return llm_manager

@pytest.fixture
def mock_websocket_manager():
    return AsyncMock()

@pytest.fixture
def mock_tool_dispatcher():
    return AsyncMock()

@pytest.mark.asyncio
async def test_subagent_workflow_end_to_end(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
    # Arrange
    supervisor = Supervisor(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher)

    # Mock LLM responses for each sub-agent
    mock_llm_manager.ask_llm.side_effect = [
        '{"category": "Data Analysis"}',  # TriageSubAgent
        '{"data": "Sample data"}',         # DataSubAgent
        '{"optimizations": ["Optimization 1"]}',  # OptimizationsCoreSubAgent
        '{"action_plan": ["Action 1"]}', # ActionsToMeetGoalsSubAgent
        '{"report": "Final report"}',      # ReportingSubAgent
    ]

    input_data = "test query"
    run_id = "test_run_id"

    # Act
    result = await supervisor.run(input_data, run_id, stream_updates=False)

    # Assert
    assert result.report_result["report"] == "Final report"
