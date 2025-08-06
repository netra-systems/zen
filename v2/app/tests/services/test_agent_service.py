import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.agent_service import AgentService
from app.db.models_clickhouse import AnalysisRequest, Settings, RequestModel, Workload, DataSource, TimeRange

@pytest.mark.asyncio
async def test_start_agent():
    # Arrange
    mock_supervisor = MagicMock()
    mock_supervisor.start_agent = AsyncMock(return_value={"status": "started"})
    agent_service = AgentService(mock_supervisor)
    
    settings = Settings(debug_mode=True)
    workload = Workload(
        run_id="test_run",
        query="test_query",
        data_source=DataSource(source_table="test_table"),
        time_range=TimeRange(start_time="2024-01-01T00:00:00Z", end_time="2024-01-02T00:00:00Z")
    )
    request_model = RequestModel(
        id="test_req",
        user_id="test_user",
        query="test query",
        workloads=[workload]
    )
    analysis_request = AnalysisRequest(settings=settings, request=request_model)

    # Act
    result = await agent_service.start_agent(analysis_request, "test_client")

    # Assert
    assert result == {"status": "started"}
    mock_supervisor.start_agent.assert_called_once_with(analysis_request, "test_client")