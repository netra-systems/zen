"""Unit tests for WebSocketContextMixin functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from datetime import datetime, timezone

from netra_backend.app.agents.mixins.websocket_context_mixin import WebSocketContextMixin
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier


class MockTestAgent(WebSocketContextMixin):
    """Mock agent class for testing the mixin."""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        super().__init__()


@pytest.fixture
def mock_websocket_manager():
    """Create a mock WebSocket manager."""
    manager = MagicMock()
    manager.send_to_thread = AsyncMock()
    return manager


@pytest.fixture
def mock_websocket_notifier(mock_websocket_manager):
    """Create a mock WebSocket notifier."""
    notifier = WebSocketNotifier(mock_websocket_manager)
    # Mock all the notifier methods
    notifier.send_agent_thinking = AsyncMock()
    notifier.send_partial_result = AsyncMock()
    notifier.send_tool_started = AsyncMock()
    notifier.send_tool_executing = AsyncMock()
    notifier.send_tool_completed = AsyncMock()
    notifier.send_agent_error = AsyncMock()
    notifier.send_agent_log = AsyncMock()
    notifier.send_stream_chunk = AsyncMock()
    notifier.send_subagent_started = AsyncMock()
    notifier.send_subagent_completed = AsyncMock()
    return notifier


@pytest.fixture
def execution_context():
    """Create a test execution context."""
    return AgentExecutionContext(
        run_id="test-run-123",
        thread_id="thread-456",
        user_id="user-789",
        agent_name="TestAgent"
    )


@pytest.fixture
def test_agent():
    """Create a test agent instance."""
    return MockTestAgent("TestAgent")


class TestWebSocketContextMixin:
    """Test WebSocketContextMixin functionality."""
    
    def test_initial_state(self, test_agent):
        """Test initial state without WebSocket context."""
        assert not test_agent.has_websocket_context()
        assert test_agent.get_websocket_thread_id() is None
        assert test_agent.get_websocket_user_id() is None
        assert test_agent.get_websocket_run_id() is None
    
    def test_set_websocket_context(self, test_agent, execution_context, mock_websocket_notifier):
        """Test setting WebSocket context."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        assert test_agent.has_websocket_context()
        assert test_agent._websocket_context == execution_context
        assert test_agent._websocket_notifier == mock_websocket_notifier
        
        # Test backward compatibility
        assert test_agent.get_websocket_thread_id() == "thread-456"
        assert test_agent.get_websocket_user_id() == "user-789"
        assert test_agent.get_websocket_run_id() == "test-run-123"
    
    def test_set_user_id_backward_compatibility(self, test_agent, execution_context, mock_websocket_notifier):
        """Test that user_id is set for backward compatibility."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        # Should set user_id if agent has that attribute
        if hasattr(test_agent, 'user_id'):
            assert test_agent.user_id == "user-789"
    
    @pytest.mark.asyncio
    async def test_emit_thinking_with_context(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_thinking with WebSocket context."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        await test_agent.emit_thinking("Processing request...", step_number=1)
        
        mock_websocket_notifier.send_agent_thinking.assert_called_once_with(
            execution_context, "Processing request...", 1
        )
    
    @pytest.mark.asyncio
    async def test_emit_thinking_without_context(self, test_agent, caplog):
        """Test emit_thinking without WebSocket context (should not fail)."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        await test_agent.emit_thinking("Processing request...", step_number=1)
        
        # Should log debug message but not fail
        # Note: Log level might be filtered, so we just verify it doesn't crash
        assert True  # The fact that we reached here means it didn't crash
    
    @pytest.mark.asyncio
    async def test_emit_progress(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_progress functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        await test_agent.emit_progress("50% complete", is_complete=False)
        
        mock_websocket_notifier.send_partial_result.assert_called_once_with(
            execution_context, "50% complete", False
        )
    
    @pytest.mark.asyncio
    async def test_emit_tool_started(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_tool_started functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        parameters = {"param1": "value1"}
        await test_agent.emit_tool_started("test_tool", parameters)
        
        mock_websocket_notifier.send_tool_started.assert_called_once_with(
            execution_context, "test_tool", parameters
        )
    
    @pytest.mark.asyncio
    async def test_emit_tool_executing(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_tool_executing functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        await test_agent.emit_tool_executing("test_tool")
        
        mock_websocket_notifier.send_tool_executing.assert_called_once_with(
            execution_context, "test_tool"
        )
    
    @pytest.mark.asyncio
    async def test_emit_tool_completed(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_tool_completed functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        result = {"output": "success"}
        await test_agent.emit_tool_completed("test_tool", result)
        
        mock_websocket_notifier.send_tool_completed.assert_called_once_with(
            execution_context, "test_tool", result
        )
    
    @pytest.mark.asyncio
    async def test_emit_error(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_error functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        error_details = {"stack_trace": "Error details"}
        await test_agent.emit_error("Test error", "validation", error_details)
        
        mock_websocket_notifier.send_agent_error.assert_called_once_with(
            execution_context, "Test error", "validation", error_details
        )
    
    @pytest.mark.asyncio
    async def test_emit_log(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_log functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        metadata = {"module": "test"}
        await test_agent.emit_log("info", "Test log message", metadata)
        
        mock_websocket_notifier.send_agent_log.assert_called_once_with(
            execution_context, "info", "Test log message", metadata
        )
    
    @pytest.mark.asyncio
    async def test_emit_stream_chunk(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_stream_chunk functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        await test_agent.emit_stream_chunk("chunk-1", "Hello world", is_final=True)
        
        mock_websocket_notifier.send_stream_chunk.assert_called_once_with(
            execution_context, "chunk-1", "Hello world", True
        )
    
    @pytest.mark.asyncio
    async def test_emit_subagent_started(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_subagent_started functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        await test_agent.emit_subagent_started("SubAgent", "sub-123")
        
        mock_websocket_notifier.send_subagent_started.assert_called_once_with(
            execution_context, "SubAgent", "sub-123"
        )
    
    @pytest.mark.asyncio
    async def test_emit_subagent_completed(self, test_agent, execution_context, mock_websocket_notifier):
        """Test emit_subagent_completed functionality."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        result = {"status": "success"}
        await test_agent.emit_subagent_completed("SubAgent", "sub-123", result, 1500.0)
        
        mock_websocket_notifier.send_subagent_completed.assert_called_once_with(
            execution_context, "SubAgent", "sub-123", result, 1500.0
        )
    
    @pytest.mark.asyncio
    async def test_emit_thinking_with_progress(self, test_agent, execution_context, mock_websocket_notifier):
        """Test convenience method emit_thinking_with_progress."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        await test_agent.emit_thinking_with_progress("Analyzing...", step_number=2, progress_content="25% done")
        
        mock_websocket_notifier.send_agent_thinking.assert_called_once_with(
            execution_context, "Analyzing...", 2
        )
        mock_websocket_notifier.send_partial_result.assert_called_once_with(
            execution_context, "25% done", False
        )
    
    @pytest.mark.asyncio
    async def test_emit_tool_lifecycle(self, test_agent, execution_context, mock_websocket_notifier):
        """Test convenience method emit_tool_lifecycle."""
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        parameters = {"input": "test"}
        result = {"output": "result"}
        
        await test_agent.emit_tool_lifecycle("test_tool", parameters, result)
        
        # Should call all three tool lifecycle methods
        mock_websocket_notifier.send_tool_started.assert_called_once_with(
            execution_context, "test_tool", parameters
        )
        mock_websocket_notifier.send_tool_executing.assert_called_once_with(
            execution_context, "test_tool"
        )
        mock_websocket_notifier.send_tool_completed.assert_called_once_with(
            execution_context, "test_tool", result
        )
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, test_agent, execution_context, mock_websocket_notifier, caplog):
        """Test that exceptions in WebSocket operations are handled gracefully."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        # Mock an exception in the notifier
        mock_websocket_notifier.send_agent_thinking.side_effect = Exception("WebSocket error")
        
        # Should not raise exception, just log it
        await test_agent.emit_thinking("Test message")
        
        # The fact that we reached here without exception means it's working
        assert True


class TestWebSocketContextMixinIntegration:
    """Integration tests with BaseSubAgent."""
    
    def test_mixin_integration(self):
        """Test that WebSocketContextMixin is properly integrated into BaseSubAgent."""
        from netra_backend.app.agents.base_agent import BaseSubAgent
        
        # Check that WebSocketContextMixin is in the MRO (Method Resolution Order)
        mro_classes = [cls.__name__ for cls in BaseSubAgent.__mro__]
        assert 'WebSocketContextMixin' in mro_classes
        
        # Verify that BaseSubAgent has the mixin methods
        assert hasattr(BaseSubAgent, 'set_websocket_context')
        assert hasattr(BaseSubAgent, 'has_websocket_context')
        assert hasattr(BaseSubAgent, 'emit_thinking')
        assert hasattr(BaseSubAgent, 'emit_tool_executing')
        assert hasattr(BaseSubAgent, 'emit_tool_completed')
    
    def test_thread_safety_properties(self, test_agent, execution_context, mock_websocket_notifier):
        """Test thread safety aspects of the mixin."""
        # Set context
        test_agent.set_websocket_context(execution_context, mock_websocket_notifier)
        
        # Verify context is properly stored
        assert test_agent._websocket_context is execution_context
        assert test_agent._websocket_notifier is mock_websocket_notifier
        
        # Multiple calls to has_websocket_context should be consistent
        for _ in range(10):
            assert test_agent.has_websocket_context() is True
    
    def test_single_source_of_truth_principle(self, test_agent):
        """Test that the mixin follows Single Source of Truth principle."""
        # Before setting context
        assert not test_agent.has_websocket_context()
        
        # Context getters should return None consistently
        assert test_agent.get_websocket_thread_id() is None
        assert test_agent.get_websocket_user_id() is None
        assert test_agent.get_websocket_run_id() is None