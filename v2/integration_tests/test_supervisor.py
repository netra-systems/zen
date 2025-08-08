
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.deepagents.supervisor import Supervisor
from app.schemas import AnalysisRequest, Request, Settings

@pytest.mark.asyncio
async def test_supervisor_runs_all_sub_agents():
    # Create mock objects for the dependencies
    db_session = AsyncMock()
    llm_manager = AsyncMock()
    websocket_manager = MagicMock()
    websocket_manager.send_to_run = AsyncMock()

    # Create a mock for each sub-agent
    triage_sub_agent = AsyncMock()
    data_sub_agent = AsyncMock()
    optimization_sub_agent = AsyncMock()
    action_sub_agent = AsyncMock()
    reporting_sub_agent = AsyncMock()

    # Set the return value for the run method of each sub-agent
    triage_sub_agent.run.return_value = {"message": "Triage complete"}
    data_sub_agent.run.return_value = {"message": "Data processing complete"}
    optimization_sub_agent.run.return_value = {"message": "Optimization complete"}
    action_sub_agent.run.return_value = {"message": "Actions complete"}
    reporting_sub_agent.run.return_value = {"message": "Reporting complete"}

    # Create an instance of the Supervisor
    supervisor = Supervisor(db_session, llm_manager, websocket_manager)

    # Replace the sub-agents in the Supervisor with the mock sub-agents
    supervisor.sub_agents = [
        triage_sub_agent,
        data_sub_agent,
        optimization_sub_agent,
        action_sub_agent,
        reporting_sub_agent,
    ]

    # Create a mock analysis request
    analysis_request = AnalysisRequest(
        settings=Settings(user_id="test_user"),
        request=Request(id="test_run", text="Test request")
    )

    # Start the supervisor
    result = await supervisor.run(analysis_request, "test_run", True)

    # Assert that the run method of each sub-agent was called once
    triage_sub_agent.run.assert_called_once()
    data_sub_agent.run.assert_called_once()
    optimization_sub_agent.run.assert_called_once()
    action_sub_agent.run.assert_called_once()
    reporting_sub_agent.run.assert_called_once()

    # Assert that the final result is correct
    assert result == {"message": "Reporting complete"}
