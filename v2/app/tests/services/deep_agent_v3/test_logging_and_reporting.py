import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_postgres import DeepAgentRun

@pytest.mark.asyncio
async def test_logging_and_reporting(mock_db_session, mock_llm_connector, mock_request):
    """Tests that the agent correctly logs step execution and generates a run report."""
    # Arrange
    with patch('app.services.deep_agent_v3.main.ToolBuilder.build_all') as mock_build_all, \
         patch('app.services.deep_agent_v3.main.ScenarioFinder.find_scenario') as mock_find_scenario, \
         patch.object(DeepAgentV3, '_init_langfuse', return_value=None):

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

        agent = DeepAgentV3(run_id="test_run_id", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
        agent.agent_core.decide_next_step = MagicMock(return_value={"tool_name": "test_tool", "tool_input": {}})

        # Act
        with patch('app.logging_config_custom.logger.app_logger.info') as mock_logger, \
             patch('app.services.deep_agent_v3.main.DeepAgentV3._generate_and_save_run_report', new_callable=AsyncMock):
            await agent.run()

        # Assert
        # Check that the logger was called with the correct information
        mock_logger.assert_any_call(json.dumps({
            'run_id': 'test_run_id',
            'step_name': 'test_tool',
            'status': 'success',
            'result': 'tool_result',
            'error': None
        }))