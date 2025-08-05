import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest
from app.services.deep_agent_v3.pipeline import Pipeline

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def mock_llm_connector():
    return MagicMock()

@pytest.fixture
def mock_request():
    return AnalysisRequest(
        user_id="test_user",
        workloads=[{"run_id": "test_run_id", "query": "test_query"}],
        query="test_query",
    )

@pytest.fixture
def mock_pipeline_for_full_analysis():
    mock_pipeline_instance = MagicMock(spec=Pipeline)
    mock_pipeline_instance.is_complete.side_effect = [False, True]
    mock_pipeline_instance.run_next_step = AsyncMock(return_value={"status": "success", "completed_step": "mock_step"})
    mock_pipeline_instance.get_current_step_name.return_value = "mock_step"
    return mock_pipeline_instance

@pytest.fixture
def mock_pipeline_for_next_step():
    mock_pipeline_instance = MagicMock(spec=Pipeline)
    mock_pipeline_instance.is_complete.return_value = False
    mock_pipeline_instance.run_next_step = AsyncMock(return_value={"status": "success", "completed_step": "mock_step"})
    mock_pipeline_instance.get_current_step_name.return_value = "mock_step"
    return mock_pipeline_instance

@pytest.mark.asyncio
async def test_run_full_analysis(mock_request, mock_db_session, mock_llm_connector, mock_pipeline_for_full_analysis):
    # Given
    with patch('app.services.deep_agent_v3.main.ToolBuilder.build_all'), \
         patch('app.services.deep_agent_v3.main.ScenarioFinder'), \
         patch.object(DeepAgentV3, '_init_langfuse', return_value=None):

        agent = DeepAgentV3(
            run_id="test_run_id",
            request=mock_request,
            db_session=mock_db_session,
            llm_connector=mock_llm_connector,
        )
        agent.pipeline = mock_pipeline_for_full_analysis

    # When
    with patch('app.services.deep_agent_v3.main.DeepAgentV3._generate_and_save_run_report', new_callable=AsyncMock):
        final_state = await agent.run_full_analysis()

    # Then
    assert agent.status == "complete"
    assert agent.pipeline.run_next_step.call_count == 1
    assert final_state is not None

@pytest.mark.asyncio
async def test_run_next_step(mock_request, mock_db_session, mock_llm_connector, mock_pipeline_for_next_step):
    # Given
    with patch('app.services.deep_agent_v3.main.ToolBuilder.build_all'), \
         patch('app.services.deep_agent_v3.main.ScenarioFinder'), \
         patch.object(DeepAgentV3, '_init_langfuse', return_value=None):

        agent = DeepAgentV3(
            run_id="test_run_id",
            request=mock_request,
            db_session=mock_db_session,
            llm_connector=mock_llm_connector,
        )
        agent.pipeline = mock_pipeline_for_next_step

    # When
    result = await agent.run_next_step()

    # Then
    assert result["status"] == "success"
    agent.pipeline.run_next_step.assert_called_once()