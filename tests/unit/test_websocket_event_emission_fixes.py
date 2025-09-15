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
        supervisor = SupervisorAgent(llm_manager=Mock(), websocket_bridge=None)
        assert supervisor.websocket_bridge is None
        mock_bridge = Mock()
        supervisor.websocket_bridge = mock_bridge
        assert supervisor.websocket_bridge == mock_bridge

    @pytest.mark.asyncio
    async def test_supervisor_emits_websocket_events(self):
        """Test that supervisor emits critical WebSocket events during execution."""
        mock_factory = Mock()
        mock_llm_manager = Mock()
        mock_websocket_bridge = AsyncMock()
        mock_websocket_bridge.notify_agent_started = AsyncMock()
        mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        mock_websocket_bridge.notify_agent_completed = AsyncMock()
        mock_websocket_bridge.notify_agent_error = AsyncMock()
        supervisor = SupervisorAgent(llm_manager=mock_llm_manager, websocket_bridge=mock_websocket_bridge)
        context = UserExecutionContext(user_id='test-user', thread_id='test-thread', run_id='test-run', request_id='test-request', db_session=Mock(), metadata={'user_request': 'Test request'})
        mock_engine = AsyncMock()
        mock_engine.execute_agent_pipeline = AsyncMock(return_value=Mock(success=True, result='test result'))
        mock_engine.cleanup = AsyncMock()
        with patch.object(supervisor, '_create_user_execution_engine', return_value=mock_engine):
            result = await supervisor.execute(context)
        mock_websocket_bridge.notify_agent_started.assert_called_once()
        mock_websocket_bridge.notify_agent_thinking.assert_called_once()
        mock_websocket_bridge.notify_agent_completed.assert_called_once()
        call_args = mock_websocket_bridge.notify_agent_started.call_args
        assert call_args[0][0] == 'test-run'
        assert call_args[0][1] == 'Supervisor'
        assert result['supervisor_result'] == 'completed'
        assert result['user_id'] == 'test-user'
        assert result['run_id'] == 'test-run'

    @pytest.mark.asyncio
    async def test_message_handler_adds_websocket_bridge(self):
        """Test that MessageHandlerService adds WebSocket bridge to supervisor."""
        mock_supervisor = Mock()
        mock_supervisor.run = AsyncMock(return_value='test result')
        mock_supervisor.thread_id = None
        mock_supervisor.user_id = None
        mock_supervisor.db_session = None
        mock_supervisor.websocket_bridge = None
        handler = StartAgentHandler(supervisor=mock_supervisor, db_session_factory=Mock())
        with patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = Mock()
            mock_create_bridge.return_value = mock_bridge
            result = await handler._execute_agent_workflow(user_request='Test request', thread_id='test-thread', user_id='test-user', run_id='test-run')
        assert mock_supervisor.websocket_bridge == mock_bridge
        mock_create_bridge.assert_called_once()
        mock_supervisor.run.assert_called_once_with('Test request', 'test-thread', 'test-user', 'test-run')

    def test_websocket_emitter_method_signatures(self):
        """Test that UnifiedWebSocketEmitter has the correct method signatures."""
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        mock_manager = Mock()
        emitter = UnifiedWebSocketEmitter(user_context=Mock(user_id='test-user', run_id='test-run'), websocket_manager=mock_manager)
        assert hasattr(emitter, 'notify_agent_started')
        assert hasattr(emitter, 'notify_agent_thinking')
        assert hasattr(emitter, 'notify_agent_completed')
        assert hasattr(emitter, 'notify_tool_executing')
        assert hasattr(emitter, 'notify_tool_completed')
        import inspect
        assert inspect.iscoroutinefunction(emitter.notify_agent_started)
        assert inspect.iscoroutinefunction(emitter.notify_agent_thinking)
        assert inspect.iscoroutinefunction(emitter.notify_agent_completed)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')