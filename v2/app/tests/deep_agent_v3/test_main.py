import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest

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

@pytest.mark.asyncio
async def test_run(mock_request, mock_db_session, mock_llm_connector):
    # Given
    with patch('app.services.deep_agent_v3.main.ToolBuilder.build_all') as mock_build_all, \
         patch('app.services.deep_agent_v3.main.ScenarioFinder') as mock_scenario_finder, \
         patch.object(DeepAgentV3, '_init_langfuse', return_value=None):

        mock_build_all.return_value = {
            "test_tool": MagicMock(run=MagicMock(return_value="tool_result"))
        }
        mock_scenario_finder.return_value.find_scenario.return_value = {
            "scenario": {
                "name": "test_scenario",
                "steps": ["test_tool"]
            },
            "confidence": 0.9,
            "justification": "test_justification"
        }

        agent = DeepAgentV3(
            run_id="test_run_id",
            request=mock_request,
            db_session=mock_db_session,
            llm_connector=mock_llm_connector,
        )
        agent.agent_core.decide_next_step = MagicMock(return_value={"tool_name": "test_tool", "tool_input": {}})

    # When
    with patch('app.services.deep_agent_v3.main.DeepAgentV3._generate_and_save_run_report', new_callable=AsyncMock):
        final_state = await agent.run()

    # Then
    assert agent.status == "complete"
    assert final_state is not None
    assert len(final_state.messages) == 2
    assert final_state.messages[0]["content"] == "Scenario identified: test_scenario"
    assert final_state.messages[1]["content"] == "tool_result"
