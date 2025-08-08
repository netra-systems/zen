
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.agents.supervisor import Supervisor
from app.schemas import RequestModel, Settings
from app.llm.llm_manager import LLMManager
from app.websocket_manager import WebSocketManager

@pytest.fixture
def mock_llm_manager():
    mock = MagicMock(spec=LLMManager)
    mock.arun = AsyncMock()
    mock.ask_llm = AsyncMock(return_value='{}')
    return mock

@pytest.fixture
def mock_manager():
    return MagicMock(spec=WebSocketManager)

@pytest.mark.asyncio
async def test_supervisor_logic(mock_llm_manager, mock_manager):
    # Arrange
    db_session = MagicMock()
    supervisor = Supervisor(db_session, mock_llm_manager, mock_manager)

    request_model = RequestModel(
        id="test_run",
        user_id="test_user",
        query="Analyze my data and generate a report.",
        workloads=[]
    )
    run_id = "test_run"

    # Act
    final_state = await supervisor.run(request_model.model_dump(), run_id, stream_updates=False)

    # Assert
    assert "report_result" in final_state
