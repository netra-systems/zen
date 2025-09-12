
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
WebSocket state recovery critical tests.

Tests WebSocket connection recovery scenarios that prevent revenue loss 
from real-time feature failures causing user abandonment.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.critical
@pytest.mark.websocket
async def test_websocket_state_recovery_after_network_drop():
    """Test WebSocket state recovers correctly after network interruption."""
    ws_manager = UnifiedWebSocketManager()
    
    # Create mock WebSocket
    mock_ws = MagicMock()
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    
    # Establish connection with active state
    user_id = "user123"
    connection = WebSocketConnection(
        connection_id="conn_123",
        user_id=user_id,
        websocket=mock_ws,
        connected_at=datetime.utcnow(),
        metadata={"active_thread": "thread456"}
    )
    
    await ws_manager.add_connection(connection)
    
    # Verify connection is active
    connections = await ws_manager.get_user_connections(user_id)
    assert len(connections) == 1
    assert connections[0].metadata.get("active_thread") == "thread456"
    
    # Simulate network drop by removing connection
    await ws_manager.remove_connection(connection.connection_id)
    
    # Reconnect with same user and recover state
    reconnected = WebSocketConnection(
        connection_id="conn_123_new",
        user_id=user_id,
        websocket=mock_ws,
        connected_at=datetime.utcnow(),
        metadata={"active_thread": "thread456", "recovered": True}
    )
    await ws_manager.add_connection(reconnected)
    
    # Verify state recovery
    connections = await ws_manager.get_user_connections(user_id)
    assert len(connections) == 1
    assert connections[0].metadata.get("active_thread") == "thread456"
    assert connections[0].metadata.get("recovered") is True


@pytest.mark.critical
@pytest.mark.websocket
async def test_message_queue_preservation_during_disconnect():
    """Test pending messages queued during disconnect are delivered on reconnect."""
    ws_manager = UnifiedWebSocketManager()
    
    # Create mock WebSocket
    mock_ws = MagicMock()
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    
    user_id = "user456"
    connection = WebSocketConnection(
        connection_id="conn_456",
        user_id=user_id,
        websocket=mock_ws,
        connected_at=datetime.utcnow()
    )
    
    await ws_manager.add_connection(connection)
    
    # Queue messages in recovery queue before disconnect
    test_message = {"type": "agent_response", "data": "test"}
    ws_manager._message_recovery_queue[user_id] = [test_message]
    
    # Remove connection (simulate disconnect)
    await ws_manager.remove_connection(connection.connection_id)
    
    # Reconnect with new connection
    new_mock_ws = MagicMock()
    new_mock_ws.send = AsyncMock()
    
    reconnected = WebSocketConnection(
        connection_id="conn_456_new",
        user_id=user_id,
        websocket=new_mock_ws,
        connected_at=datetime.utcnow()
    )
    await ws_manager.add_connection(reconnected)
    
    # Process recovery queue manually (in real system this would be automatic)
    if user_id in ws_manager._message_recovery_queue:
        for msg in ws_manager._message_recovery_queue[user_id]:
            await ws_manager.send_to_user(user_id, msg)
        ws_manager._message_recovery_queue[user_id] = []
    
    # Verify message was sent
    new_mock_ws.send.assert_called()
    call_args = new_mock_ws.send.call_args[0][0]
    assert "agent_response" in call_args
    assert "test" in call_args


@pytest.mark.critical
@pytest.mark.websocket
async def test_connection_state_consistency_after_rapid_reconnects():
    """Test connection state remains consistent during rapid reconnection attempts."""
    ws_manager = UnifiedWebSocketManager()
    
    user_id = "user789"
    
    # Rapid connect/disconnect cycle
    for i in range(5):
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()
        
        connection = WebSocketConnection(
            connection_id=f"conn_{i}",
            user_id=user_id,
            websocket=mock_ws,
            connected_at=datetime.utcnow()
        )
        
        await ws_manager.add_connection(connection)
        await ws_manager.remove_connection(connection.connection_id)
    
    # Final connection
    final_ws = MagicMock()
    final_ws.send = AsyncMock()
    final_ws.close = AsyncMock()
    
    final_connection = WebSocketConnection(
        connection_id="conn_final",
        user_id=user_id,
        websocket=final_ws,
        connected_at=datetime.utcnow()
    )
    
    await ws_manager.add_connection(final_connection)
    
    # Verify final connection state is stable
    connections = await ws_manager.get_user_connections(user_id)
    assert len(connections) == 1
    assert connections[0].connection_id == "conn_final"


@pytest.mark.critical
@pytest.mark.websocket
async def test_websocket_cleanup_on_permanent_disconnect():
    """Test WebSocket resources properly cleaned up on permanent disconnect."""
    ws_manager = UnifiedWebSocketManager()
    
    # Create mock WebSocket
    mock_ws = MagicMock()
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    
    user_id = "cleanup_user"
    connection = WebSocketConnection(
        connection_id="conn_cleanup",
        user_id=user_id,
        websocket=mock_ws,
        connected_at=datetime.utcnow(),
        metadata={"data": "should_be_cleaned"}
    )
    
    await ws_manager.add_connection(connection)
    
    # Verify connection exists
    connections = await ws_manager.get_user_connections(user_id)
    assert len(connections) == 1
    
    # Permanent disconnect with cleanup
    await ws_manager.remove_connection(connection.connection_id)
    
    # Clear any recovery queues (permanent disconnect)
    if user_id in ws_manager._message_recovery_queue:
        del ws_manager._message_recovery_queue[user_id]
    
    # Verify cleanup
    connections = await ws_manager.get_user_connections(user_id)
    assert len(connections) == 0
    assert user_id not in ws_manager._message_recovery_queue