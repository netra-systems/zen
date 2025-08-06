import pytest
import unittest
from unittest.mock import MagicMock, AsyncMock
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest, RequestModel, Settings, Workload, DataSource, TimeRange

@pytest.mark.asyncio
async def test_start_agent():
    # Mock the dependencies
    mock_db_session = MagicMock()
    mock_llm_manager = MagicMock()
    mock_graph = MagicMock()
    
    # Mock the graph's astream_events method to be an async generator
    async def mock_astream_events(*args, **kwargs):
        yield {"event": "on_tool_end", "data": {"output": MagicMock()}}

    mock_graph.astream_events = mock_astream_events

    # Mock the SingleAgentTeam and its create_graph method
    with unittest.mock.patch('app.services.apex_optimizer_agent.supervisor.SingleAgentTeam') as mock_team_class:
        mock_team_instance = mock_team_class.return_value
        mock_team_instance.create_graph.return_value = mock_graph

        # Instantiate the supervisor
        supervisor = NetraOptimizerAgentSupervisor(mock_db_session, mock_llm_manager)

        # Create a mock request
        settings = Settings(debug_mode=False)
        workload = Workload(
            run_id="test_run",
            query="test workload query",
            data_source=DataSource(source_table="test_table"),
            time_range=TimeRange(start_time="2024-01-01T00:00:00Z", end_time="2024-01-02T00:00:00Z")
        )
        request_model = RequestModel(
            user_id="test_user",
            query="test query",
            workloads=[workload]
        )
        analysis_request = AnalysisRequest(settings=settings, request=request_model)
        
        # Call the method to be tested
        result = await supervisor.start_agent(analysis_request)

        # Assert that the result is the initial response
        assert result == {"status": "agent_started", "run_id": analysis_request.request.id}

        # Now, run the agent and check the results
        await supervisor.run_agent(analysis_request.request.id)
