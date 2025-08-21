"""Test WebSocket error handling for connection state issues.

Tests to prevent regression of the error:
"WebSocket is not connected. Need to call 'accept' first"
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from app.websocket.connection import ConnectionManager
from app.routes.websockets import (
    _handle_websocket_error, _handle_general_exception,
    _handle_websocket_exceptions
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket with proper state attributes."""
    ws = MagicMock(spec=WebSocket)
    ws.client_state = WebSocketState.CONNECTING
    ws.application_state = WebSocketState.CONNECTING
    return ws


@pytest.fixture
def mock_connected_websocket():
    """Create a mock WebSocket in connected state."""
    ws = MagicMock(spec=WebSocket)
    ws.client_state = WebSocketState.CONNECTED
    ws.application_state = WebSocketState.CONNECTED
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def connection_manager():
    """Create a ConnectionManager instance."""
    return ConnectionManager()


@pytest.mark.asyncio
async def test_close_websocket_safely_with_unconnected_socket(connection_manager, mock_websocket):
    """Test that closing an unconnected WebSocket doesn't raise errors."""
    # This should not raise an error even if WebSocket is not connected
    await connection_manager._close_websocket_safely(
        mock_websocket, code=1011, reason="Test error"
    )
    # WebSocket.close should not be called if not connected
    assert not hasattr(mock_websocket.close, 'called') or not mock_websocket.close.called


@pytest.mark.asyncio
async def test_close_websocket_safely_with_connected_socket(connection_manager, mock_connected_websocket):
    """Test that closing a connected WebSocket works properly."""
    await connection_manager._close_websocket_safely(
        mock_connected_websocket, code=1000, reason="Normal closure"
    )
    # WebSocket.close should be called when connected
    mock_connected_websocket.close.assert_called_once_with(code=1000, reason="Normal closure")


@pytest.mark.asyncio
async def test_close_websocket_safely_with_no_state_attributes(connection_manager):
    """Test handling WebSocket without state attributes."""
    ws = MagicMock(spec=WebSocket)
    # Remove state attributes to simulate edge case
    del ws.client_state
    del ws.application_state
    ws.close = AsyncMock()
    
    # Should handle gracefully without errors
    await connection_manager._close_websocket_safely(ws, code=1011, reason="Test")
    # Close should not be called when state attributes are missing
    ws.close.assert_not_called()


@pytest.mark.asyncio
async def test_handle_websocket_error_with_unconnected_socket(mock_websocket):
    """Test error handling when WebSocket is not connected."""
    with patch('app.routes.websockets.manager') as mock_manager:
        with patch('app.routes.websockets.logger') as mock_logger:
            error = Exception("Test error")
            await _handle_websocket_error(error, "test_user", mock_websocket)
            
            # Should log the error
            mock_logger.error.assert_called_once()
            # Should NOT attempt to disconnect if WebSocket is CONNECTING
            mock_manager.disconnect_user.assert_not_called()


@pytest.mark.asyncio
async def test_handle_websocket_error_with_connected_socket(mock_connected_websocket):
    """Test error handling when WebSocket is connected."""
    with patch('app.routes.websockets.manager') as mock_manager:
        mock_manager.disconnect_user = AsyncMock()
        with patch('app.routes.websockets.logger') as mock_logger:
            error = Exception("Test error")
            await _handle_websocket_error(error, "test_user", mock_connected_websocket)
            
            # Should log the error
            mock_logger.error.assert_called_once()
            # Should attempt to disconnect if WebSocket is CONNECTED
            mock_manager.disconnect_user.assert_called_once_with(
                "test_user", mock_connected_websocket, code=1011, reason="Server error"
            )


@pytest.mark.asyncio
async def test_handle_general_exception_with_no_user_id(mock_websocket):
    """Test general exception handling when user_id is None."""
    with patch('app.routes.websockets.logger') as mock_logger:
        with patch('app.routes.websockets._handle_websocket_error') as mock_error_handler:
            error = Exception("Auth failed")
            await _handle_general_exception(error, None, mock_websocket)
            
            # Should log the error
            mock_logger.error.assert_called_once()
            # Should NOT call error handler when user_id is None
            mock_error_handler.assert_not_called()


@pytest.mark.asyncio
async def test_handle_websocket_exceptions_with_value_error(mock_websocket):
    """Test that ValueError (auth errors) are handled without disconnect."""
    with patch('app.routes.websockets._handle_general_exception') as mock_handler:
        error = ValueError("Authentication failed")
        await _handle_websocket_exceptions(error, "test_user", mock_websocket)
        # Should not call general exception handler for ValueError
        mock_handler.assert_not_called()


@pytest.mark.asyncio
async def test_connection_manager_disconnect_with_missing_websocket():
    """Test disconnect when WebSocket doesn't exist in connection manager."""
    manager = ConnectionManager()
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.application_state = WebSocketState.CONNECTED
    mock_ws.close = AsyncMock()
    
    # Try to disconnect a WebSocket that was never connected
    await manager.disconnect("unknown_user", mock_ws)
    # Should handle gracefully without errors
    # close should not be called for non-existent connection
    mock_ws.close.assert_not_called()


@pytest.mark.asyncio
async def test_websocket_state_transitions():
    """Test WebSocket state handling during connection lifecycle."""
    ws = MagicMock(spec=WebSocket)
    
    # Test CONNECTING state
    ws.client_state = WebSocketState.CONNECTING
    ws.application_state = WebSocketState.CONNECTING
    with patch('app.routes.websockets.manager') as mock_manager:
        await _handle_websocket_error(Exception("Early error"), "user", ws)
        mock_manager.disconnect_user.assert_not_called()
    
    # Test CONNECTED state
    ws.client_state = WebSocketState.CONNECTED
    ws.application_state = WebSocketState.CONNECTED
    with patch('app.routes.websockets.manager') as mock_manager:
        mock_manager.disconnect_user = AsyncMock()
        await _handle_websocket_error(Exception("Connected error"), "user", ws)
        mock_manager.disconnect_user.assert_called_once()
    
    # Test DISCONNECTED state
    ws.client_state = WebSocketState.DISCONNECTED
    ws.application_state = WebSocketState.DISCONNECTED
    with patch('app.routes.websockets.manager') as mock_manager:
        mock_manager.disconnect_user = AsyncMock()
        await _handle_websocket_error(Exception("Post-disconnect error"), "user", ws)
        # Should not try to disconnect already disconnected WebSocket
        mock_manager.disconnect_user.assert_not_called()