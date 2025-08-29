"""
Unit tests for WebSocket state checking regression prevention.

These tests ensure that is_websocket_connected() properly checks both
client_state and application_state attributes, preventing the ABNORMAL_CLOSURE
issue where connections were immediately closing.

To verify these tests catch the regression:
1. Break is_websocket_connected() to only check application_state
2. These tests should fail
3. Restore the fix to check client_state first
4. Tests should pass
"""

import pytest
from unittest.mock import Mock, AsyncMock
from starlette.websockets import WebSocketState

from netra_backend.app.websocket_core.utils import is_websocket_connected


class TestWebSocketStateCheckingRegression:
    """Unit tests to prevent regression of WebSocket state checking bug."""
    
    def test_must_check_client_state_when_present(self):
        """
        REGRESSION TEST: Must check client_state when it exists.
        This test fails if only checking application_state.
        """
        websocket = Mock()
        # Starlette WebSockets have client_state
        websocket.client_state = WebSocketState.CONNECTED
        # May not have application_state or it could be different
        websocket.application_state = WebSocketState.DISCONNECTED
        
        # Must return True because client_state is CONNECTED
        assert is_websocket_connected(websocket) is True, \
            "Failed to check client_state - would cause immediate disconnect"
    
    def test_must_check_client_state_before_application_state(self):
        """
        REGRESSION TEST: client_state must be checked BEFORE application_state.
        This ensures Starlette WebSocket state is prioritized.
        """
        websocket = Mock()
        websocket.client_state = WebSocketState.DISCONNECTED
        websocket.application_state = WebSocketState.CONNECTED
        
        # Must return False because client_state takes precedence
        assert is_websocket_connected(websocket) is False, \
            "client_state must be checked before application_state"
    
    def test_must_handle_missing_application_state(self):
        """
        REGRESSION TEST: Must handle WebSockets without application_state.
        Real Starlette WebSockets don't have application_state.
        """
        websocket = Mock()
        websocket.client_state = WebSocketState.CONNECTED
        # Explicitly remove application_state to simulate real Starlette WebSocket
        if hasattr(websocket, 'application_state'):
            delattr(websocket, 'application_state')
        
        # Must still return True based on client_state alone
        assert is_websocket_connected(websocket) is True, \
            "Failed when application_state is missing - common in Starlette"
    
    def test_must_fallback_to_application_state_when_no_client_state(self):
        """
        REGRESSION TEST: Must check application_state when client_state is missing.
        Some WebSocket implementations might only have application_state.
        """
        websocket = Mock(spec=[])  # No default attributes
        websocket.application_state = WebSocketState.CONNECTED
        
        # Must return True based on application_state
        assert is_websocket_connected(websocket) is True, \
            "Failed to fallback to application_state when client_state missing"
    
    def test_must_return_true_when_no_state_attributes(self):
        """
        REGRESSION TEST: Must default to True when no state attributes exist.
        This allows the receive() call to handle disconnection properly.
        """
        websocket = Mock(spec=[])  # No state attributes at all
        
        # Must default to True to enter the message loop
        assert is_websocket_connected(websocket) is True, \
            "Must default to True when no state attributes - let receive() handle disconnect"
    
    def test_starlette_websocket_simulation(self):
        """
        REGRESSION TEST: Simulate exact Starlette WebSocket behavior.
        This is the real-world scenario that was failing.
        """
        # Simulate a real Starlette WebSocket
        websocket = Mock()
        websocket.client_state = WebSocketState.CONNECTED
        # Starlette doesn't set application_state
        
        # This was returning False before the fix, causing immediate disconnect
        assert is_websocket_connected(websocket) is True, \
            "Failed with Starlette WebSocket - this is the exact bug scenario"
    
    def test_both_states_connected(self):
        """Test when both states indicate connected."""
        websocket = Mock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.application_state = WebSocketState.CONNECTED
        
        assert is_websocket_connected(websocket) is True
    
    def test_both_states_disconnected(self):
        """Test when both states indicate disconnected."""
        websocket = Mock()
        websocket.client_state = WebSocketState.DISCONNECTED
        websocket.application_state = WebSocketState.DISCONNECTED
        
        assert is_websocket_connected(websocket) is False
    
    def test_websocket_state_values(self):
        """
        REGRESSION TEST: Ensure we're checking the correct state values.
        WebSocketState.CONNECTED is the only valid "connected" state.
        """
        websocket = Mock()
        
        # Test all possible WebSocketState values
        for state in [WebSocketState.CONNECTING, WebSocketState.DISCONNECTED]:
            websocket.client_state = state
            assert is_websocket_connected(websocket) is False, \
                f"Should return False for client_state={state}"
        
        websocket.client_state = WebSocketState.CONNECTED
        assert is_websocket_connected(websocket) is True, \
            "Should return True only for CONNECTED state"


class TestWebSocketStateIntegrationWithManager:
    """Integration tests with WebSocket manager to prevent state issues."""
    
    @pytest.mark.asyncio
    async def test_manager_must_accept_starlette_websocket(self):
        """
        REGRESSION TEST: Manager must work with Starlette WebSocket state.
        """
        from netra_backend.app.websocket_core.manager import WebSocketManager
        
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        # No application_state (like real Starlette)
        websocket.send_json = AsyncMock()
        
        # This should work without checking application_state
        connection_id = await manager.connect_user("test_user", websocket)
        assert connection_id is not None
        assert manager.is_user_connected("test_user")
        
        # Cleanup
        await manager.disconnect_user(connection_id)
    
    @pytest.mark.asyncio
    async def test_safe_send_must_work_with_client_state_only(self):
        """
        REGRESSION TEST: safe_websocket_send must work with client_state only.
        """
        from netra_backend.app.websocket_core.utils import safe_websocket_send
        
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.send_json = AsyncMock()
        
        # Must successfully send when only client_state is CONNECTED
        result = await safe_websocket_send(websocket, {"test": "data"})
        assert result is True
        websocket.send_json.assert_called_once_with({"test": "data"})
    
    @pytest.mark.asyncio
    async def test_safe_close_must_work_with_client_state_only(self):
        """
        REGRESSION TEST: safe_websocket_close must work with client_state only.
        """
        from netra_backend.app.websocket_core.utils import safe_websocket_close
        
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.close = AsyncMock()
        
        # Must successfully close when only client_state is CONNECTED
        await safe_websocket_close(websocket)
        websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_loop_enters_with_client_state_only(self):
        """
        REGRESSION TEST: Message loop must enter when only client_state is CONNECTED.
        This simulates the exact scenario that was failing.
        """
        from netra_backend.app.routes.websocket import _handle_websocket_messages
        from starlette.websockets import WebSocketDisconnect
        
        websocket = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTED
        # Simulate immediate disconnect (what was happening in the bug)
        websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1006))
        
        # Mock dependencies
        ws_manager = Mock()
        message_router = Mock()
        connection_monitor = Mock(
            get_connection_start_time=Mock(return_value=0),
            update_activity=Mock()
        )
        security_manager = Mock()
        heartbeat = Mock()
        
        # Should enter the loop at least once (not immediately exit)
        # The WebSocketDisconnect should be caught and handled properly
        await _handle_websocket_messages(
            websocket=websocket,
            user_id="test_user",
            connection_id="test_conn",
            ws_manager=ws_manager,
            message_router=message_router,
            connection_monitor=connection_monitor,
            security_manager=security_manager,
            heartbeat=heartbeat
        )
        
        # Verify we attempted to receive (entered the loop)
        websocket.receive_text.assert_called()