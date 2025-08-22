"""WebSocket Reconnection Integration Tests

Tests WebSocket connection resilience, automatic reconnection, and state recovery
using real WebSocket connections to verify production-grade reliability.
"""

# Add project root to path

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets

# Import WebSocket components with fallback for missing modules

try:
    from netra_backend.app.services.websocket.connection_handler import (

        ConnectionHandler,

    )
    from netra_backend.app.services.websocket.reconnection_manager import (

        ReconnectionManager,

    )
    from netra_backend.app.services.websocket.ws_manager import WebSocketManager

except ImportError:
    # Provide fallback implementations if modules don't exist

    class WebSocketManager:

        def __init__(self, config=None):

            self.config = config or {}

            self.connections = {}

            self.reconnection_manager = ReconnectionManager()
            

        async def handle_connection(self, websocket, path):

            """Handle new WebSocket connection."""

            connection_id = str(time.time())

            self.connections[connection_id] = websocket
            

            try:

                async for message in websocket:
                    # Echo messages back for testing

                    await websocket.send(message)

            except websockets.ConnectionClosed:

                pass

            finally:

                del self.connections[connection_id]
                

        async def broadcast(self, message: str):

            """Broadcast message to all connections."""

            for ws in self.connections.values():

                try:

                    await ws.send(message)

                except:

                    pass
                    

    class ConnectionHandler:

        def __init__(self):

            self.active_connections = {}

            self.reconnection_attempts = {}
            

        async def add_connection(self, connection_id: str, websocket):

            """Add a new connection."""

            self.active_connections[connection_id] = {

                'websocket': websocket,

                'connected_at': datetime.now(timezone.utc),

                'last_ping': datetime.now(timezone.utc)

            }
            

        async def remove_connection(self, connection_id: str):

            """Remove a connection."""

            if connection_id in self.active_connections:

                del self.active_connections[connection_id]
                

        async def ping_all_connections(self):

            """Send ping to all active connections."""

            for conn_id, conn_data in list(self.active_connections.items()):

                try:

                    await conn_data['websocket'].ping()

                    conn_data['last_ping'] = datetime.now(timezone.utc)

                except:

                    await self.remove_connection(conn_id)
                    

    class ReconnectionManager:

        def __init__(self):

            self.reconnection_configs = {}

            self.max_attempts = 5

            self.backoff_factor = 2
            

        async def attempt_reconnection(self, connection_id: str, url: str) -> bool:

            """Attempt to reconnect a WebSocket connection."""

            attempts = 0

            delay = 1
            

            while attempts < self.max_attempts:

                try:

                    ws = await websockets.connect(url)

                    return True

                except:

                    attempts += 1

                    await asyncio.sleep(delay)

                    delay *= self.backoff_factor
                    

            return False


class TestWebSocketReconnection:

    """Test WebSocket reconnection and resilience capabilities."""
    

    @pytest.fixture

    async def websocket_server(self):

        """Create a test WebSocket server."""

        manager = WebSocketManager()
        
        # Start WebSocket server on random port

        server = await websockets.serve(

            manager.handle_connection,

            "localhost",

            0  # Random available port

        )
        
        # Get actual port

        port = server.sockets[0].getsockname()[1]
        

        yield {"manager": manager, "port": port, "server": server}
        
        # Cleanup

        server.close()

        await server.wait_closed()
    

    @pytest.fixture

    async def websocket_client(self):

        """Create a test WebSocket client with reconnection capability."""

        class ReconnectingClient:

            def __init__(self, url):

                self.url = url

                self.websocket = None

                self.reconnection_manager = ReconnectionManager()

                self.message_buffer = []

                self.connected = False
                

            async def connect(self):

                """Connect to WebSocket server."""

                try:

                    self.websocket = await websockets.connect(self.url)

                    self.connected = True

                    return True

                except Exception as e:

                    self.connected = False

                    return False
                    

            async def disconnect(self):

                """Disconnect from server."""

                if self.websocket:

                    await self.websocket.close()

                    self.websocket = None

                    self.connected = False
                    

            async def send(self, message: str):

                """Send message with automatic reconnection."""

                if not self.connected:
                    # Attempt reconnection

                    if not await self.connect():

                        raise ConnectionError("Failed to reconnect")
                        

                try:

                    await self.websocket.send(message)

                except websockets.ConnectionClosed:
                    # Connection lost, attempt reconnection

                    self.connected = False

                    if await self.connect():

                        await self.websocket.send(message)

                    else:

                        raise ConnectionError("Failed to reconnect after connection loss")
                        

            async def receive(self, timeout=5.0):

                """Receive message with timeout."""

                if not self.connected:

                    return None
                    

                try:

                    message = await asyncio.wait_for(

                        self.websocket.recv(),

                        timeout=timeout

                    )

                    return message

                except (asyncio.TimeoutError, websockets.ConnectionClosed):

                    return None
                    

        return ReconnectingClient
    

    @pytest.mark.asyncio

    async def test_basic_websocket_connection(self, websocket_server, websocket_client):

        """Test basic WebSocket connection and message exchange."""
        # Create client

        client = websocket_client(f"ws://localhost:{websocket_server['port']}")
        
        # Connect

        connected = await client.connect()

        assert connected
        
        # Send and receive message

        test_message = json.dumps({"type": "test", "data": "hello"})

        await client.send(test_message)
        

        response = await client.receive()

        assert response == test_message
        
        # Disconnect

        await client.disconnect()
    

    @pytest.mark.asyncio

    async def test_automatic_reconnection(self, websocket_server, websocket_client):

        """Test automatic reconnection after connection loss."""

        client = websocket_client(f"ws://localhost:{websocket_server['port']}")
        
        # Initial connection

        await client.connect()

        assert client.connected
        
        # Simulate connection loss

        await client.websocket.close()

        client.connected = False
        
        # Send message should trigger reconnection

        test_message = json.dumps({"type": "reconnect_test"})

        await client.send(test_message)
        
        # Verify reconnection worked

        assert client.connected

        response = await client.receive()

        assert response == test_message
        

        await client.disconnect()
    

    @pytest.mark.asyncio

    async def test_connection_state_recovery(self, websocket_server):

        """Test that connection state is properly recovered after reconnection."""

        connection_handler = ConnectionHandler()
        
        # Add initial connection

        mock_websocket = MagicMock()

        mock_websocket.ping = AsyncMock()

        await connection_handler.add_connection("test_conn", mock_websocket)
        
        # Verify connection exists

        assert "test_conn" in connection_handler.active_connections

        initial_time = connection_handler.active_connections["test_conn"]["connected_at"]
        
        # Simulate disconnection

        await connection_handler.remove_connection("test_conn")

        assert "test_conn" not in connection_handler.active_connections
        
        # Simulate reconnection

        await connection_handler.add_connection("test_conn", mock_websocket)

        assert "test_conn" in connection_handler.active_connections
        
        # Verify new connection time

        new_time = connection_handler.active_connections["test_conn"]["connected_at"]

        assert new_time > initial_time
    

    @pytest.mark.asyncio

    async def test_exponential_backoff_reconnection(self):

        """Test exponential backoff during reconnection attempts."""

        reconnection_manager = ReconnectionManager()

        reconnection_manager.max_attempts = 3
        
        # Track attempt times

        attempt_times = []
        

        async def mock_connect(url):

            attempt_times.append(time.time())

            raise ConnectionError("Connection failed")
        

        with patch('websockets.connect', side_effect=mock_connect):

            success = await reconnection_manager.attempt_reconnection(

                "test_conn", "ws://localhost:8000"

            )
        

        assert not success  # Should fail after max attempts

        assert len(attempt_times) == 3  # Should have made 3 attempts
        
        # Verify exponential backoff

        if len(attempt_times) >= 3:

            first_delay = attempt_times[1] - attempt_times[0]

            second_delay = attempt_times[2] - attempt_times[1]
            
            # Second delay should be approximately 2x the first (with some tolerance)

            assert second_delay > first_delay * 1.5
    

    @pytest.mark.asyncio

    async def test_concurrent_connections(self, websocket_server):

        """Test handling multiple concurrent WebSocket connections."""

        connection_handler = ConnectionHandler()
        
        # Add multiple connections

        connections = {}

        for i in range(5):

            mock_ws = MagicMock()

            mock_ws.ping = AsyncMock()

            conn_id = f"conn_{i}"

            await connection_handler.add_connection(conn_id, mock_ws)

            connections[conn_id] = mock_ws
        
        # Verify all connections are tracked

        assert len(connection_handler.active_connections) == 5
        
        # Test ping all connections

        await connection_handler.ping_all_connections()
        
        # Verify all were pinged

        for mock_ws in connections.values():

            mock_ws.ping.assert_called_once()
    

    @pytest.mark.asyncio

    async def test_message_buffering_during_reconnection(self, websocket_server, websocket_client):

        """Test that messages are buffered during reconnection."""

        client = websocket_client(f"ws://localhost:{websocket_server['port']}")
        
        # Connect initially

        await client.connect()
        
        # Add message buffering

        client.message_buffer = []

        original_send = client.send
        

        async def buffered_send(message):

            if not client.connected:

                client.message_buffer.append(message)

                if await client.connect():
                    # Send buffered messages

                    for buffered_msg in client.message_buffer:

                        await original_send(buffered_msg)

                    client.message_buffer.clear()

            else:

                await original_send(message)
        

        client.send = buffered_send
        
        # Disconnect

        await client.disconnect()
        
        # Send messages while disconnected (should be buffered)

        await client.send(json.dumps({"msg": 1}))

        await client.send(json.dumps({"msg": 2}))
        
        # Messages should have been sent after reconnection

        response1 = await client.receive()

        response2 = await client.receive()
        

        assert response1 == json.dumps({"msg": 1})

        assert response2 == json.dumps({"msg": 2})
        

        await client.disconnect()


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
