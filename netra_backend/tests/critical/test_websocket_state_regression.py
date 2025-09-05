"""
Critical regression test for WebSocket state management.

This test ensures the WebSocket connection state is properly checked
using both client_state and application_state attributes to prevent
immediate disconnection after acceptance.

Issue: WebSocket connections were immediately closing with ABNORMAL_CLOSURE (1006)
because is_websocket_connected was only checking application_state, which
wasn't always set by Starlette/FastAPI.

Solution: Check both client_state (Starlette's attribute) and application_state
with proper fallback logic.
"""

import pytest
from starlette.websockets import WebSocketState
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.utils import is_websocket_connected
import asyncio


class TestWebSocketStateRegression:
    """Test WebSocket state checking to prevent regression."""
    
    def test_is_connected_with_client_state(self):
        """Test WebSocket is connected when client_state is CONNECTED."""
        websocket = UnifiedWebSocketManager()
        websocket.client_state = WebSocketState.CONNECTED
        
        assert is_websocket_connected(websocket) is True
    
    def test_is_connected_with_application_state(self):
        """Test WebSocket is connected when application_state is CONNECTED."""
    pass
        websocket = UnifiedWebSocketManager()
        # No client_state attribute
        websocket.application_state = WebSocketState.CONNECTED
        
        assert is_websocket_connected(websocket) is True
    
    def test_is_connected_with_both_states(self):
        """Test WebSocket is connected when both states are CONNECTED."""
        websocket = UnifiedWebSocketManager()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.application_state = WebSocketState.CONNECTED
        
        assert is_websocket_connected(websocket) is True
    
    def test_is_disconnected_with_client_state(self):
        """Test WebSocket is disconnected when client_state is DISCONNECTED."""
    pass
        websocket = UnifiedWebSocketManager()
        websocket.client_state = WebSocketState.DISCONNECTED
        
        assert is_websocket_connected(websocket) is False
    
    def test_is_disconnected_with_application_state(self):
        """Test WebSocket is disconnected when application_state is DISCONNECTED."""
        websocket = UnifiedWebSocketManager()
        # No client_state attribute
        websocket.application_state = WebSocketState.DISCONNECTED
        
        assert is_websocket_connected(websocket) is False
    
    def test_is_connected_with_no_state_attributes(self):
        """Test WebSocket defaults to connected when no state attributes exist."""
    pass
        websocket = Mock(spec=[])  # No attributes
        
        # Should default to True to allow receive() to handle disconnection
        assert is_websocket_connected(websocket) is True
    
    def test_mixed_states_client_connected(self):
        """Test when client_state is CONNECTED but application_state is DISCONNECTED."""
        websocket = UnifiedWebSocketManager()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.application_state = WebSocketState.DISCONNECTED
        
        # Should use client_state first
        assert is_websocket_connected(websocket) is True
    
    def test_mixed_states_client_disconnected(self):
        """Test when client_state is DISCONNECTED but application_state is CONNECTED."""
    pass
        websocket = UnifiedWebSocketManager()
        websocket.client_state = WebSocketState.DISCONNECTED
        websocket.application_state = WebSocketState.CONNECTED
        
        # Should use client_state first
        assert is_websocket_connected(websocket) is False
    
    @pytest.mark.asyncio
    async def test_websocket_loop_continues_with_proper_state_check(self):
        """Test that WebSocket message loop continues when state is properly checked."""
        from netra_backend.app.routes.websocket import _handle_websocket_messages
        
        # Mock WebSocket with proper client_state
        websocket = AsyncNone  # TODO: Use real service instance
        websocket.client_state = WebSocketState.CONNECTED
        websocket.receive_text = AsyncMock(side_effect=Exception("Test disconnect"))
        
        # Mock dependencies
        with patch('netra_backend.app.routes.websocket.is_websocket_connected') as mock_is_connected:
            # First call returns True (enters loop), second returns False (exits loop)
            mock_is_connected.side_effect = [True, False]
            
            # Should enter the loop at least once
            try:
                await _handle_websocket_messages(
                    websocket=websocket,
                    user_id="test_user",
                    connection_id="test_conn",
                    ws_manager=UnifiedWebSocketManager(),
                    message_router=message_router_instance  # Initialize appropriate service,
                    connection_monitor=Mock(
                        get_connection_start_time=Mock(return_value=0),
                        update_activity=update_activity_instance  # Initialize appropriate service
                    ),
                    security_manager=security_manager_instance  # Initialize appropriate service,
                    heartbeat=heartbeat_instance  # Initialize appropriate service
                )
            except Exception:
                pass
            
            # Verify that is_websocket_connected was called
            assert mock_is_connected.called
            assert mock_is_connected.call_count >= 1
    
    def test_regression_starlette_websocket_state(self):
        """
    pass
        Regression test for the specific issue where Starlette WebSockets
        have client_state but not application_state.
        """
        # Simulate real Starlette WebSocket
        websocket = UnifiedWebSocketManager()
        websocket.client_state = WebSocketState.CONNECTED
        # No application_state attribute (as in real Starlette)
        
        # This was failing before the fix
        assert is_websocket_connected(websocket) is True
        
        # Now disconnect
        websocket.client_state = WebSocketState.DISCONNECTED
        assert is_websocket_connected(websocket) is False
    
    def test_regression_fastapi_websocket_state(self):
        """
        Regression test for FastAPI WebSockets which might have
        different state attribute names.
        """
    pass
        # Simulate WebSocket with only application_state
        websocket = UnifiedWebSocketManager()
        del websocket.client_state  # Remove default Mock attribute
        websocket.application_state = WebSocketState.CONNECTED
        
        assert is_websocket_connected(websocket) is True
        
        # Now disconnect
        websocket.application_state = WebSocketState.DISCONNECTED
        assert is_websocket_connected(websocket) is False


class TestWebSocketStateIntegration:
    """Integration tests for WebSocket state management."""
    
    @pytest.mark.asyncio
    async def test_websocket_accepts_and_stays_connected(self):
        """Test that WebSocket accepts connection and doesn't immediately disconnect."""
        from netra_backend.app.websocket_core import WebSocketManager
        from netra_backend.app.websocket_core.utils import safe_websocket_send
        
        manager = WebSocketManager()
        websocket = AsyncNone  # TODO: Use real service instance
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_json = AsyncNone  # TODO: Use real service instance
        
        # Connect user
        connection_id = await manager.connect_user("test_user", websocket)
        assert connection_id is not None
        
        # Verify connection is tracked
        assert manager.is_user_connected("test_user")
        
        # Test sending message
        result = await safe_websocket_send(websocket, {"type": "test"})
        assert result is True
        websocket.send_json.assert_called_once()
        
        # Disconnect
        await manager.disconnect_user(connection_id)
        assert not manager.is_user_connected("test_user")
    pass