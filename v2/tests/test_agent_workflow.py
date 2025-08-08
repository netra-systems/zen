import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from app.main import app
from app.services.deepagents.supervisor import Supervisor
from app.schemas import AnalysisRequest, RequestModel, ChatMessage, ChatMessageData, User
from app.auth.auth_dependencies import ActiveUserWsDep
from app.websocket import websocket_endpoint

@pytest.fixture
def mock_user():
    return User(id="test_user", email="test@example.com")

@pytest.mark.asyncio
async def test_agent_workflow(mock_user):
    # Mock the Supervisor
    mock_supervisor = MagicMock(spec=Supervisor)
    mock_supervisor.start_agent = AsyncMock()

    # Mock the WebSocket
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.receive_text = AsyncMock(return_value=AnalysisRequest(
        settings={"debug_mode": True},
        request=RequestModel(
            user_id="test_user",
            query="test query",
            workloads=[],
        )
    ).json())
    mock_websocket.send_text = AsyncMock()

    # Call the websocket_endpoint function directly
    await websocket_endpoint(mock_websocket, "test_run_id", mock_user, mock_supervisor)

    # Add assertions here to verify the behavior of the Supervisor
    mock_supervisor.start_agent.assert_called_once()

@pytest.mark.asyncio
async def test_sub_agent_workflow():
    # Mock the LLMManager
    mock_llm_manager = MagicMock()
    mock_llm_manager.arun = AsyncMock(return_value=MagicMock(content="DataSubAgent"))

    # Mock the WebSocketManager
    mock_ws_manager = MagicMock()
    mock_ws_manager.send_to_run = AsyncMock()

    # Create a Supervisor instance with the mocked dependencies
    supervisor = Supervisor(db_session=MagicMock(), llm_manager=mock_llm_manager, manager=mock_ws_manager)

    # Create a test request
    analysis_request = AnalysisRequest(
        settings={"debug_mode": True},
        request=RequestModel(
            user_id="test_user",
            query="test query",
            workloads=[],
        )
    )

    # Start the agent
    with patch('app.services.deepagents.supervisor.ChatMessageData.from_langchain') as mock_from_langchain:
        mock_from_langchain.return_value = ChatMessageData(
            sub_agent_name="TriageSubAgent",
            ai_message="DataSubAgent"
        )
        await supervisor.start_agent(analysis_request, "test_run_id", stream_updates=True)

    # Add assertions to verify the workflow
    assert mock_llm_manager.arun.call_count == 5
    assert mock_ws_manager.send_to_run.call_count == 5
