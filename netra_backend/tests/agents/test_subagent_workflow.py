
import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
        # Return proper JSON strings based on the config or prompt context
        prompt = args[0] if args else ""
        
        # Determine response based on the agent type/prompt
        if "triage" in prompt.lower() or "category" in prompt.lower():
            return '{"category": "Data Analysis", "confidence_score": 0.9}'
        elif "data" in prompt.lower() and "analysis" in prompt.lower():
            return '{"analysis_results": "Sample data analysis"}'
        elif "optimization" in prompt.lower():
            return '{"optimizations": ["Optimization 1"], "cost_savings": 1000}'
        elif "action" in prompt.lower() and "plan" in prompt.lower():
            return '{"action_plan": ["Action 1", "Action 2"], "timeline": "2 weeks"}'
        elif "report" in prompt.lower():
            return '{"report": "Final comprehensive analysis report with detailed findings and recommendations", "report_type": "analysis", "sections": [{"title": "Summary", "content": "Analysis complete"}]}'
        else:
            return '{"status": "completed"}'
    
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

@pytest.mark.asyncio
async def test_subagent_workflow_end_to_end(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
    # Arrange
    # Mock the state persistence to avoid the coroutine issue
    with patch('netra_backend.app.agents.supervisor_consolidated.state_persistence_service') as mock_state_persistence:
        mock_state_persistence.save_agent_state = AsyncMock()
        mock_state_persistence.load_agent_state = AsyncMock(return_value=None)
        # Mock: Async component isolation for testing without real async operations
        mock_state_persistence.get_thread_context = AsyncMock(return_value=None)
        
        supervisor = Supervisor(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher)
        
        # Create a mock reporting agent that properly sets state
        mock_reporting_agent = AsyncMock()
        async def mock_reporting_execute_impl(state, run_id, stream_updates):
            print(f"DEBUG: Mock reporting agent called with state.step_count={state.step_count}")
            from netra_backend.app.agents.state import ReportResult
            state.report_result = ReportResult(
                report_type="analysis", 
                content="Comprehensive analysis report with detailed findings and recommendations",
                sections=[],
                attachments=[],
                generated_at="2023-01-01T00:00:00Z"
            )
            state.step_count += 1
            print(f"DEBUG: Mock reporting agent set report_result={state.report_result}")
            
        mock_reporting_agent.execute.side_effect = mock_reporting_execute_impl
        
        # Replace the reporting agent in the supervisor's registry
        supervisor.registry.agents["reporting"] = mock_reporting_agent

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
        assert result.report_result.content is not None
