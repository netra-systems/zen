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
    
    # Mock the graph's ainvoke method
    mock_graph.ainvoke = AsyncMock()

    # Mock the SingleAgentTeam and its create_graph method
    with unittest.mock.patch('app.services.apex_optimizer_agent.supervisor.SingleAgentTeam') as mock_team_class,         unittest.mock.patch('asyncio.create_task') as mock_create_task:
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

        # Assert that asyncio.create_task was called
        mock_create_task.assert_called_once()

        # Assert that the graph was started with the correct initial state
        mock_graph.ainvoke.assert_called_once()
        call_args, call_kwargs = mock_graph.ainvoke.call_args
        assert call_args[0]["messages"][0].content == "test query"
        assert call_args[0]["todo_list"] == ["triage_request"]

        # Assert that the result is the initial response
        assert result == {"status": "agent_started", "request_id": analysis_request.request.id}
