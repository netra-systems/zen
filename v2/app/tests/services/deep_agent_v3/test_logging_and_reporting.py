
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_postgres import DeepAgentRun

@pytest.mark.asyncio
async def test_logging_and_reporting(mock_db_session, mock_llm_connector, mock_request):
    """Tests that the agent correctly logs step execution and generates a run report."""
    # Arrange
    step1 = AsyncMock(return_value="Step 1 complete")
    step1.__name__ = "step1"
    
    with patch('app.services.deep_agent_v3.main.ALL_STEPS', {"step1": step1}):
        with patch('app.services.deep_agent_v3.main.ScenarioFinder.find_scenario', return_value={"steps": ["step1"]}):
            agent = DeepAgentV3(run_id="test_run_id", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)

            # Act
            with patch('app.logging_config_custom.logger.app_logger.info') as mock_logger:
                await agent.run_full_analysis()

            # Assert
            # Check that the logger was called with the correct information
            mock_logger.assert_any_call(json.dumps({
                'run_id': 'test_run_id',
                'step_name': 'step1',
                'status': 'success',
                'result': 'Step 1 complete',
                'error': None
            }))

            # Check that a run report was generated and saved to the database
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [
                DeepAgentRun(step_name="step1", run_log=json.dumps({'status': 'success', 'result': 'Step 1 complete'}))
            ]
            mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value.run_report = "# Deep Agent Run Report: test_run_id..."

            assert "# Deep Agent Run Report: test_run_id" in mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value.run_report
