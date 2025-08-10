import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.schemas import AnalysisRequest, Settings, RequestModel
from langchain_core.messages import AIMessage
from app.agents.base import BaseSubAgent

@pytest.fixture
def supervisor():
    db_session = MagicMock()
    llm_manager = MagicMock()
    # Mock the get_llm method to return a mock with an async ainvoke
    llm_mock = MagicMock()
    llm_mock.ainvoke = AsyncMock(return_value=AIMessage(content=""))
    llm_manager.get_llm.return_value = llm_mock
    manager = MagicMock()
    return Supervisor(db_session, llm_manager, manager)

@pytest.mark.asyncio
async def test_supervisor_end_to_end(supervisor, monkeypatch):
    # Mock the sub-agents and their responses
    monkeypatch.setattr(supervisor.sub_agents[0], "run", AsyncMock(return_value={"messages": [AIMessage(content="Triage complete")], "current_agent": "TriageSubAgent"}))
    monkeypatch.setattr(supervisor.sub_agents[1], "run", AsyncMock(return_value={"messages": [AIMessage(content="Data gathered")], "current_agent": "DataSubAgent"}))
    monkeypatch.setattr(supervisor.sub_agents[2], "run", AsyncMock(return_value={"messages": [AIMessage(content="Optimization complete")], "current_agent": "OptimizationsCoreSubAgent"}))
    monkeypatch.setattr(supervisor.sub_agents[3], "run", AsyncMock(return_value={"messages": [AIMessage(content="Actions created")], "current_agent": "ActionsToMeetGoalsSubAgent"}))
    monkeypatch.setattr(supervisor.sub_agents[4], "run", AsyncMock(return_value={"messages": [AIMessage(content="Report generated")], "current_agent": "ReportingSubAgent"}))

    analysis_request = AnalysisRequest(settings=Settings(debug_mode=True), request=RequestModel(user_id="test_user", query="Test request", workloads=[]))
    run_id = "test_run"

    final_state = await supervisor.run(analysis_request.model_dump(), run_id, False)

    # Assert that the final state is as expected
    assert final_state is not None and final_state['messages'][-1].content == "Report generated"