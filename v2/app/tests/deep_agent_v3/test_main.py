import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.deep_agent_v3.main import DeepAgentV3
from app.services.deep_agent_v3.scenario_finder import ScenarioFinder
from app.config import AppConfig, LLMConfig, LangfuseConfig


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_llm_manager():
    return MagicMock(spec=LLMManager)


@pytest.fixture
def mock_request():
    return AnalysisRequest(
        user_id="test_user",
        workloads=[{"run_id": "test_run_id", "query": "test_query"}],
        query=json.dumps({"query": "test_query"}),
    )


@pytest.mark.asyncio
async def test_run(mock_request, mock_llm_manager, mock_db_session):
    # Given
    run_id = str(uuid.uuid4())
    mock_scenario_finder = MagicMock(spec=ScenarioFinder)
    mock_scenario_finder.find_scenario.return_value = {
        "scenario": {
            "name": "test_scenario",
            "steps": ["analyze_request", "propose_solution", "generate_report"],
        },
        "confidence": 0.9,
        "justification": "test_justification",
    }

    with patch("app.services.deep_agent_v3.main.ToolBuilder.build_all") as mock_build_all, patch.object(
        DeepAgentV3, "_init_langfuse", return_value=None
    ):
        mock_tool = MagicMock()
        mock_tool.run = AsyncMock(return_value="tool_result")
        mock_build_all.return_value = {
            "analyze_request": mock_tool,
            "propose_solution": mock_tool,
            "generate_report": mock_tool,
        }

        agent = DeepAgentV3(
            run_id=run_id,
            request=mock_request,
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            scenario_finder=mock_scenario_finder,
        )
        agent.agent_core.decide_next_step = MagicMock(
            return_value={"tool_name": "test_tool", "tool_input": {}}
        )

    # When
    with patch(
        "app.services.deep_agent_v3.main.DeepAgentV3._generate_and_save_run_report",
        new_callable=AsyncMock,
    ):
        final_state = await agent.run()

    # Then
    assert agent.status == "complete"
    assert final_state is not None
    assert len(final_state.messages) == 4
    assert final_state.messages[0]["content"] == "Scenario identified: test_scenario"
    assert final_state.messages[1]["content"] == '"tool_result"'
    assert final_state.messages[2]["content"] == '"tool_result"'
    assert final_state.messages[3]["content"] == '"tool_result"'

@pytest.fixture
def mock_settings():
    return AppConfig(
        llm_configs={
            "default": LLMConfig(
                provider="google",
                model_name="gemini-1.5-flash-latest",
                api_key="test_api_key"
            )
        },
        langfuse=LangfuseConfig(
            public_key="test_public_key",
            secret_key="test_secret_key",
            host="https://cloud.langfuse.com/"
        )
    )

def test_deep_agent_v3_initialization_with_settings(mock_settings):
    with patch("app.services.deep_agent_v3.main.settings", mock_settings):
        mock_db_session = MagicMock()
        mock_llm_manager = LLMManager(settings=mock_settings)

        agent = DeepAgentV3(
            run_id="test_run",
            request=MagicMock(),
            db_session=mock_db_session,
            llm_manager=mock_llm_manager
        )

        assert agent.llm_manager is not None
        assert agent.langfuse is not None
