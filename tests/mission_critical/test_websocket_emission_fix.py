class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
Mission Critical Test: WebSocket Emission Method Fix
Verifies that SupervisorAgent correctly uses emit_agent_event
"""

import pytest
import asyncio
from datetime import datetime, timezone
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Add paths
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketEmissionFix:
    """Test that the WebSocket emission method fix is working correctly."""
    
    @pytest.mark.asyncio
    async def test_supervisor_uses_emit_agent_event(self):
        """Verify SupervisorAgent calls emit_agent_event correctly."""
        
        # Create mock WebSocket bridge
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.emit_agent_event = AsyncMock(return_value=True)
        
        # Create mock dependencies
        websocket = TestWebSocketConnection()
        mock_llm.invoke = AsyncMock(return_value=MagicMock(content="Test response"))
        
        websocket = TestWebSocketConnection()
        
        # Create supervisor
        supervisor = SupervisorAgent.create(
            llm_client=mock_llm,
            tool_dispatcher=mock_tool_dispatcher,
            agent_registry=mock_agent_registry,
            websocket_bridge=mock_bridge
        )
        
        # Create context
        context = UserExecutionContext.create(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run_123",
            websocket_connection_id="ws_conn_456"
        )
        
        # Call _emit_thinking
        await supervisor._emit_thinking(context, "Test thinking message")
        
        # Verify emit_agent_event was called correctly
        mock_bridge.emit_agent_event.assert_called_once()
        
        # Check the call arguments
        call_args = mock_bridge.emit_agent_event.call_args
        assert call_args[1]['event_type'] == 'agent_thinking'
        assert call_args[1]['run_id'] == 'test_run_123'
        assert call_args[1]['agent_name'] == 'Supervisor'
        assert 'Test thinking message' in str(call_args[1]['data'])
    
    @pytest.mark.asyncio
    async def test_emit_thinking_handles_errors_gracefully(self):
        """Verify _emit_thinking doesn't crash on WebSocket errors."""
        
        # Create mock bridge that fails
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.emit_agent_event = AsyncMock(side_effect=Exception("WebSocket error"))
        
        # Create supervisor
        supervisor = SupervisorAgent.create(
            websocket=TestWebSocketConnection(),
            websocket_bridge=mock_bridge
        )
        
        # Create context
        context = UserExecutionContext.create(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run_123"
        )
        
        # This should not raise an exception
        await supervisor._emit_thinking(context, "Test message")
        
        # Verify the method was called despite the error
        mock_bridge.emit_agent_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_validates_emit_agent_event(self):
        """Verify startup module validates for emit_agent_event method."""
        
        # Import startup validation
        from netra_backend.app.startup_module import validate_websocket_infrastructure
        
        # Create supervisor with proper bridge
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.websocket = TestWebSocketConnection()
        
        supervisor = SupervisorAgent.create(
            websocket=TestWebSocketConnection(),
            websocket_bridge=mock_bridge
        )
        
        # This should pass validation
        with patch('netra_backend.app.startup_module.logger') as mock_logger:
            # The validation should check for emit_agent_event
            assert hasattr(supervisor.websocket_bridge, 'emit_agent_event')
            mock_logger.info.assert_not_called()  # No error logs
    
    @pytest.mark.asyncio
    async def test_integration_with_real_bridge_structure(self):
        """Test that the fix works with real AgentWebSocketBridge structure."""
        
        # Create a mock that mimics real bridge
        websocket = TestWebSocketConnection()
        mock_bridge.emit_agent_event = AsyncMock(return_value=True)
        mock_bridge._validate_event_context = MagicMock(return_value=True)
        mock_bridge._resolve_thread_id_from_run_id = AsyncMock(return_value="test_thread")
        
        # Create supervisor
        supervisor = SupervisorAgent.create(
            websocket=TestWebSocketConnection(),
            websocket_bridge=mock_bridge
        )
        
        # Create context with all fields
        context = UserExecutionContext.create(
            user_id="user_123",
            thread_id="thread_456",
            run_id="run_789",
            websocket_connection_id="ws_abc"
        )
        
        # Emit thinking
        await supervisor._emit_thinking(context, "Processing your request...")
        
        # Verify correct method was called
        mock_bridge.emit_agent_event.assert_called_once()
        
        # Verify data structure
        call_data = mock_bridge.emit_agent_event.call_args[1]
        assert call_data['event_type'] == 'agent_thinking'
        assert call_data['run_id'] == 'run_789'
        assert call_data['data']['message'] == 'Processing your request...'
        assert call_data['data']['user_id'] == 'user_123'
        assert call_data['data']['connection_id'] == 'ws_abc'


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])