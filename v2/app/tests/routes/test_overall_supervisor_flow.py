
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from app.services.deepagents.overall_supervisor import OverallSupervisor
from app.db.models_clickhouse import AnalysisRequest, Settings, RequestModel

@pytest.mark.asyncio
async def test_overall_supervisor_flow():
    # Mock dependencies
    db_session = Mock()
    llm_manager = Mock()
    websocket_manager = Mock()

    # Create an instance of the OverallSupervisor
    supervisor = OverallSupervisor(db_session, llm_manager, websocket_manager)

    # Mock the sub-agents and their responses
    mock_triage_agent = Mock()
    mock_triage_agent.as_runnable.return_value = AsyncMock(return_value={"messages": ["Triage complete"], "next_node": "data"})
    supervisor.sub_agents["triage"] = mock_triage_agent

    mock_data_agent = Mock()
    mock_data_agent.as_runnable.return_value = AsyncMock(return_value={"messages": ["Data gathered"], "next_node": "optimizations_core"})
    supervisor.sub_agents["data"] = mock_data_agent

    mock_optimization_agent = Mock()
    mock_optimization_agent.as_runnable.return_value = AsyncMock(return_value={"messages": ["Optimization proposed"], "next_node": "actions_to_meet_goals"})
    supervisor.sub_agents["optimizations_core"] = mock_optimization_agent

    mock_action_agent = Mock()
    mock_action_agent.as_runnable.return_value = AsyncMock(return_value={"messages": ["Actions formulated"], "next_node": "reporting"})
    supervisor.sub_agents["actions_to_meet_goals"] = mock_action_agent

    mock_reporting_agent = Mock()
    mock_reporting_agent.as_runnable.return_value = AsyncMock(return_value={"messages": ["Report generated"], "next_node": "END"})
    supervisor.sub_agents["reporting"] = mock_reporting_agent

    # Create a mock analysis request
    analysis_request = AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(user_id="test_user", query="test query", workloads=[])
    )

    # Start the agent
    run_id = "test_run_id"
    await supervisor.start_agent(analysis_request, run_id)

    # Wait for the agent to complete
    await asyncio.sleep(1)

    # Assert that the flow was correct
    assert supervisor.agent_states[run_id]["messages"][-1] == "Report generated"
