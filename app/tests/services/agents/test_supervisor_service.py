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
    tool_dispatcher = MagicMock()
    return Supervisor(db_session, llm_manager, manager, tool_dispatcher)

@pytest.mark.asyncio
async def test_supervisor_end_to_end(supervisor, monkeypatch):
    # Mock the sub-agents' execute methods to prevent actual execution
    for agent in supervisor.sub_agents:
        monkeypatch.setattr(agent, "execute", AsyncMock())
        agent.set_state = MagicMock()

    analysis_request = AnalysisRequest(settings=Settings(debug_mode=True), request_model=RequestModel(user_id="test_user", query="Test request", workloads=[]))
    run_id = "test_run"

    # Run the supervisor - the main test is that this doesn't crash
    final_state = await supervisor.run(analysis_request.request_model.query, run_id, False)

    # Assert that the supervisor completed successfully without crashing
    assert final_state is not None
    # Verify it's a DeepAgentState object with user_request
    assert hasattr(final_state, 'user_request')
    assert final_state.user_request == "Test request"