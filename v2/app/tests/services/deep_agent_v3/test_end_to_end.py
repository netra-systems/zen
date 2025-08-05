import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest


from app.db.session import get_db_session

import uuid

from app.db.session import get_db_session

@pytest.mark.asyncio
async def test_end_to_end_scenario(db_session):
    # Arrange
    run_id = str(uuid.uuid4())
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[{"query": "test_query"}],
        query="test_query"
    )
    llm_connector = MagicMock()

    # Create the agent
    with patch('app.services.deep_agent_v3.main.ToolBuilder.build_all') as mock_build_all, \
         patch('app.services.deep_agent_v3.main.ScenarioFinder.find_scenario', new_callable=AsyncMock) as mock_find_scenario, \
         patch.object(DeepAgentV3, '_init_langfuse', return_value=None), \
         patch('app.services.deep_agent_v3.main.DeepAgentV3._generate_and_save_run_report', new_callable=AsyncMock):

        mock_tool = MagicMock()
        mock_tool.run = MagicMock(return_value="tool_result")
        mock_build_all.return_value = {
            "test_tool": mock_tool
        }
        mock_find_scenario.return_value = {
            "scenario": {
                "name": "test_scenario",
                "steps": ["test_tool"]
            },
            "confidence": 0.9,
            "justification": "test_justification"
        }

        async with get_db_session() as db_session:
            agent = DeepAgentV3(run_id, request, db_session, llm_connector)
            agent.agent_core.decide_next_step = MagicMock(return_value={"tool_name": "test_tool", "tool_input": {}})

            # Act
            result_state = await agent.run()

            # Assert
            assert agent.status == "complete"


