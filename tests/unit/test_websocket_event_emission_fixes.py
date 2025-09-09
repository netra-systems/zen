"""
Unit tests to verify WebSocket event emission fixes.

Tests that the critical WebSocket events are properly emitted during agent execution.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket.message_handler import StartAgentHandler


class TestWebSocketEventEmissionFixes:
    """Test suite for WebSocket event emission fixes."""
    
    def test_supervisor_has_websocket_bridge_attribute(self):
        """Test that SupervisorAgent can have a websocket_bridge attribute."""
        supervisor = SupervisorAgent(
            llm_manager=Mock(),
            websocket_bridge=None
        )
        
        # Should accept None initially
        assert supervisor.websocket_bridge is None
        
        # Should accept a mock bridge
        mock_bridge = Mock()
        supervisor.websocket_bridge = mock_bridge
        assert supervisor.websocket_bridge == mock_bridge
    
    @pytest.mark.asyncio
    async def test_supervisor_emits_websocket_events(self):
        """Test that supervisor emits critical WebSocket events during execution."""
        # Create mock dependencies
        mock_factory = Mock()
        mock_llm_manager = Mock()
        mock_websocket_bridge = AsyncMock()
        
        # Configure mock websocket bridge methods
        mock_websocket_bridge.notify_agent_started = AsyncMock()
        mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        mock_websocket_bridge.notify_agent_completed = AsyncMock()
        mock_websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create supervisor with WebSocket bridge
        supervisor = SupervisorAgent(
            llm_manager=mock_llm_manager,
            websocket_bridge=mock_websocket_bridge
        )
        
        # Create test context with all required fields
        context = UserExecutionContext(
            user_id="test-user",
            thread_id="test-thread",
            run_id="test-run",
            request_id="test-request",
            db_session=Mock(),  # Add mock session in constructor
            metadata={"user_request": "Test request"}
        )
        
        # Mock the engine and its methods
        mock_engine = AsyncMock()
        mock_engine.execute_agent_pipeline = AsyncMock(return_value=Mock(success=True, result="test result"))
        mock_engine.cleanup = AsyncMock()
        
        # Patch the engine creation
        with patch.object(supervisor, '_create_user_execution_engine', return_value=mock_engine):
            # Execute supervisor
            result = await supervisor.execute(context)
        
        # Verify WebSocket events were emitted
        mock_websocket_bridge.notify_agent_started.assert_called_once()
        mock_websocket_bridge.notify_agent_thinking.assert_called_once()
        mock_websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Verify the correct parameters were passed
        call_args = mock_websocket_bridge.notify_agent_started.call_args
        assert call_args[0][0] == "test-run"  # run_id
        assert call_args[0][1] == "Supervisor"  # agent_name
        
        # Verify result structure
        assert result["supervisor_result"] == "completed"
        assert result["user_id"] == "test-user"
        assert result["run_id"] == "test-run"
    
    @pytest.mark.asyncio
    async def test_message_handler_adds_websocket_bridge(self):
        """Test that MessageHandlerService adds WebSocket bridge to supervisor."""
        # Create mock supervisor
        mock_supervisor = Mock()
        mock_supervisor.run = AsyncMock(return_value="test result")
        mock_supervisor.thread_id = None
        mock_supervisor.user_id = None
        mock_supervisor.db_session = None
        mock_supervisor.websocket_bridge = None  # Initially no bridge
        
        # Create handler
        handler = StartAgentHandler(
            supervisor=mock_supervisor,
            db_session_factory=Mock()
        )
        
        # Mock create_agent_websocket_bridge
        with patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = Mock()
            mock_create_bridge.return_value = mock_bridge
            
            # Execute workflow
            result = await handler._execute_agent_workflow(
                user_request="Test request",
                thread_id="test-thread",
                user_id="test-user",
                run_id="test-run"
            )
        
        # Verify WebSocket bridge was added
        assert mock_supervisor.websocket_bridge == mock_bridge
        mock_create_bridge.assert_called_once()
        
        # Verify supervisor was called
        mock_supervisor.run.assert_called_once_with(
            "Test request", "test-thread", "test-user", "test-run"
        )
    
    def test_websocket_emitter_method_signatures(self):
        """Test that UnifiedWebSocketEmitter has the correct method signatures."""
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Create mock WebSocket manager
        mock_manager = Mock()
        
        # Create emitter
        emitter = UnifiedWebSocketEmitter(
            user_context=Mock(user_id="test-user", run_id="test-run"),
            websocket_manager=mock_manager
        )
        
        # Verify methods exist and accept correct parameters
        assert hasattr(emitter, 'notify_agent_started')
        assert hasattr(emitter, 'notify_agent_thinking')
        assert hasattr(emitter, 'notify_agent_completed')
        assert hasattr(emitter, 'notify_tool_executing')
        assert hasattr(emitter, 'notify_tool_completed')
        
        # These methods should be async
        import inspect
        assert inspect.iscoroutinefunction(emitter.notify_agent_started)
        assert inspect.iscoroutinefunction(emitter.notify_agent_thinking)
        assert inspect.iscoroutinefunction(emitter.notify_agent_completed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])