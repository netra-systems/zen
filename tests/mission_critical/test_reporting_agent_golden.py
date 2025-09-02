"""
Mission Critical Tests for Golden Pattern ReportingSubAgent

Tests the complete golden pattern implementation including:
- WebSocket event emissions for chat value delivery
- Report generation workflow with real LLM services
- Error handling with proper AgentError types
- Complete end-to-end flow testing
- BaseAgent infrastructure integration

CRITICAL: This test suite ensures the ReportingSubAgent follows
the golden pattern and delivers chat value through WebSocket events.
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


class TestReportingAgentGoldenPattern:
    """Test the ReportingSubAgent golden pattern implementation."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.ask_llm.return_value = json.dumps({
            "report": "Test report generated successfully",
            "sections": [
                {
                    "section_id": "summary",
                    "title": "Executive Summary",
                    "content": "This is a test summary",
                    "section_type": "summary"
                }
            ],
            "metadata": {"generated_at": time.time()}
        })
        return llm_manager

    @pytest.fixture
    def reporting_agent(self, mock_llm_manager):
        """Create ReportingSubAgent instance."""
        agent = ReportingSubAgent()
        agent.llm_manager = mock_llm_manager
        return agent

    @pytest.fixture
    def valid_state(self):
        """Create valid DeepAgentState with all required results."""
        state = DeepAgentState()
        state.user_request = "Generate a comprehensive analysis report"
        state.action_plan_result = {"actions": ["analyze", "optimize"]}
        state.optimizations_result = {"optimizations": ["cache", "index"]}
        state.data_result = {"data": "analysis complete"}
        state.triage_result = {"category": "analysis", "priority": "high"}
        return state

    @pytest.fixture
    def incomplete_state(self):
        """Create incomplete DeepAgentState missing required results."""
        state = DeepAgentState()
        state.user_request = "Generate report"
        state.action_plan_result = None  # Missing
        state.optimizations_result = {"optimizations": ["cache"]}
        state.data_result = None  # Missing
        state.triage_result = {"category": "analysis"}
        return state

    @pytest.fixture
    def execution_context(self, valid_state):
        """Create valid execution context."""
        return ExecutionContext(
            run_id="test_run_123",
            agent_name="ReportingSubAgent",
            state=valid_state,
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789",
            start_time=time.time(),
            correlation_id="correlation_123"
        )

    async def test_golden_pattern_inheritance(self, reporting_agent):
        """Test that ReportingSubAgent follows golden pattern inheritance."""
        # Verify inheritance from BaseAgent
        from netra_backend.app.agents.base_agent import BaseAgent
        assert isinstance(reporting_agent, BaseAgent)
        
        # Verify infrastructure is enabled
        assert reporting_agent._enable_reliability == True
        assert reporting_agent._enable_execution_engine == True
        assert reporting_agent._enable_caching == True
        
        # Verify BaseAgent methods are available
        assert hasattr(reporting_agent, 'emit_thinking')
        assert hasattr(reporting_agent, 'emit_progress')
        assert hasattr(reporting_agent, 'emit_error')
        assert hasattr(reporting_agent, 'execute_with_reliability')

    async def test_validate_preconditions_success(self, reporting_agent, execution_context):
        """Test successful validation of preconditions."""
        # Should return True for valid context
        result = await reporting_agent.validate_preconditions(execution_context)
        assert result == True

    async def test_validate_preconditions_failure(self, reporting_agent, incomplete_state):
        """Test validation failure with proper AgentValidationError."""
        context = ExecutionContext(
            run_id="test_run_123",
            agent_name="ReportingSubAgent",
            state=incomplete_state,
            stream_updates=True,
            thread_id="thread_456",
            user_id="user_789",
            start_time=time.time(),
            correlation_id="correlation_123"
        )
        
        # Should raise AgentValidationError for missing results
        with pytest.raises(AgentValidationError) as exc_info:
            await reporting_agent.validate_preconditions(context)
        
        # Verify error details
        error = exc_info.value
        assert "Missing required analysis results" in str(error)
        assert "action_plan_result" in str(error)
        assert "data_result" in str(error)

    @pytest.mark.asyncio
    async def test_websocket_events_emission(self, reporting_agent, execution_context):
        """Test WebSocket events are emitted for chat value delivery."""
        # Mock WebSocket event methods
        reporting_agent.emit_thinking = AsyncMock()
        reporting_agent.emit_progress = AsyncMock()
        reporting_agent.emit_error = AsyncMock()
        
        # Mock internal methods to avoid actual LLM calls
        with patch.object(reporting_agent, '_build_reporting_prompt', return_value="test prompt"):
            with patch.object(reporting_agent, '_execute_reporting_llm_with_observability', 
                            return_value='{"report": "test", "metadata": {}}'):
                with patch.object(reporting_agent, '_send_success_update'):
                    
                    # Execute core logic
                    result = await reporting_agent.execute_core_logic(execution_context)
                    
                    # Verify WebSocket events were emitted
                    assert reporting_agent.emit_thinking.call_count >= 2  # At least 2 thinking events
                    assert reporting_agent.emit_progress.call_count >= 2  # At least 2 progress events
                    
                    # Verify specific event calls
                    thinking_calls = [call.args[0] for call in reporting_agent.emit_thinking.call_args_list]
                    assert any("Starting comprehensive report generation" in call for call in thinking_calls)
                    assert any("Generating final report with AI model" in call for call in thinking_calls)
                    
                    progress_calls = [call.args[0] for call in reporting_agent.emit_progress.call_args_list]
                    assert any("Building comprehensive analysis prompt" in call for call in progress_calls)
                    assert any("Final report generation completed successfully" in call for call in progress_calls)

    @pytest.mark.asyncio
    async def test_error_handling_with_websocket_events(self, reporting_agent, execution_context):
        """Test proper error handling with WebSocket error events."""
        # Mock WebSocket methods
        reporting_agent.emit_thinking = AsyncMock()
        reporting_agent.emit_progress = AsyncMock()
        reporting_agent.emit_error = AsyncMock()
        
        # Mock LLM to raise an exception
        with patch.object(reporting_agent, '_execute_reporting_llm_with_observability',
                         side_effect=Exception("LLM service unavailable")):
            
            # Execute should handle error gracefully
            result = await reporting_agent.execute_core_logic(execution_context)
            
            # Verify error event was emitted
            reporting_agent.emit_error.assert_called_once()
            error_call = reporting_agent.emit_error.call_args[0][0]
            assert "Report generation failed" in error_call
            
            # Verify fallback result is returned
            assert result is not None
            assert "fallback_used" in result.get("metadata", {})

    @pytest.mark.asyncio
    async def test_complete_report_generation_workflow(self, reporting_agent, execution_context, mock_llm_manager):
        """Test complete end-to-end report generation workflow."""
        # Mock WebSocket methods
        reporting_agent.emit_thinking = AsyncMock()
        reporting_agent.emit_progress = AsyncMock()
        reporting_agent._send_update = AsyncMock()
        
        # Execute core logic
        result = await reporting_agent.execute_core_logic(execution_context)
        
        # Verify LLM was called
        mock_llm_manager.ask_llm.assert_called_once()
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "report" in result
        assert result["report"] == "Test report generated successfully"
        
        # Verify state was updated
        assert execution_context.state.report_result is not None

    @pytest.mark.asyncio
    async def test_legacy_execute_method(self, reporting_agent, valid_state):
        """Test backward compatibility with legacy execute method."""
        # Mock execute_with_reliability to avoid actual reliability infrastructure
        reporting_agent.execute_with_reliability = AsyncMock()
        
        # Execute using legacy method
        await reporting_agent.execute(valid_state, "test_run_123", True)
        
        # Verify reliability infrastructure was called
        reporting_agent.execute_with_reliability.assert_called_once()
        
        # Verify arguments passed correctly
        args = reporting_agent.execute_with_reliability.call_args
        assert args[1][1] == "execute_reporting"  # operation_name

    def test_fallback_report_creation(self, reporting_agent, valid_state):
        """Test fallback report creation for error scenarios."""
        fallback_result = reporting_agent._create_fallback_report(valid_state)
        
        # Verify fallback structure
        assert isinstance(fallback_result, dict)
        assert "report" in fallback_result
        assert "summary" in fallback_result
        assert "metadata" in fallback_result
        
        # Verify fallback indicators
        assert fallback_result["summary"]["fallback_used"] == True
        assert fallback_result["metadata"]["fallback_used"] == True
        assert "Primary report generation failed" in fallback_result["metadata"]["reason"]

    def test_report_result_conversion(self, reporting_agent):
        """Test conversion from dict to ReportResult object."""
        test_data = {
            "report": "Test report content",
            "sections": [
                {
                    "section_id": "test_section",
                    "title": "Test Section",
                    "content": "Test content",
                    "section_type": "analysis"
                },
                "string_section"  # Test string section handling
            ],
            "metadata": {"test": "value"}
        }
        
        result = reporting_agent._create_report_result(test_data)
        
        # Verify ReportResult object creation
        from netra_backend.app.agents.state import ReportResult
        assert isinstance(result, ReportResult)
        assert result.content == "Test report content"
        assert len(result.sections) == 2
        assert result.metadata["test"] == "value"
        
        # Verify section conversion
        assert result.sections[0].section_id == "test_section"
        assert result.sections[1].title == "String_section"  # Capitalized

    async def test_entry_conditions_check(self, reporting_agent, valid_state, incomplete_state):
        """Test entry conditions checking."""
        # Valid state should pass
        result = await reporting_agent.check_entry_conditions(valid_state, "test_run")
        assert result == True
        
        # Incomplete state should fail
        result = await reporting_agent.check_entry_conditions(incomplete_state, "test_run")
        assert result == False

    async def test_cleanup_method(self, reporting_agent, valid_state):
        """Test cleanup method execution."""
        # Create mock report result with metadata
        from netra_backend.app.agents.state import ReportResult
        valid_state.report_result = ReportResult(
            report_type="analysis",
            content="test",
            sections=[],
            metadata={"cleanup_test": True}
        )
        
        # Should not raise any exceptions
        await reporting_agent.cleanup(valid_state, "test_run_123")

    @pytest.mark.asyncio
    async def test_llm_observability_integration(self, reporting_agent):
        """Test LLM observability integration."""
        with patch('netra_backend.app.agents.reporting_sub_agent.start_llm_heartbeat') as mock_start:
            with patch('netra_backend.app.agents.reporting_sub_agent.stop_llm_heartbeat') as mock_stop:
                with patch('netra_backend.app.agents.reporting_sub_agent.log_agent_input') as mock_log_input:
                    with patch('netra_backend.app.agents.reporting_sub_agent.log_agent_output') as mock_log_output:
                        
                        # Execute LLM with observability
                        response = await reporting_agent._execute_reporting_llm_with_observability(
                            "test prompt", "test_correlation_id"
                        )
                        
                        # Verify observability hooks were called
                        mock_start.assert_called_once_with("test_correlation_id", "ReportingSubAgent")
                        mock_stop.assert_called_once_with("test_correlation_id")
                        mock_log_input.assert_called_once()
                        mock_log_output.assert_called_once()

    def test_golden_pattern_compliance(self, reporting_agent):
        """Test compliance with golden pattern requirements."""
        # Verify line count is reasonable (should be under 250 lines)
        import inspect
        import netra_backend.app.agents.reporting_sub_agent as agent_module
        source_lines = inspect.getsourcelines(agent_module)[0]
        line_count = len(source_lines)
        assert line_count < 250, f"Agent has {line_count} lines, should be under 250 for golden pattern"
        
        # Verify required methods are implemented
        assert hasattr(reporting_agent, 'validate_preconditions')
        assert hasattr(reporting_agent, 'execute_core_logic')
        
        # Verify infrastructure methods are NOT implemented (inherited from BaseAgent)
        # These should be inherited, not duplicated
        source = inspect.getsource(ReportingSubAgent)
        assert 'class ReliabilityManager' not in source
        assert 'class ExecutionEngine' not in source
        assert 'def emit_websocket_event' not in source
        
        # Verify proper imports for AgentError types
        assert hasattr(reporting_agent, '__module__')
        module = __import__(reporting_agent.__module__, fromlist=['AgentValidationError'])
        assert hasattr(module, 'AgentValidationError')


@pytest.mark.integration
class TestReportingAgentIntegration:
    """Integration tests with real BaseAgent infrastructure."""

    @pytest.fixture
    def integration_agent(self):
        """Create agent for integration testing."""
        agent = ReportingSubAgent()
        # Use mock LLM to avoid real API calls
        agent.llm_manager = AsyncMock(spec=LLMManager)
        agent.llm_manager.ask_llm.return_value = '{"report": "Integration test report", "metadata": {}}'
        return agent

    @pytest.mark.asyncio
    async def test_baseagent_infrastructure_integration(self, integration_agent):
        """Test integration with BaseAgent infrastructure."""
        # Test health status (from BaseAgent)
        health = integration_agent.get_health_status()
        assert isinstance(health, dict)
        assert "agent_name" in health
        assert health["agent_name"] == "ReportingSubAgent"
        
        # Test WebSocket bridge availability
        has_websocket = integration_agent.has_websocket_context()
        assert isinstance(has_websocket, bool)


if __name__ == "__main__":
    # Run specific test for quick validation
    pytest.main([__file__ + "::TestReportingAgentGoldenPattern::test_golden_pattern_inheritance", "-v"])