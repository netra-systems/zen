"""
Tests for MCP WebSocket Transport

Test WebSocket transport for real-time communication.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from starlette.websockets import WebSocketState, WebSocketDisconnect
from app.mcp.transports.websocket_transport import (
    WebSocketTransport, WebSocketConnection
)


class TestWebSocketConnection:
    """Test WebSocket connection wrapper"""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        ws.application_state = WebSocketState.CONNECTED
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        return ws
        
    def test_connection_creation(self, mock_websocket):
        """Test connection creation"""
        conn = WebSocketConnection(mock_websocket, "session123")
        
        assert conn.websocket == mock_websocket
        assert conn.session_id == "session123"
        assert isinstance(conn.connected_at, datetime)
        assert isinstance(conn.last_activity, datetime)
        assert conn.message_count == 0
        
    @pytest.mark.asyncio
    async def test_send_json(self, mock_websocket):
        """Test sending JSON data"""
        conn = WebSocketConnection(mock_websocket, "session123")
        
        data = {"test": "data"}
        await conn.send_json(data)
        
        mock_websocket.send_json.assert_called_once_with(data)
        assert conn.message_count == 1
        assert conn.last_activity > conn.connected_at
        
    @pytest.mark.asyncio
    async def test_send_json_disconnected(self, mock_websocket):
        """Test sending JSON when disconnected"""
        mock_websocket.application_state = WebSocketState.DISCONNECTED
        conn = WebSocketConnection(mock_websocket, "session123")
        
        with pytest.raises(Exception):
            await conn.send_json({"test": "data"})
            
        mock_websocket.send_json.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_receive_json(self, mock_websocket):
        """Test receiving JSON data"""
        mock_websocket.receive_json.return_value = {"received": "data"}
        conn = WebSocketConnection(mock_websocket, "session123")
        
        data = await conn.receive_json()
        
        assert data == {"received": "data"}
        assert conn.last_activity > conn.connected_at


class TestWebSocketTransport:
    """Test WebSocket transport functionality"""
    
    @pytest.fixture
    def transport(self):
        """Create WebSocket transport"""
        return WebSocketTransport()
        
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        ws.application_state = WebSocketState.CONNECTED
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.close = AsyncMock()
        return ws
        
    @pytest.mark.asyncio
    async def test_transport_initialization(self, transport):
        """Test transport initialization"""
        assert transport.server is not None
        assert transport.connections == {}
        assert transport.connection_locks == {}
        
    @pytest.mark.asyncio
    async def test_handle_websocket_connection(self, transport, mock_websocket):
        """Test handling WebSocket connection"""
        # Simulate connection and immediate disconnect
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()
        
        await transport.handle_websocket(mock_websocket)
        
        mock_websocket.accept.assert_called_once()
        mock_websocket.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_websocket_welcome_message(self, transport, mock_websocket):
        """Test welcome message on connection"""
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()
        
        await transport.handle_websocket(mock_websocket)
        
        # Check welcome message was sent
        calls = mock_websocket.send_json.call_args_list
        assert len(calls) > 0
        welcome = calls[0][0][0]
        assert welcome["method"] == "connection.established"
        assert "session_id" in welcome["params"]
        assert welcome["params"]["server"] == "Netra MCP Server"
        
    @pytest.mark.asyncio
    async def test_message_processing(self, transport, mock_websocket):
        """Test message processing"""
        # Mock server response
        transport.server.handle_request = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "result": {"success": True},
            "id": 1
        })
        
        # Simulate receiving one message then disconnect
        mock_websocket.receive_json.side_effect = [
            {"jsonrpc": "2.0", "method": "test", "id": 1},
            WebSocketDisconnect()
        ]
        
        await transport.handle_websocket(mock_websocket)
        
        # Verify request was processed
        transport.server.handle_request.assert_called_once()
        call_args = transport.server.handle_request.call_args[0]
        assert call_args[0]["method"] == "test"
        
    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, transport, mock_websocket):
        """Test handling of JSON decode errors"""
        mock_websocket.receive_json.side_effect = json.JSONDecodeError("test", "doc", 0)
        
        # Use a flag to stop after first error
        error_sent = False
        original_send = mock_websocket.send_json
        
        async def send_json_once(*args, **kwargs):
            nonlocal error_sent
            if not error_sent:
                error_sent = True
                await original_send(*args, **kwargs)
                raise WebSocketDisconnect()
                
        mock_websocket.send_json = send_json_once
        
        await transport.handle_websocket(mock_websocket)
        
        # Check error response was sent
        original_send.assert_called_once()
        error_response = original_send.call_args[0][0]
        assert error_response["error"]["code"] == -32700
        
    @pytest.mark.asyncio
    async def test_initialization_adds_transport_info(self, transport, mock_websocket):
        """Test that initialization adds transport info"""
        transport.server.handle_request = AsyncMock()
        
        mock_websocket.receive_json.side_effect = [
            {"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
            WebSocketDisconnect()
        ]
        
        await transport.handle_websocket(mock_websocket)
        
        # Check transport was added to params
        call_args = transport.server.handle_request.call_args[0]
        assert call_args[0]["params"]["transport"] == "websocket"
        
    @pytest.mark.asyncio
    async def test_concurrent_request_processing(self, transport, mock_websocket):
        """Test concurrent request processing with locks"""
        transport.server.handle_request = AsyncMock()
        
        # Simulate multiple messages
        mock_websocket.receive_json.side_effect = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
            WebSocketDisconnect()
        ]
        
        await transport.handle_websocket(mock_websocket)
        
        # Both requests should be processed
        assert transport.server.handle_request.call_count == 2
        
    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, transport, mock_websocket):
        """Test broadcasting to specific session"""
        # Setup connection
        conn = WebSocketConnection(mock_websocket, "session123")
        transport.connections["session123"] = conn
        
        message = {"type": "broadcast", "data": "test"}
        await transport.broadcast_to_session("session123", message)
        
        mock_websocket.send_json.assert_called_once_with(message)
        
    @pytest.mark.asyncio
    async def test_broadcast_to_session_not_found(self, transport):
        """Test broadcasting to non-existent session"""
        # Should not raise error
        await transport.broadcast_to_session("nonexistent", {"data": "test"})
        
    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, transport):
        """Test broadcasting to all sessions"""
        # Setup multiple connections
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()
        
        transport.connections["session1"] = WebSocketConnection(ws1, "session1")
        transport.connections["session2"] = WebSocketConnection(ws2, "session2")
        
        message = {"type": "broadcast", "data": "test"}
        await transport.broadcast_to_all(message)
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
        
    @pytest.mark.asyncio
    async def test_broadcast_to_all_with_exclude(self, transport):
        """Test broadcasting with exclusion"""
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()
        
        transport.connections["session1"] = WebSocketConnection(ws1, "session1")
        transport.connections["session2"] = WebSocketConnection(ws2, "session2")
        
        message = {"type": "broadcast", "data": "test"}
        await transport.broadcast_to_all(message, exclude={"session1"})
        
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once_with(message)
        
    def test_get_active_sessions(self, transport):
        """Test getting active sessions"""
        ws1 = Mock()
        ws2 = Mock()
        
        conn1 = WebSocketConnection(ws1, "session1")
        conn1.message_count = 5
        conn2 = WebSocketConnection(ws2, "session2")
        conn2.message_count = 10
        
        transport.connections["session1"] = conn1
        transport.connections["session2"] = conn2
        
        sessions = transport.get_active_sessions()
        
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "session1"
        assert sessions[0]["message_count"] == 5
        assert sessions[1]["session_id"] == "session2"
        assert sessions[1]["message_count"] == 10
        
    @pytest.mark.asyncio
    async def test_close_session(self, transport, mock_websocket):
        """Test closing specific session"""
        conn = WebSocketConnection(mock_websocket, "session123")
        transport.connections["session123"] = conn
        transport.connection_locks["session123"] = asyncio.Lock()
        
        await transport.close_session("session123")
        
        mock_websocket.close.assert_called_once()
        assert "session123" not in transport.connections
        assert "session123" not in transport.connection_locks
        
    @pytest.mark.asyncio
    async def test_close_nonexistent_session(self, transport):
        """Test closing non-existent session"""
        # Should not raise error
        await transport.close_session("nonexistent")
        
    @pytest.mark.asyncio
    async def test_heartbeat_loop(self, transport, mock_websocket):
        """Test heartbeat loop functionality"""
        conn = WebSocketConnection(mock_websocket, "session123")
        transport.connections["session123"] = conn
        
        # Run heartbeat once
        heartbeat_task = asyncio.create_task(
            transport._heartbeat_loop(conn)
        )
        
        # Wait briefly then cancel
        await asyncio.sleep(0.1)
        heartbeat_task.cancel()
        
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_error_in_process_request(self, transport, mock_websocket):
        """Test error handling in request processing"""
        transport.server.handle_request = AsyncMock(
            side_effect=Exception("Processing error")
        )
        
        conn = WebSocketConnection(mock_websocket, "session123")
        transport.connections["session123"] = conn
        transport.connection_locks["session123"] = asyncio.Lock()
        
        await transport._process_request(conn, {
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        # Error response should be sent
        mock_websocket.send_json.assert_called_once()
        error_response = mock_websocket.send_json.call_args[0][0]
        assert error_response["error"]["code"] == -32603
        assert "Processing error" in error_response["error"]["message"]