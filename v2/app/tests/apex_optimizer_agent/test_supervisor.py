
import pytest
import unittest
from unittest.mock import MagicMock, AsyncMock
from app.services.apex_optimizer_agent.supervisor import NetraOptimizerAgentSupervisor
from app.db.models_clickhouse import AnalysisRequest

@pytest.mark.asyncio
async def test_start_agent():
    # Mock the dependencies
    mock_db_session = MagicMock()
    mock_llm_manager = MagicMock()
    mock_graph = MagicMock()
    
    # Mock the graph's astream method to be an async generator
    mock_graph.astream = AsyncMock()

    async def async_gen(*args, **kwargs):
        yield {"final_answer": "The agent has finished."}

    mock_graph.astream.return_value = async_gen()()

    # Mock the Team and its create_graph method
    with unittest.mock.patch('app.services.apex_optimizer_agent.supervisor.Team') as mock_team_class:
        mock_team_instance = mock_team_class.return_value
        mock_team_instance.create_graph.return_value = mock_graph

        # Instantiate the supervisor
        supervisor = NetraOptimizerAgentSupervisor(mock_db_session, mock_llm_manager)

        # Create a mock request
        request = AnalysisRequest(query="test query", user_id="test_user")

        # Call the method to be tested
        result = await supervisor.start_agent(request)

        # Assert that the graph was streamed with the correct initial state
        mock_graph.astream.assert_called_once()
        call_args, call_kwargs = mock_graph.astream.call_args
        assert call_args[0]["messages"][0].content == "test query"

        # Assert that the result is the final event from the stream
        assert result == {"final_answer": "The agent has finished."}
