
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.agent_service import AgentService
from app.db.models_clickhouse import AnalysisRequest

@pytest.mark.asyncio
async def test_start_agent():
    # Arrange
    mock_supervisor = MagicMock()
    mock_supervisor.start_agent = AsyncMock(return_value={"status": "started"})
    agent_service = AgentService(mock_supervisor)
    analysis_request = AnalysisRequest(query="test query", user_id="test_user")

    # Act
    result = await agent_service.start_agent(analysis_request, "test_client")

    # Assert
    assert result == {"status": "started"}
    mock_supervisor.start_agent.assert_called_once_with(analysis_request, "test_client")
