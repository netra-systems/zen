"""Mission Critical Test Suite for Agent Error Context Handling

Tests for agent error handling, ErrorContext validation, and graceful degradation.
Ensures agents handle errors properly and maintain system stability.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState, ActionPlanResult, OptimizationsResult
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestErrorContextHandling:
    """Test ErrorContext creation and validation."""
    
    def test_error_context_auto_generates_trace_id(self):
        """Test that ErrorContext auto-generates trace_id when not provided."""
        # Create ErrorContext without trace_id
        error_context = ErrorContext(
            operation="test_operation"
        )
        
        # Verify trace_id was auto-generated
        assert error_context.trace_id is not None
        assert error_context.trace_id.startswith("trace_")
        assert len(error_context.trace_id) > 10
    
    def test_error_context_uses_provided_trace_id(self):
        """Test that ErrorContext uses provided trace_id when given."""
        custom_trace_id = "trace_custom_12345"
        
        error_context = ErrorContext(
            trace_id=custom_trace_id,
            operation="test_operation"
        )
        
        assert error_context.trace_id == custom_trace_id
    
    def test_error_context_generate_trace_id_method(self):
        """Test the generate_trace_id class method."""
        trace_id = ErrorContext.generate_trace_id()
        
        assert trace_id is not None
        assert trace_id.startswith("trace_")
        assert len(trace_id) == 22  # "trace_" + 16 hex chars
    
    def test_error_context_with_all_fields(self):
        """Test ErrorContext with all optional fields populated."""
        error_context = ErrorContext(
            operation="test_operation",
            user_id="user_123",
            correlation_id="corr_456",
            request_id="req_789",
            session_id="sess_abc",
            agent_name="TestAgent",
            operation_name="test_op",
            run_id="run_def",
            retry_count=2,
            max_retries=5,
            details={"key": "value"},
            additional_data={"extra": "data"},
            component="TestComponent",
            severity="HIGH",
            error_code="ERR_001"
        )
        
        assert error_context.trace_id is not None  # Auto-generated
        assert error_context.operation == "test_operation"
        assert error_context.user_id == "user_123"
        assert error_context.retry_count == 2


class TestRunIdValidation:
    """Test run_id validation and suspicious pattern detection."""
    
    @pytest.fixture
    def bridge(self):
        """Create AgentWebSocketBridge instance for testing."""
        bridge = AgentWebSocketBridge()
        bridge._websocket_manager = Mock()
        bridge._thread_run_registry = Mock()
        return bridge
    
    def test_valid_run_id_patterns(self, bridge):
        """Test that valid run_id patterns are not flagged as suspicious."""
        valid_patterns = [
            "thread_061dda3ade2d4681_run_1756948781010_c3b67c3b",
            "thread_374579bdba3c41b8_run_1756907956810_40a39203",
            "run_12345678_abcdef",
            "execution_2025_09_04_12345",
            "user_session_xyz_run_001"
        ]
        
        for run_id in valid_patterns:
            assert not bridge._is_suspicious_run_id(run_id), f"Valid run_id {run_id} flagged as suspicious"
    
    def test_suspicious_run_id_patterns(self, bridge):
        """Test that actually suspicious run_id patterns are detected."""
        suspicious_patterns = [
            "test_run_123",
            "debug_session",
            "mock_execution",
            "system_broadcast",
            "global_event",
            "admin_override",
            "null",
            "undefined",
            "",
            "ab",  # Too short
            "sys_operation",
            "system_task"
        ]
        
        for run_id in suspicious_patterns:
            assert bridge._is_suspicious_run_id(run_id), f"Suspicious run_id {run_id} not detected"
    
    def test_run_id_word_boundary_matching(self, bridge):
        """Test that word boundary matching prevents false positives."""
        # These should NOT be flagged because 'test' is not a word boundary match
        safe_patterns = [
            "thread_latest_update",  # Contains 'test' within 'latest'
            "contest_winner_run",     # Contains 'test' within 'contest'
            "fastest_execution"       # Contains 'test' within 'fastest'
        ]
        
        for run_id in safe_patterns:
            assert not bridge._is_suspicious_run_id(run_id), f"Safe run_id {run_id} incorrectly flagged"
    
    def test_context_validation(self, bridge):
        """Test full context validation for WebSocket events."""
        # Valid context
        assert bridge._validate_event_context("run_12345", "agent_started", "TestAgent")
        
        # Invalid contexts
        assert not bridge._validate_event_context(None, "agent_started", "TestAgent")
        assert not bridge._validate_event_context("", "agent_started", "TestAgent")
        assert not bridge._validate_event_context("registry", "agent_started", "TestAgent")
        assert not bridge._validate_event_context("  ", "agent_started", "TestAgent")


class TestAgentErrorHandling:
    """Test agent error handling and graceful degradation."""
    
    @pytest.fixture
    async def agent(self):
        """Create ActionsToMeetGoalsSubAgent for testing."""
        agent = ActionsToMeetGoalsSubAgent()
        agent.logger = Mock()
        agent.llm_manager = AsyncMock()
        agent.action_plan_builder = Mock()
        
        # Mock WebSocket emitters
        agent.emit_agent_started = AsyncMock()
        agent.emit_thinking = AsyncMock()
        agent.emit_progress = AsyncMock()
        agent.emit_tool_executing = AsyncMock()
        agent.emit_tool_completed = AsyncMock()
        agent.emit_agent_completed = AsyncMock()
        agent.emit_error = AsyncMock()
        
        return agent
    
    @pytest.fixture
    def context(self):
        """Create UserExecutionContext for testing."""
        context = Mock(spec=UserExecutionContext)
        context.run_id = "test_run_123456"
        context.user_id = "user_abc"
        context.thread_id = "thread_def"
        context.metadata = {
            'user_request': "Test request",
            'optimizations_result': Mock(spec=OptimizationsResult),
            'data_result': {"test": "data"}
        }
        return context
    
    @pytest.mark.asyncio
    async def test_error_context_creation_failure_handled(self, agent, context):
        """Test that ErrorContext creation failures don't break execution."""
        # Mock ErrorContext to fail
        with patch('netra_backend.app.agents.actions_to_meet_goals_sub_agent.ErrorContext') as mock_ec:
            mock_ec.side_effect = Exception("ErrorContext creation failed")
            mock_ec.generate_trace_id.side_effect = Exception("Trace ID generation failed")
            
            # Make LLM call fail to trigger error handling
            agent.llm_manager.ask_llm.side_effect = Exception("LLM failure")
            
            # Should still execute fallback logic despite ErrorContext failures
            result = await agent.execute(context, stream_updates=True)
            
            # Verify fallback was executed
            assert result is not None
            assert 'action_plan_result' in result
            
            # Verify error was logged
            agent.logger.error.assert_called()
            error_calls = [str(call) for call in agent.logger.error.call_args_list]
            assert any("ErrorContext creation failed" in call for call in error_calls)
    
    @pytest.mark.asyncio
    async def test_missing_dependencies_graceful_degradation(self, agent, context):
        """Test that missing dependencies trigger graceful degradation."""
        # Remove required dependencies
        context.metadata = {'user_request': "Test request"}
        
        # Execute should apply defaults
        result = await agent.execute(context, stream_updates=False)
        
        # Verify defaults were applied
        assert 'action_plan_result' in result
        
        # Check that warning was logged about missing dependencies
        agent.logger.warning.assert_called()
        warning_calls = [str(call) for call in agent.logger.warning.call_args_list]
        assert any("Missing dependencies" in call for call in warning_calls)
    
    @pytest.mark.asyncio
    async def test_fallback_logic_execution(self, agent, context):
        """Test that fallback logic executes when main execution fails."""
        # Make core logic fail
        agent.validate_preconditions = AsyncMock(return_value=False)
        
        # Execute should trigger fallback
        result = await agent.execute(context, stream_updates=True)
        
        # Verify fallback result
        assert result is not None
        assert 'action_plan_result' in result
        
        # Verify WebSocket events were sent for fallback
        agent.emit_agent_started.assert_called()
        agent.emit_agent_completed.assert_called()
    
    @pytest.mark.asyncio
    async def test_precondition_validation_with_defaults(self, agent, context):
        """Test precondition validation applies defaults for missing data."""
        # Missing optimizations_result
        context.metadata = {
            'user_request': "Test request",
            'data_result': {"test": "data"}
        }
        
        # Validate should pass with defaults
        result = await agent.validate_preconditions(context)
        assert result is True
        
        # Verify default was applied
        assert 'optimizations_result' in context.metadata
    
    @pytest.mark.asyncio
    async def test_error_propagation_with_context(self, agent, context):
        """Test that errors are properly propagated with context information."""
        # Make LLM call fail
        error_msg = "Test LLM failure"
        agent.llm_manager.ask_llm.side_effect = Exception(error_msg)
        
        # Should execute fallback and not raise
        result = await agent.execute(context, stream_updates=False)
        
        # Verify result contains fallback
        assert result is not None
        assert 'action_plan_result' in result
        
        # Verify error was logged with context
        agent.logger.warning.assert_called()
        warning_calls = [str(call) for call in agent.logger.warning.call_args_list]
        assert any(error_msg in call for call in warning_calls)


class TestCascadingFailuresPrevention:
    """Test prevention of cascading failures in agent chains."""
    
    @pytest.mark.asyncio
    async def test_error_context_failure_doesnt_cascade(self):
        """Test that ErrorContext failures don't cascade through agent chain."""
        # Create agent chain mock
        agent1 = ActionsToMeetGoalsSubAgent()
        agent1.logger = Mock()
        
        context = Mock(spec=UserExecutionContext)
        context.run_id = "test_run"
        context.metadata = {'user_request': "Test"}
        
        # Mock ErrorContext to always fail
        with patch('netra_backend.app.agents.actions_to_meet_goals_sub_agent.ErrorContext') as mock_ec:
            mock_ec.side_effect = Exception("ErrorContext always fails")
            mock_ec.generate_trace_id.side_effect = Exception("Generate fails too")
            
            # Agent should still return a result
            result = await agent1.execute(context)
            
            assert result is not None
            assert 'action_plan_result' in result
    
    @pytest.mark.asyncio
    async def test_multiple_agents_with_error_handling(self):
        """Test that multiple agents in chain handle errors independently."""
        agents = []
        for i in range(3):
            agent = ActionsToMeetGoalsSubAgent()
            agent.logger = Mock()
            agent.name = f"Agent{i}"
            agents.append(agent)
        
        context = Mock(spec=UserExecutionContext)
        context.run_id = "test_run"
        context.metadata = {'user_request': "Test"}
        
        # Execute all agents - even if some fail, others should continue
        results = []
        for agent in agents:
            try:
                result = await agent.execute(context)
                results.append(result)
            except Exception as e:
                # Should not happen with proper error handling
                pytest.fail(f"Agent {agent.name} raised exception: {e}")
        
        # All agents should return results (even if fallback)
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert 'action_plan_result' in result


class TestErrorContextStateManaement:
    """Test ErrorContext state management and cleanup."""
    
    def test_error_context_storage_initialization(self):
        """Test that ErrorContext storage initializes properly."""
        # Clear any existing context
        ErrorContext.clear_context()
        
        # Set values
        ErrorContext.set_trace_id("test_trace")
        ErrorContext.set_user_id("test_user")
        ErrorContext.set_request_id("test_request")
        
        # Retrieve values
        assert ErrorContext.get_trace_id() == "test_trace"
        assert ErrorContext.get_user_id() == "test_user"
        assert ErrorContext.get_request_id() == "test_request"
    
    def test_error_context_cleanup(self):
        """Test that ErrorContext can be properly cleaned up."""
        # Set values
        ErrorContext.set_trace_id("test_trace")
        ErrorContext.set_user_id("test_user")
        
        # Clear context
        ErrorContext.clear_context()
        
        # Verify cleared
        assert ErrorContext.get_trace_id() is None
        assert ErrorContext.get_user_id() is None
    
    def test_error_context_manager_usage(self):
        """Test ErrorContextManager for scoped context."""
        from netra_backend.app.schemas.shared_types import ErrorContextManager
        
        # Set initial context
        ErrorContext.set_trace_id("original_trace")
        
        # Use context manager to temporarily change
        with ErrorContextManager(trace_id="temp_trace", user_id="temp_user"):
            assert ErrorContext.get_trace_id() == "temp_trace"
            assert ErrorContext.get_user_id() == "temp_user"
        
        # Verify restored to original
        assert ErrorContext.get_trace_id() == "original_trace"
        assert ErrorContext.get_user_id() is None  # Was not set originally


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])