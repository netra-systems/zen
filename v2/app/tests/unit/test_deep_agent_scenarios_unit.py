
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest

@pytest.fixture
def mock_db_session():
    """Provides a mock database session."""
    session = MagicMock()
    session.info = {"user_id": "test_user"}
    return session

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    connector = MagicMock()
    connector.generate_text_async = AsyncMock(return_value='{"key": "value"}')
    return connector

@pytest.mark.parametrize("scenario_prompt", [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
])
@pytest.mark.asyncio
async def test_deep_agent_scenario_unit(scenario_prompt: str, mock_db_session, mock_llm_connector):
    run_id = f"test-run-{hash(scenario_prompt)}"
    agent_request = AnalysisRequest(
        run_id=run_id,
        query=scenario_prompt,
        data_source={
            "source_table": "default.synthetic_data",
            "filters": {},
        },
        time_range={
            "start_time": "2025-08-03T00:00:00Z",
            "end_time": "2025-08-04T00:00:00Z",
        },
    )

    agent = DeepAgentV3(run_id=run_id, request=agent_request, db_session=mock_db_session, llm_connector=mock_llm_connector)

    with patch.object(agent.tools['log_fetcher'], 'execute', new_callable=AsyncMock) as mock_fetch,
         patch.object(agent.tools['log_pattern_identifier'], 'execute', new_callable=AsyncMock) as mock_identify,
         patch.object(agent.tools['policy_proposer'], 'execute', new_callable=AsyncMock) as mock_propose:

        mock_fetch.return_value = [MagicMock()]
        mock_identify.return_value = [MagicMock()]
        mock_propose.return_value = [MagicMock()]

        final_report = await agent.run_full_analysis()

        assert agent.is_complete()
        assert "Analysis Complete" in final_report
