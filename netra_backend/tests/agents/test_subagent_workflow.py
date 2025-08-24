
import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest

from netra_backend.app.agents.supervisor_consolidated import (
    SupervisorAgent as Supervisor,
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

@pytest.fixture
def mock_db_session():
    # Mock: Generic component isolation for controlled unit testing
    return AsyncMock()

@pytest.fixture
def mock_llm_manager():
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    llm_manager = MagicMock(spec=LLMManager)
    # Create AsyncMock with proper return values
    async def mock_ask_llm(*args, **kwargs):
        # Return proper JSON strings in sequence
        if not hasattr(mock_ask_llm, 'call_count'):
            mock_ask_llm.call_count = 0
        
        responses = [
            '{"category": "Data Analysis"}',  # TriageSubAgent
            '{"data": "Sample data"}',         # DataSubAgent
            '{"optimizations": ["Optimization 1"]}',  # OptimizationsCoreSubAgent
            '{"action_plan": ["Action 1"]}', # ActionsToMeetGoalsSubAgent
            '{"report": "Final report"}',      # ReportingSubAgent
        ]
        
        if mock_ask_llm.call_count < len(responses):
            response = responses[mock_ask_llm.call_count]
            mock_ask_llm.call_count += 1
            return response
        return '{}'
    
    llm_manager.ask_llm = mock_ask_llm
    return llm_manager

@pytest.fixture
def mock_websocket_manager():
    # Mock: Generic component isolation for controlled unit testing
    return AsyncMock()

@pytest.fixture
def mock_tool_dispatcher():
    # Mock: Generic component isolation for controlled unit testing
    return AsyncMock()

# @pytest.mark.skip(reason="Complex mock setup issues with coroutines - needs refactoring")
@pytest.mark.asyncio
async def test_subagent_workflow_end_to_end(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
    # Arrange
    # Mock the state persistence to avoid the coroutine issue
    with patch('app.agents.supervisor_consolidated.state_persistence_service') as mock_state_persistence:
        mock_state_persistence.save_agent_state = AsyncMock()
        mock_state_persistence.load_agent_state = AsyncMock(return_value=None)
        # Mock: Async component isolation for testing without real async operations
        mock_state_persistence.get_thread_context = AsyncMock(return_value=None)
        
        supervisor = Supervisor(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher)

        input_data = "test query"
        run_id = "test_run_id"
        thread_id = "test_thread_id"
        user_id = "test_user_id"

        # Act
        result = await supervisor.run(input_data, thread_id, user_id, run_id)

        # Assert
        assert result.report_result is not None
        # Verify the workflow completed successfully with proper report structure
        assert result.report_result.report_type == "analysis"
        assert hasattr(result.report_result, 'content')
        assert result.report_result.generated_at is not None
