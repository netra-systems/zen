"""
Test WebSocketManager Never None Fix

Critical test to ensure WebSocketManager is never set to None during agent registration,
which was causing agent execution issues in GCP staging environment.

Bug: WebSocketManager being set to None prevented real-time agent events
Fix: Added retry logic, validation, and strict None checks
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from netra_backend.app.websocket_core import get_websocket_manager
from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


@pytest.mark.asyncio
async def test_websocket_manager_never_returns_none():
    """Test that get_websocket_manager never returns None."""
    # Reset singleton
    from netra_backend.app.websocket_core.manager import _websocket_manager
    import netra_backend.app.websocket_core.manager as manager_module
    manager_module._websocket_manager = None
    
    # Get manager multiple times
    for i in range(5):
        manager = get_websocket_manager()
        assert manager is not None, f"WebSocket manager was None on attempt {i + 1}"
        assert hasattr(manager, 'connections'), "WebSocket manager missing connections attribute"
        assert hasattr(manager, 'send_to_thread'), "WebSocket manager missing send_to_thread method"


@pytest.mark.asyncio
async def test_agent_registry_rejects_none_websocket_manager():
    """Test that AgentRegistry.set_websocket_manager rejects None values."""
    mock_llm = Mock()
    mock_dispatcher = Mock()
    
    registry = AgentRegistry()
    
    # Should raise ValueError when trying to set None
    with pytest.raises(ValueError, match="WebSocketManager cannot be None"):
        registry.set_websocket_manager(None)


@pytest.mark.asyncio
async def test_agent_registry_validates_websocket_manager():
    """Test that AgentRegistry validates WebSocketManager has required methods."""
    mock_llm = Mock()
    mock_dispatcher = Mock()
    
    registry = AgentRegistry()
    
    # Create incomplete WebSocket manager mock (missing required methods)
    incomplete_manager = Mock()
    del incomplete_manager.send_to_thread  # Remove required method
    del incomplete_manager.connections     # Remove required attribute
    
    # Should raise ValueError for incomplete manager
    with pytest.raises(ValueError, match="WebSocketManager incomplete"):
        registry.set_websocket_manager(incomplete_manager)


@pytest.mark.asyncio
async def test_agent_websocket_bridge_retry_logic():
    """Test AgentWebSocketBridge retry logic for WebSocketManager initialization."""
    bridge = await get_agent_websocket_bridge()
    
    # Mock get_websocket_manager to fail twice, then succeed
    call_count = 0
    original_get_manager = get_websocket_manager
    
    def mock_get_manager():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return None  # Fail first 2 attempts
        return original_get_manager()  # Succeed on 3rd attempt
    
    with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', mock_get_manager):
        # This should succeed after retries
        await bridge._initialize_websocket_manager()
        assert bridge._websocket_manager is not None
        assert call_count == 3  # Should have been called 3 times


@pytest.mark.asyncio
async def test_deterministic_startup_websocket_retry():
    """Test deterministic startup retry logic for WebSocketManager."""
    from netra_backend.app.smd import DeterministicStartupManager
    from fastapi import FastAPI
    
    app = FastAPI()
    startup_manager = DeterministicStartupManager(app)
    
    # Mock supervisor
    mock_supervisor = Mock()
    mock_registry = Mock()
    mock_tool_dispatcher = Mock()
    mock_tool_dispatcher._websocket_enhanced = False
    mock_registry.tool_dispatcher = mock_tool_dispatcher
    mock_registry.set_websocket_manager = Mock()
    mock_supervisor.registry = mock_registry
    app.state.agent_supervisor = mock_supervisor
    
    # Mock get_websocket_manager to fail twice, then succeed
    call_count = 0
    original_get_manager = get_websocket_manager
    
    def mock_get_manager():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return None  # Fail first 2 attempts
        return original_get_manager()  # Succeed on 3rd attempt
    
    with patch('netra_backend.app.smd.get_websocket_manager', mock_get_manager):
        # This should succeed after retries
        await startup_manager._ensure_tool_dispatcher_enhancement()
        
        # Verify WebSocket manager was set on registry
        mock_registry.set_websocket_manager.assert_called_once()
        args, kwargs = mock_registry.set_websocket_manager.call_args
        assert args[0] is not None, "WebSocket manager passed to registry was None"


@pytest.mark.asyncio
async def test_websocket_manager_creation_failure_handling():
    """Test handling of WebSocket manager creation failures."""
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    import netra_backend.app.websocket_core.manager as manager_module
    
    # Reset singleton
    manager_module._websocket_manager = None
    
    # Mock WebSocketManager creation to fail
    with patch.object(WebSocketManager, '__new__', side_effect=Exception("Creation failed")):
        with pytest.raises(RuntimeError, match="WebSocketManager creation failed"):
            get_websocket_manager()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])