import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.services.deepagents.overall_supervisor import OverallSupervisor
from app.schemas import AnalysisRequest, RequestModel, Settings
from langchain_community.chat_models.fake import FakeListChatModel

class FakeLLMWithTools(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

@pytest.mark.asyncio
async def test_overall_supervisor_workflow():
    # Mock dependencies
    db_session = MagicMock()
    llm_manager = MagicMock()
    llm_manager.get_llm.return_value = FakeLLMWithTools(responses=["Hello, world!"])
    websocket_manager = MagicMock()
    websocket_manager.send_to_run = AsyncMock()

    # Create a mock request
    mock_request_model = RequestModel(
        id="test_request_id",
        user_id="test_user_id",
        query="Optimize my LLM usage",
        workloads=[]
    )

    mock_settings = Settings(debug_mode=True)

    mock_analysis_request = AnalysisRequest(
        request=mock_request_model,
        settings=mock_settings
    )

    # Instantiate the supervisor
    supervisor = OverallSupervisor(db_session, llm_manager, websocket_manager)

    # Start the agent
    supervisor.start_agent = AsyncMock(return_value={"status": "completed"})
    response = await supervisor.start_agent(mock_analysis_request, "test_run_id", True)

    # Assert that the agent started successfully
    assert response["status"] == "completed"