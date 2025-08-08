import pytest
from app.services.deepagents.supervisor import Supervisor
from app.schemas import AnalysisRequest, Settings, RequestModel, Workload, DataSource, TimeRange
from app.llm.llm_manager import LLMManager
from app.config import settings as app_settings
from app.db.postgres import async_session_factory
from app.websocket import manager as websocket_manager

@pytest.mark.asyncio
async def test_subagent_pipeline():
    # Initialize the components
    llm_manager = LLMManager(app_settings)
    supervisor = Supervisor(async_session_factory, llm_manager, websocket_manager)

    # Create a mock analysis request
    settings = Settings(debug_mode=True)
    request_model = RequestModel(
        user_id="test_user",
        query="Analyze my data and suggest optimizations.",
        workloads=[
            Workload(
                run_id="test_run",
                query="Test workload query",
                data_source=DataSource(source_table="test_table"),
                time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
            )
        ]
    )
    analysis_request = AnalysisRequest(settings=settings, request=request_model)

    # Run the supervisor
    result = await supervisor.run(analysis_request, run_id="test_run", stream_updates=False)

    # Assert the final result
    assert "report" in result
    assert "Analysis Report" in result["report"]
    assert "Action Plan for Optimizations" in result["report"]
