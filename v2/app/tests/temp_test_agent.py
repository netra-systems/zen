import pytest
import os
import asyncio
from unittest.mock import MagicMock
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest, RequestModel, Settings
from langchain_core.messages import AIMessage
from langchain.chat_models.fake import FakeListChatModel

@pytest.mark.asyncio
async def test_start_agent_manually():
    # Set log level for debugging
    os.environ["LOG_LEVEL"] = "INFO"

    # Mock dependencies
    db_session = MagicMock()
    llm_manager = MagicMock()
    llm_manager.get_llm.return_value = FakeListChatModel(responses=[AIMessage(content="Hello, world!")])

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
    supervisor = NetraOptimizerAgentSupervisor(db_session, llm_manager)

    # Start the agent
    response = await supervisor.start_agent(mock_analysis_request)

    print(response)

    # Give the agent some time to run
    await asyncio.sleep(5)

