import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.supervisor import Supervisor
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher

@pytest.fixture
def mock_llm_manager():
    return MagicMock(spec=LLMManager)

@pytest.fixture
def mock_tool_dispatcher():
    return MagicMock(spec=ToolDispatcher)

@pytest.fixture
def mock_websocket_manager():
    return AsyncMock()

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.mark.asyncio
async def test_agent_flow(mock_llm_manager, mock_tool_dispatcher, mock_websocket_manager, mock_db_session):
    # Arrange
    triage_agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher)
    data_agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
    optimizations_agent = OptimizationsCoreSubAgent(mock_llm_manager, mock_tool_dispatcher)
    actions_agent = ActionsToMeetGoalsSubAgent(mock_llm_manager, mock_tool_dispatcher)
    reporting_agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)

    supervisor = Supervisor(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher)
    supervisor.sub_agents = [triage_agent, data_agent, optimizations_agent, actions_agent, reporting_agent]

    input_data = "test query"
    run_id = "test_run_id"

    # Act
    result = await supervisor.run(input_data, run_id, True)

    # Assert
    assert supervisor.get_state() == "completed"
    assert mock_websocket_manager.send_to_client.call_count == 12 # 1 start, 5*2 sub_agent_updates, 1 completed
