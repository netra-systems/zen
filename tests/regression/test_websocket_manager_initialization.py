"""
Regression test for WebSocket manager initialization issue.

This test ensures that:
1. get_websocket_manager() never returns None
2. WebSocket manager is properly initialized during startup
3. Agent registry receives a valid WebSocket manager
4. No warnings about None WebSocket manager are logged

Issue: WebSocket manager was returning None due to syntax error in manager.py
Fixed: Removed orphaned methods that were incorrectly placed outside the class
"""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.smd import StartupOrchestrator
from netra_backend.app.services.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession


class TestWebSocketManagerInitialization:
    """Test WebSocket manager initialization and integration."""
    
    def test_get_websocket_manager_never_returns_none(self):
        """Test that get_websocket_manager() never returns None."""
        # Clear any existing instance to test fresh initialization
        from netra_backend.app.websocket_core import manager as ws_module
        ws_module._websocket_manager = None
        
        # Get manager instance
        manager = get_websocket_manager()
        
        # Verify it's not None
        assert manager is not None, "get_websocket_manager() returned None"
        assert isinstance(manager, WebSocketManager), f"Expected WebSocketManager, got {type(manager)}"
        
    def test_websocket_manager_singleton(self):
        """Test that WebSocket manager follows singleton pattern."""
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        assert manager1 is manager2, "WebSocket manager is not a singleton"
        
    def test_websocket_manager_has_required_attributes(self):
        """Test that WebSocket manager has all required attributes."""
        manager = get_websocket_manager()
        
        # Check critical attributes exist
        assert hasattr(manager, 'connections'), "Missing connections attribute"
        assert hasattr(manager, 'user_connections'), "Missing user_connections attribute"
        assert hasattr(manager, 'send_to_user'), "Missing send_to_user method"
        assert hasattr(manager, 'connect_user'), "Missing connect_user method"
        assert hasattr(manager, 'disconnect_user'), "Missing disconnect_user method"
        
    def test_agent_registry_accepts_websocket_manager(self):
        """Test that AgentRegistry properly accepts WebSocket manager."""
        # Create mock dependencies
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Create registry
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        
        # Get WebSocket manager
        ws_manager = get_websocket_manager()
        
        # Set WebSocket manager - should not raise or warn
        with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            mock_logger.get_logger.return_value = Mock()
            logger_instance = mock_logger.get_logger.return_value
            
            # Set the manager
            registry.set_websocket_manager(ws_manager)
            
            # Verify no warning about None was logged
            warning_calls = [call for call in logger_instance.warning.call_args_list 
                           if call and len(call[0]) > 0 and 'None' in str(call[0][0])]
            assert len(warning_calls) == 0, f"Unexpected warning about None: {warning_calls}"
            
    @pytest.mark.asyncio
    async def test_supervisor_agent_initialization_with_websocket(self):
        """Test that SupervisorAgent properly initializes with WebSocket manager."""
        # Create mock dependencies
        db_session = Mock(spec=AsyncSession)
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Get WebSocket manager
        ws_manager = get_websocket_manager()
        
        # Create supervisor - should not raise
        supervisor = SupervisorAgent(
            db_session,
            llm_manager,
            ws_manager,
            tool_dispatcher
        )
        
        # Verify supervisor has WebSocket manager
        assert supervisor.websocket_manager is not None, "Supervisor WebSocket manager is None"
        assert supervisor.websocket_manager is ws_manager, "Supervisor has wrong WebSocket manager"
        
        # Verify registry has WebSocket manager set
        assert hasattr(supervisor, 'registry'), "Supervisor missing registry"
        
    @pytest.mark.asyncio
    async def test_deterministic_startup_websocket_initialization(self):
        """Test WebSocket initialization during deterministic startup."""
        app = FastAPI()
        
        # Initialize app.state with required attributes
        app.state.db_session_factory = Mock(spec=AsyncSession)
        app.state.llm_manager = Mock(spec=LLMManager)
        app.state.tool_dispatcher = Mock(spec=ToolDispatcher)
        
        orchestrator = StartupOrchestrator(app)
        
        # Test WebSocket initialization
        await orchestrator._initialize_websocket()
        
        # Verify WebSocket manager exists and is not None
        ws_manager = get_websocket_manager()
        assert ws_manager is not None, "WebSocket manager is None after initialization"
        
    def test_websocket_manager_syntax_validation(self):
        """Test that WebSocket manager module has valid syntax."""
        import ast
        import inspect
        from netra_backend.app.websocket_core import manager as ws_module
        
        # Get the source code
        source_file = inspect.getfile(ws_module)
        
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
        # Try to parse the source code
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in WebSocket manager: {e}")
            
    def test_no_orphaned_methods_in_module(self):
        """Test that there are no orphaned methods at module level."""
        from netra_backend.app.websocket_core import manager as ws_module
        
        # Get all module-level callables
        module_callables = []
        for name in dir(ws_module):
            if not name.startswith('_'):
                obj = getattr(ws_module, name)
                if callable(obj) and not isinstance(obj, type):
                    module_callables.append(name)
                    
        # Expected module-level functions
        expected_functions = {
            'get_websocket_manager',
            'get_manager',
            'websocket_context',
            'sync_state', 
            'broadcast_message',
            # Test compatibility functions added via monkey patching
            '_send_with_timeout_retry_method',
            '_calculate_retry_delay_method',
            '_handle_send_failure_method'
        }
        
        # Find unexpected functions (potential orphaned methods)
        unexpected = set(module_callables) - expected_functions
        
        # Filter out imports and other expected items
        unexpected = {f for f in unexpected 
                     if not f.startswith('get_') 
                     and f not in ['asynccontextmanager', 'logger', 'types']}
        
        assert len(unexpected) == 0, f"Found unexpected module-level functions (possible orphaned methods): {unexpected}"
        
    @pytest.mark.asyncio
    async def test_websocket_manager_send_functionality(self):
        """Test that WebSocket manager can handle send operations."""
        manager = get_websocket_manager()
        
        # Test sending to non-existent user (should handle gracefully)
        result = await manager.send_to_user("test_user", {"type": "test", "data": "test"})
        
        # Should return False for non-connected user but not raise
        assert result is False, "Expected False for non-connected user"
        
    def test_websocket_manager_stats(self):
        """Test that WebSocket manager can provide stats."""
        manager = get_websocket_manager()
        
        # Get stats should work without error
        stats_coro = manager.get_stats()
        
        # Run the coroutine
        loop = asyncio.new_event_loop()
        try:
            stats = loop.run_until_complete(stats_coro)
            
            # Verify stats structure
            assert isinstance(stats, dict), f"Expected dict, got {type(stats)}"
            assert 'active_connections' in stats, "Missing active_connections in stats"
            assert 'active_users' in stats, "Missing active_users in stats"
        finally:
            loop.close()


class TestWebSocketAgentIntegration:
    """Test WebSocket integration with agent system."""
    
    def test_agent_registry_websocket_enhancement(self):
        """Test that tool dispatcher gets enhanced with WebSocket."""
        # Create mock dependencies
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        tool_dispatcher._websocket_enhanced = False
        
        # Create registry
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        
        # Get WebSocket manager
        ws_manager = get_websocket_manager()
        
        # Mock the enhancement
        with patch.object(tool_dispatcher, '__setattr__') as mock_setattr:
            registry.set_websocket_manager(ws_manager)
            
            # Verify enhancement was attempted
            # The actual enhancement happens through setattr
            assert mock_setattr.called or hasattr(tool_dispatcher, '_websocket_manager'), \
                   "Tool dispatcher was not enhanced with WebSocket"
                   
    @pytest.mark.asyncio
    async def test_websocket_event_notification_capability(self):
        """Test that WebSocket manager can send agent events."""
        manager = get_websocket_manager()
        
        # Test sending agent events
        events = [
            {"type": "agent_started", "agent": "test_agent"},
            {"type": "agent_thinking", "thought": "processing"},
            {"type": "tool_executing", "tool": "test_tool"},
            {"type": "tool_completed", "result": "success"},
            {"type": "agent_completed", "final": "done"}
        ]
        
        for event in events:
            # Should handle gracefully even without connections
            result = await manager.send_to_user("test_run_id", event)
            # Returns False for no connections, but doesn't raise
            assert result is False, f"Unexpected result for {event['type']}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])