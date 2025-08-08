
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.services.deepagents.supervisor import Supervisor
from app.llm.llm_manager import LLMManager
from app.connection_manager import ConnectionManager
from app.schemas import AnalysisRequest, Settings, RequestModel, DataSource, TimeRange, Workload
from app.services.deepagents.state import DeepAgentState

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_llm_manager():
    return MagicMock(spec=LLMManager)

@pytest.fixture
def mock_connection_manager():
    return MagicMock(spec=ConnectionManager)

@pytest.fixture
def supervisor(mock_db_session, mock_llm_manager, mock_connection_manager):
    return Supervisor(mock_db_session, mock_llm_manager, mock_connection_manager)

@pytest.mark.asyncio
async def test_supervisor_workflow(supervisor: Supervisor):
    analysis_request = AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(
            user_id="test_user",
            query="test_query",
            workloads=[
                Workload(
                    run_id="test_run_123",
                    query="test_workload_query",
                    data_source={"source_table": "test_table"},
                    time_range={"start_time": "2025-01-01T00:00:00Z", "end_time": "2025-01-02T00:00:00Z"}
                )
            ]
        )
    )
    run_id = "test_run_123"

    # Mock the graph's astream method to simulate the workflow
    async def mock_astream(initial_state):
        # Triage
        state = initial_state.copy()
        state["current_agent"] = "TriageSubAgent"
        state["messages"].append(MagicMock(content="Triage complete"))
        yield state

        # Data
        state = state.copy()
        state["current_agent"] = "DataSubAgent"
        state["messages"].append(MagicMock(content="Data processing complete"))
        yield state

        # Optimization
        state = state.copy()
        state["current_agent"] = "OptimizationsCoreSubAgent"
        state["messages"].append(MagicMock(content="Optimization analysis complete"))
        yield state

        # Actions
        state = state.copy()
        state["current_agent"] = "ActionsToMeetGoalsSubAgent"
        state["messages"].append(MagicMock(content="Actions formulated"))
        yield state

        # Reporting
        state = state.copy()
        state["current_agent"] = "ReportingSubAgent"
        state["messages"].append(MagicMock(content="Report generated"))
        yield state

    supervisor.graph.astream = mock_astream
    supervisor.manager.send_to_run = AsyncMock()

    final_state = await supervisor.start_agent(analysis_request, run_id, stream_updates=True)

    assert final_state is not None
    assert final_state["current_agent"] == "ReportingSubAgent"
    assert len(final_state["messages"]) == 5

    # Verify that the connection manager was called to send updates
    assert supervisor.manager.send_to_run.call_count == 5

    calls = supervisor.manager.send_to_run.call_args_list
    assert calls[0].args[0]['data']['agent'] == 'TriageSubAgent'
    assert len(calls[0].args[0]['data']['messages']) == 1

    assert calls[1].args[0]['data']['agent'] == 'DataSubAgent'
    assert len(calls[1].args[0]['data']['messages']) == 2

    assert calls[2].args[0]['data']['agent'] == 'OptimizationsCoreSubAgent'
    assert len(calls[2].args[0]['data']['messages']) == 3

    assert calls[3].args[0]['data']['agent'] == 'ActionsToMeetGoalsSubAgent'
    assert len(calls[3].args[0]['data']['messages']) == 4

    assert calls[4].args[0]['data']['agent'] == 'ReportingSubAgent'
    assert len(calls[4].args[0]['data']['messages']) == 5
