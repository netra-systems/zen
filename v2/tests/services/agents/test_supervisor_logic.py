import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.agents.supervisor import Supervisor
from app.schemas import AnalysisRequest, RequestModel, Settings
from app.llm.llm_manager import LLMManager
from app.connection_manager import WebSocketManager

@pytest.fixture
def mock_llm_manager():
    mock = MagicMock(spec=LLMManager)
    mock.arun = AsyncMock()
    return mock

@pytest.fixture
def mock_manager():
    return MagicMock(spec=WebSocketManager)

@pytest.mark.asyncio
async def test_supervisor_logic(mock_llm_manager, mock_manager):
    # Arrange
    db_session = MagicMock()
    supervisor = Supervisor(db_session, mock_llm_manager, mock_manager)

    analysis_request = AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(
            id="test_run",
            user_id="test_user",
            query="Analyze my data and generate a report.",
            workloads=[]
        )
    )
    run_id = "test_run"

    async def astream_mock(initial_state):
        yield {"current_agent": "TriageSubAgent", "messages": []}
        yield {"current_agent": "DataSubAgent", "messages": []}
        yield {"current_agent": "OptimizationsCoreSubAgent", "messages": []}
        yield {"current_agent": "ActionsToMeetGoalsSubAgent", "messages": []}
        yield {"current_agent": "ReportingSubAgent", "messages": []}
        yield {"current_agent": "__end__", "messages": []}

    supervisor.graph.astream = astream_mock

    # Act
    final_state = await supervisor.run(analysis_request.model_dump(), run_id, stream_updates=True)

    # Assert
    assert final_state["current_agent"] == "__end__"
    assert mock_manager.broadcast_to_client.call_count == 6
