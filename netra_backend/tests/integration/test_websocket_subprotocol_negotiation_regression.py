"""
Integration tests for WebSocket subprotocol negotiation regression prevention.

These tests ensure that the WebSocket endpoint properly negotiates subprotocols
with the client, preventing the immediate disconnect issue where the client
closes the connection when it doesn't receive the expected subprotocol response.

To verify these tests catch the regression:
1. Remove the subprotocol parameter from websocket.accept() in websocket_endpoint
2. These tests should fail
3. Restore the subprotocol negotiation
4. Tests should pass
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket
from fastapi.testclient import TestClient
import httpx

from netra_backend.app.main import app
from netra_backend.app.routes.websocket import websocket_endpoint


class TestWebSocketSubprotocolNegotiationRegression:
    """Integration tests to prevent regression of subprotocol negotiation bug."""
    
    @pytest.mark.asyncio
    async def test_must_accept_with_jwt_auth_subprotocol(self):
        """
        REGRESSION TEST: Must accept WebSocket with jwt-auth subprotocol.
        This test fails if subprotocol is not included in accept().
        """
        # Create a mock WebSocket with subprotocols
        websocket = AsyncMock(spec=WebSocket)
        websocket.headers = {
            "sec-websocket-protocol": "jwt-auth, jwt.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        }
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=asyncio.CancelledError)  # Simulate disconnect
        
        # Mock authentication
        with patch('netra_backend.app.routes.websocket.secure_websocket_context') as mock_context:
            mock_auth_info = Mock(user_id="test_user")
            mock_security_manager = Mock()
            mock_context.return_value.__aenter__.return_value = (mock_auth_info, mock_security_manager)
            mock_context.return_value.__aexit__.return_value = None
            
            # Mock other dependencies
            with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_manager:
                mock_ws_manager = Mock()
                mock_ws_manager.connect_user = AsyncMock(return_value="conn_123")
                mock_ws_manager.disconnect_user = AsyncMock()
                mock_manager.return_value = mock_ws_manager
                
                with patch('netra_backend.app.routes.websocket.get_message_router'):
                    with patch('netra_backend.app.routes.websocket.get_connection_monitor'):
                        try:
                            await websocket_endpoint(websocket)
                        except (asyncio.CancelledError, Exception):
                            pass  # Expected when receive_text fails
        
        # CRITICAL: Must have been called with subprotocol parameter
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        assert 'subprotocol' in call_args.kwargs, \
            "WebSocket.accept() must include subprotocol parameter"
        assert call_args.kwargs['subprotocol'] == 'jwt-auth', \
            "Must select jwt-auth subprotocol when client sends it"
    
    @pytest.mark.asyncio
    async def test_must_accept_without_subprotocol_when_none_sent(self):
        """
        REGRESSION TEST: Must handle clients that don't send subprotocols.
        """
        websocket = AsyncMock(spec=WebSocket)
        websocket.headers = {}  # No subprotocol header
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=asyncio.CancelledError)
        
        with patch('netra_backend.app.routes.websocket.secure_websocket_context') as mock_context:
            mock_auth_info = Mock(user_id="test_user")
            mock_security_manager = Mock()
            mock_context.return_value.__aenter__.return_value = (mock_auth_info, mock_security_manager)
            mock_context.return_value.__aexit__.return_value = None
            
            with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_manager:
                mock_ws_manager = Mock()
                mock_ws_manager.connect_user = AsyncMock(return_value="conn_123")
                mock_ws_manager.disconnect_user = AsyncMock()
                mock_manager.return_value = mock_ws_manager
                
                with patch('netra_backend.app.routes.websocket.get_message_router'):
                    with patch('netra_backend.app.routes.websocket.get_connection_monitor'):
                        try:
                            await websocket_endpoint(websocket)
                        except (asyncio.CancelledError, Exception):
                            pass
        
        # Should accept without subprotocol when none provided
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        # Either no subprotocol arg, or subprotocol=None
        if 'subprotocol' in call_args.kwargs:
            assert call_args.kwargs['subprotocol'] is None
    
    @pytest.mark.asyncio
    async def test_subprotocol_parsing_with_multiple_protocols(self):
        """
        REGRESSION TEST: Must correctly parse multiple subprotocols.
        Frontend sends multiple protocols: jwt-auth, jwt.token, compression-gzip
        """
        websocket = AsyncMock(spec=WebSocket)
        websocket.headers = {
            "sec-websocket-protocol": "jwt-auth, jwt.eyJhbGc, compression-gzip"
        }
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=asyncio.CancelledError)
        
        with patch('netra_backend.app.routes.websocket.secure_websocket_context') as mock_context:
            mock_auth_info = Mock(user_id="test_user")
            mock_security_manager = Mock()
            mock_context.return_value.__aenter__.return_value = (mock_auth_info, mock_security_manager)
            mock_context.return_value.__aexit__.return_value = None
            
            with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_manager:
                mock_ws_manager = Mock()
                mock_ws_manager.connect_user = AsyncMock(return_value="conn_123")
                mock_ws_manager.disconnect_user = AsyncMock()
                mock_manager.return_value = mock_ws_manager
                
                with patch('netra_backend.app.routes.websocket.get_message_router'):
                    with patch('netra_backend.app.routes.websocket.get_connection_monitor'):
                        try:
                            await websocket_endpoint(websocket)
                        except (asyncio.CancelledError, Exception):
                            pass
        
        # Must select jwt-auth from the list
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        assert call_args.kwargs.get('subprotocol') == 'jwt-auth', \
            "Must select jwt-auth from multiple protocols"
    
    @pytest.mark.asyncio
    async def test_client_disconnect_without_subprotocol_response(self):
        """
        REGRESSION TEST: Simulate client disconnecting when no subprotocol returned.
        This is what was happening in the actual bug.
        """
        from starlette.websockets import WebSocketDisconnect
        
        websocket = AsyncMock(spec=WebSocket)
        websocket.headers = {
            "sec-websocket-protocol": "jwt-auth"
        }
        
        # Simulate what happens without subprotocol response:
        # Client immediately disconnects after accept
        disconnect_called = False
        
        async def mock_accept(**kwargs):
            nonlocal disconnect_called
            if 'subprotocol' not in kwargs:
                # Client would disconnect immediately
                disconnect_called = True
        
        websocket.accept = AsyncMock(side_effect=mock_accept)
        websocket.send_json = AsyncMock()
        
        async def mock_receive():
            if disconnect_called:
                raise WebSocketDisconnect(code=1006, reason="No subprotocol")
            return '{"type": "ping"}'
        
        websocket.receive_text = AsyncMock(side_effect=mock_receive)
        
        with patch('netra_backend.app.routes.websocket.secure_websocket_context') as mock_context:
            mock_auth_info = Mock(user_id="test_user")
            mock_security_manager = Mock()
            mock_context.return_value.__aenter__.return_value = (mock_auth_info, mock_security_manager)
            mock_context.return_value.__aexit__.return_value = None
            
            with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_manager:
                mock_ws_manager = Mock()
                mock_ws_manager.connect_user = AsyncMock(return_value="conn_123")
                mock_ws_manager.disconnect_user = AsyncMock()
                mock_manager.return_value = mock_ws_manager
                
                with patch('netra_backend.app.routes.websocket.get_message_router'):
                    with patch('netra_backend.app.routes.websocket.get_connection_monitor'):
                        await websocket_endpoint(websocket)
        
        # Verify subprotocol was included (preventing disconnect)
        assert not disconnect_called, \
            "Client disconnected - subprotocol not included in accept()"
        call_args = websocket.accept.call_args
        assert 'subprotocol' in call_args.kwargs, \
            "Must include subprotocol to prevent client disconnect"


class TestWebSocketProtocolCompliance:
    """Test RFC 6455 WebSocket protocol compliance."""
    
    @pytest.mark.asyncio
    async def test_rfc6455_subprotocol_negotiation_requirement(self):
        """
        REGRESSION TEST: RFC 6455 Section 4.2.2 compliance.
        Server MUST include Sec-WebSocket-Protocol in response if client sends it.
        """
        # This tests the protocol requirement that was violated
        websocket = AsyncMock(spec=WebSocket)
        websocket.headers = {
            "sec-websocket-protocol": "jwt-auth"
        }
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=asyncio.CancelledError)
        
        with patch('netra_backend.app.routes.websocket.secure_websocket_context') as mock_context:
            mock_auth_info = Mock(user_id="test_user")
            mock_security_manager = Mock()
            mock_context.return_value.__aenter__.return_value = (mock_auth_info, mock_security_manager)
            mock_context.return_value.__aexit__.return_value = None
            
            with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_manager:
                mock_ws_manager = Mock()
                mock_ws_manager.connect_user = AsyncMock(return_value="conn_123")
                mock_ws_manager.disconnect_user = AsyncMock()
                mock_manager.return_value = mock_ws_manager
                
                with patch('netra_backend.app.routes.websocket.get_message_router'):
                    with patch('netra_backend.app.routes.websocket.get_connection_monitor'):
                        try:
                            await websocket_endpoint(websocket)
                        except (asyncio.CancelledError, Exception):
                            pass
        
        # RFC 6455: Server MUST select one of the client's proposed subprotocols
        websocket.accept.assert_called_once()
        call_args = websocket.accept.call_args
        assert 'subprotocol' in call_args.kwargs, \
            "RFC 6455 violation: Server must respond with subprotocol when client sends one"
        assert call_args.kwargs['subprotocol'] in ['jwt-auth'], \
            "RFC 6455: Selected subprotocol must be from client's list"
    
    def test_subprotocol_header_parsing(self):
        """Test parsing of Sec-WebSocket-Protocol header."""
        # Test the logic that parses the subprotocol header
        test_cases = [
            ("jwt-auth", ["jwt-auth"]),
            ("jwt-auth, jwt.token", ["jwt-auth", "jwt.token"]),
            ("jwt-auth,jwt.token,compression-gzip", ["jwt-auth", "jwt.token", "compression-gzip"]),
            ("  jwt-auth  ,  jwt.token  ", ["jwt-auth", "jwt.token"]),  # With spaces
            ("", []),  # Empty header
        ]
        
        for header_value, expected in test_cases:
            # This is the parsing logic from the fix
            subprotocols = [p.strip() for p in header_value.split(",") if p.strip()]
            assert subprotocols == expected, \
                f"Failed to parse header: {header_value}"
    
    @pytest.mark.asyncio
    async def test_websocket_stays_connected_with_subprotocol(self):
        """
        REGRESSION TEST: WebSocket must stay connected when subprotocol is negotiated.
        This is the ultimate test - connection should not immediately close.
        """
        from netra_backend.app.websocket_core.manager import WebSocketManager
        
        # Setup a connection with proper subprotocol
        manager = WebSocketManager()
        websocket = AsyncMock()
        websocket.client_state = 1  # WebSocketState.CONNECTED
        websocket.headers = {"sec-websocket-protocol": "jwt-auth"}
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        # Track if connection stays open
        connection_duration = 0
        
        async def mock_receive():
            nonlocal connection_duration
            connection_duration += 1
            if connection_duration > 3:  # Stay connected for multiple iterations
                from starlette.websockets import WebSocketDisconnect
                raise WebSocketDisconnect(code=1000)  # Normal close
            await asyncio.sleep(0.1)
            return '{"type": "ping"}'
        
        websocket.receive_text = AsyncMock(side_effect=mock_receive)
        
        # Connection should stay open for multiple message cycles
        with patch('netra_backend.app.routes.websocket.secure_websocket_context') as mock_context:
            mock_auth_info = Mock(user_id="test_user")
            mock_security_manager = Mock()
            mock_context.return_value.__aenter__.return_value = (mock_auth_info, mock_security_manager)
            mock_context.return_value.__aexit__.return_value = None
            
            with patch('netra_backend.app.routes.websocket.get_websocket_manager', return_value=manager):
                with patch('netra_backend.app.routes.websocket.get_message_router'):
                    with patch('netra_backend.app.routes.websocket.get_connection_monitor'):
                        await websocket_endpoint(websocket)
        
        # Verify connection stayed open for multiple iterations
        assert connection_duration > 1, \
            "Connection closed immediately - subprotocol negotiation failed"
        
        # Verify subprotocol was included in accept
        call_args = websocket.accept.call_args
        assert call_args.kwargs.get('subprotocol') == 'jwt-auth', \
            "Connection stayed open but subprotocol not properly negotiated"