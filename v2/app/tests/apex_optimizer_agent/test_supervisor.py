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
    
    # Mock the graph's astart method
    mock_graph.astart = AsyncMock()

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

        # Assert that the graph was started with the correct initial state
        mock_graph.astart.assert_awaited_once()
        call_args, call_kwargs = mock_graph.astart.call_args
        assert call_args[0]["messages"][0].content == "test query"
        assert call_args[0]["todo_list"] == ["triage_request"]

        # Assert that the result is the initial response
        assert result == {"status": "agent_started", "request_id": analysis_request.request.id}
