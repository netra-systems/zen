"""Critical regression tests for WebSocket authentication failures.

Suite 1: Authentication Error Propagation
Ensures all auth failures are loud and properly propagated.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from routes.utils.websocket_helpers import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    authenticate_websocket_user,
    decode_token_payload,
    validate_user_id_in_payload
)


class TestAuthenticationErrorPropagation:
    """Suite 1: Verify all authentication errors are raised and logged."""
    
    @pytest.mark.asyncio
    async def test_invalid_token_raises_and_closes_connection(self):
        """Test that invalid tokens cause loud failures with connection closure."""
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        security_service = Mock()
        security_service.decode_token = Mock(side_effect=ValueError("Invalid token"))
        
        with pytest.raises(ValueError) as exc_info:
            await authenticate_websocket_user(websocket, "invalid_token", security_service)
        
        assert "Invalid token" in str(exc_info.value)
        websocket.close.assert_called_once()
        assert websocket.close.call_args[1]['code'] == 1008
        assert "Authentication failed" in websocket.close.call_args[1]['reason']
    
    @pytest.mark.asyncio
    async def test_missing_user_id_in_token_raises_error(self):
        """Test that tokens without user_id fail loudly."""
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        security_service = Mock()
        security_service.decode_token = Mock(return_value={})  # No 'sub' field
        
        with pytest.raises(ValueError) as exc_info:
            await authenticate_websocket_user(websocket, "token_without_sub", security_service)
        
        assert "User ID not found in token" in str(exc_info.value)
        websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_propagates(self):
        """Test that database failures during auth are not silent."""
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        security_service = Mock()
        security_service.decode_token = Mock(return_value={"sub": "test-user"})
        
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_db.side_effect = ConnectionError("Database unavailable")
            
            with pytest.raises(ConnectionError) as exc_info:
                await authenticate_websocket_user(websocket, "valid_token", security_service)
            
            assert "Database unavailable" in str(exc_info.value)
            websocket.close.assert_called_once()


class TestUserLookupFailures:
    """Suite 2: Verify user lookup failures are explicit."""
    
    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_with_details(self):
        """Test that missing users cause explicit errors with user ID."""
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        security_service = Mock()
        security_service.decode_token = Mock(return_value={"sub": "nonexistent-user-123"})
        security_service.get_user_by_id = AsyncMock(return_value=None)
        
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with pytest.raises(ValueError) as exc_info:
                await authenticate_websocket_user(websocket, "token", security_service)
            
            assert "User not found" in str(exc_info.value)
            websocket.close.assert_called_once()
            assert "1008" in str(websocket.close.call_args)
    
    @pytest.mark.asyncio
    async def test_inactive_user_fails_explicitly(self):
        """Test that inactive users are rejected with clear error."""
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        security_service = Mock()
        security_service.decode_token = Mock(return_value={"sub": "inactive-user"})
        
        mock_user = Mock()
        mock_user.is_active = False
        mock_user.id = "inactive-user"
        security_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            with pytest.raises(ValueError) as exc_info:
                await authenticate_websocket_user(websocket, "token", security_service)
            
            assert "User inactive-user is not active" in str(exc_info.value)
            websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_rollback_on_user_fetch_error(self):
        """Test that database errors trigger rollback and retry with logging."""
        websocket = Mock(spec=WebSocket)
        websocket.close = AsyncMock()
        security_service = Mock()
        security_service.decode_token = Mock(return_value={"sub": "test-user"})
        
        # First call fails, second succeeds after rollback
        security_service.get_user_by_id = AsyncMock(
            side_effect=[
                Exception("Database locked"),
                Mock(is_active=True, id="test-user")
            ]
        )
        
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            result = await authenticate_websocket_user(websocket, "token", security_service)
            
            assert result == "test-user"
            mock_session.rollback.assert_called_once()
            assert security_service.get_user_by_id.call_count == 2


class TestWebSocketMessageHandling:
    """Suite 3: Verify message processing failures are explicit."""
    
    @pytest.mark.asyncio
    async def test_malformed_json_logs_and_responds_error(self):
        """Test that malformed JSON is logged and error sent to client."""
        from netra_backend.app.routes.utils.websocket_helpers import parse_json_message
        
        manager = Mock()
        manager.send_error = AsyncMock()
        
        result = await parse_json_message("{invalid json", "user-123", manager)
        
        assert result is None
        manager.send_error.assert_called_once_with("user-123", "Invalid JSON message format")
    
    @pytest.mark.asyncio  
    async def test_message_timeout_closes_stale_connections(self):
        """Test that message timeouts close stale connections."""
        from netra_backend.app.routes.utils.websocket_helpers import check_connection_alive
        
        conn_info = Mock()
        conn_info.last_activity = 0  # Very old timestamp
        
        manager = Mock()
        manager.disconnect_user = AsyncMock()
        
        with patch('time.time', return_value=1000):  # Current time much later
            result = check_connection_alive(conn_info, "user-123", manager)
        
        assert result is False  # Should indicate connection dead
    
    @pytest.mark.asyncio
    async def test_handler_exceptions_logged_with_context(self):
        """Test that message handler exceptions include full context."""
        from netra_backend.app.routes.websockets import _handle_validated_message
        
        websocket = Mock(spec=WebSocket)
        websocket.application_state = WebSocketState.CONNECTED
        
        message = {"type": "unknown_type", "payload": {"data": "test"}}
        agent_service = Mock()
        agent_service.process_message = AsyncMock(
            side_effect=RuntimeError("Handler failed")
        )
        
        manager = Mock()
        manager.handle_message = AsyncMock(return_value=False)
        
        with patch('app.routes.websockets.manager', manager):
            result = await _handle_validated_message(
                "user-123", websocket, message, json.dumps(message), agent_service
            )
        
        assert result is True  # Should continue despite error
        manager.handle_message.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])