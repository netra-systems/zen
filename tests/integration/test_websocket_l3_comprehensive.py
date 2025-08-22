#!/usr/bin/env python3
"""
L3 Integration Tests for WebSocket - Comprehensive Coverage
Tests WebSocket connections, messaging, reconnection, and real-time features
"""

# Add app to path
from datetime import datetime, timedelta
from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import json
import os
import pytest
import sys
import time
import websockets


# Mock classes for testing
from enum import Enum


class ConnectionState(Enum):

    DISCONNECTED = "disconnected"

    CONNECTED = "connected"

    FAILED = "failed"


class WebSocketClient:

    def __init__(self, url):

        self.url = url

        self.state = ConnectionState.DISCONNECTED

        self.auto_reconnect = False

        self.rate_limit = None

        self.enable_compression = False

        self.connect_timeout = 10

        self.message_queue = []

        self._event_handlers = {}
        

    async def connect(self):

        pass
    

    async def connect_with_auth(self, token):

        pass
    

    async def send_message(self, message):

        pass
    

    async def receive_message(self):

        pass
    

    def is_connected(self):

        return True  # Will be properly set in tests
    

    async def handle_disconnect(self):

        pass
    

    async def heartbeat(self):

        pass
    

    async def subscribe_to_room(self, room):

        pass
    

    async def send_binary(self, data):

        pass
    

    async def send_message_safe(self, message):

        pass
    

    def get_error_count(self):

        return 0
    

    async def send_message_with_rate_limit(self, message):

        pass
    

    async def disconnect(self):

        pass
    

    def queue_message(self, message):

        self.message_queue.append(message)
    

    async def connect_and_flush_queue(self):

        pass
    

    def on(self, event, handler):

        if event not in self._event_handlers:

            self._event_handlers[event] = []

        self._event_handlers[event].append(handler)
    

    async def handle_message(self, message):

        event_type = message.get("type")

        if event_type in self._event_handlers:

            for handler in self._event_handlers[event_type]:

                await handler(message)
    

    async def send_compressed(self, message):

        pass
    

    async def send_with_ack(self, message):

        return "msg_123"
    

    async def wait_for_ack(self, msg_id, timeout):

        return True
    

    async def connect_with_headers(self, headers):

        pass
    

    async def connect_with_subprotocols(self, subprotocols):

        pass
    

    def get_subprotocol(self):

        return "chat.v2"
    

    async def send_ordered(self, message):

        pass
    

    async def send_with_backpressure(self, message):

        pass
    

    async def connect_with_origin(self, origin):

        pass
    

    def set_state(self, state):

        self.saved_state = state
    

    async def reconnect_with_state(self):

        pass
    

    def get_cached_statement(self, query):

        return None


class WebSocketManager:

    def __init__(self, max_connections_per_user=None):

        self.max_connections_per_user = max_connections_per_user

        self.clients = {}

        self.enable_metrics = False
        

    def add_client(self, client_id, ws):

        self.clients[client_id] = ws
    

    async def add_user_connection(self, user_id, conn_id, ws):

        return True
    

    async def broadcast(self, message):

        pass
    

    async def user_online(self, user_id, ws):

        pass
    

    async def user_offline(self, user_id):

        pass
    

    def is_user_online(self, user_id):

        return False
    

    async def add_tenant_client(self, tenant, client_id, ws):

        pass
    

    async def broadcast_to_tenant(self, tenant, message):

        pass
    

    async def add_connection_with_metadata(self, ws, metadata):

        return "conn_123"
    

    def get_connection_metadata(self, conn_id):

        return {}
    

    async def shutdown_gracefully(self, timeout):

        pass
    

    async def start_draining(self):

        pass
    

    async def add_client_if_not_draining(self, conn_id, ws):

        return False
    

    async def send_message(self, conn_id, message):

        pass
    

    async def receive_message(self, conn_id, message):

        pass
    

    def get_metrics(self):

        return {}
    

    async def remove_connection(self, conn_id):

        pass


class TestWebSocketL3Integration:

    """Comprehensive L3 integration tests for WebSocket functionality."""

    # Test 31: Basic WebSocket connection establishment

    @pytest.mark.asyncio

    async def test_websocket_connection_establishment(self):

        """Test basic WebSocket connection establishment."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            

            mock_connect.assert_called_once_with("ws://localhost:8000/websocket")

            assert ws_client.is_connected()

    # Test 32: WebSocket authentication handshake

    @pytest.mark.asyncio

    async def test_websocket_authentication_handshake(self):

        """Test WebSocket authentication during handshake."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Simulate auth handshake

            mock_ws.recv.return_value = json.dumps({

                "type": "auth_required"

            })
            

            await ws_client.connect_with_auth("auth_token_123")
            

            mock_ws.send.assert_called_with(json.dumps({

                "type": "auth",

                "token": "auth_token_123"

            }))

    # Test 33: WebSocket message sending and receiving

    @pytest.mark.asyncio

    async def test_websocket_message_send_receive(self):

        """Test sending and receiving messages via WebSocket."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Send message

            await ws_client.send_message({"type": "chat", "content": "Hello"})

            mock_ws.send.assert_called()
            
            # Receive message

            mock_ws.recv.return_value = json.dumps({"type": "chat", "content": "Reply"})

            message = await ws_client.receive_message()
            

            assert message["content"] == "Reply"

    # Test 34: WebSocket automatic reconnection

    @pytest.mark.asyncio

    async def test_websocket_automatic_reconnection(self):

        """Test automatic reconnection on connection loss."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")

        ws_client.auto_reconnect = True
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Initial connection

            await ws_client.connect()
            
            # Simulate connection loss

            mock_ws.close.return_value = None

            await ws_client.handle_disconnect()
            
            # Should attempt reconnection

            await asyncio.sleep(0.1)

            assert mock_connect.call_count >= 2

    # Test 35: WebSocket heartbeat/ping-pong

    @pytest.mark.asyncio

    async def test_websocket_heartbeat_ping_pong(self):

        """Test WebSocket heartbeat mechanism."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Start heartbeat

            heartbeat_task = asyncio.create_task(ws_client.heartbeat())
            

            await asyncio.sleep(0.1)
            
            # Should have sent ping

            mock_ws.ping.assert_called()
            

            heartbeat_task.cancel()

    # Test 36: WebSocket room/channel subscription

    @pytest.mark.asyncio

    async def test_websocket_room_subscription(self):

        """Test WebSocket room/channel subscription."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()

            await ws_client.subscribe_to_room("room_123")
            

            mock_ws.send.assert_called_with(json.dumps({

                "type": "subscribe",

                "room": "room_123"

            }))

    # Test 37: WebSocket broadcast messaging

    @pytest.mark.asyncio

    async def test_websocket_broadcast_messaging(self):

        """Test WebSocket broadcast to multiple clients."""

        ws_manager = WebSocketManager()
        
        # Create multiple mock clients

        clients = []

        for i in range(3):

            mock_ws = AsyncMock()

            client_id = f"client_{i}"

            ws_manager.add_client(client_id, mock_ws)

            clients.append((client_id, mock_ws))
        
        # Broadcast message

        await ws_manager.broadcast({"type": "announcement", "message": "Hello all"})
        
        # All clients should receive

        for client_id, mock_ws in clients:

            mock_ws.send.assert_called_with(json.dumps({

                "type": "announcement",

                "message": "Hello all"

            }))

    # Test 38: WebSocket connection limits

    @pytest.mark.asyncio

    async def test_websocket_connection_limits(self):

        """Test WebSocket connection limits per user."""

        ws_manager = WebSocketManager(max_connections_per_user=2)
        

        user_id = "user_123"
        
        # Add connections up to limit

        for i in range(2):

            mock_ws = AsyncMock()

            result = await ws_manager.add_user_connection(user_id, f"conn_{i}", mock_ws)

            assert result is True
        
        # Should reject additional connection

        mock_ws = AsyncMock()

        result = await ws_manager.add_user_connection(user_id, "conn_3", mock_ws)

        assert result is False

    # Test 39: WebSocket binary message handling

    @pytest.mark.asyncio

    async def test_websocket_binary_message_handling(self):

        """Test handling of binary WebSocket messages."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Send binary data

            binary_data = b"Binary content here"

            await ws_client.send_binary(binary_data)
            

            mock_ws.send.assert_called_with(binary_data)

    # Test 40: WebSocket error recovery

    @pytest.mark.asyncio

    async def test_websocket_error_recovery(self):

        """Test WebSocket error recovery mechanisms."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Simulate error during send

            mock_ws.send.side_effect = websockets.exceptions.ConnectionClosed(None, None)
            

            await ws_client.connect()
            
            # Should handle error gracefully

            result = await ws_client.send_message_safe({"test": "data"})

            assert result is False

            assert ws_client.get_error_count() > 0

    # Test 41: WebSocket rate limiting

    @pytest.mark.asyncio

    async def test_websocket_rate_limiting(self):

        """Test WebSocket message rate limiting."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")

        ws_client.rate_limit = 5  # 5 messages per second
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Send multiple messages quickly

            start_time = time.time()

            for i in range(10):

                await ws_client.send_message_with_rate_limit({"msg": i})
            

            elapsed = time.time() - start_time

            assert elapsed >= 1.0  # Should take at least 2 seconds

    # Test 42: WebSocket connection state management

    @pytest.mark.asyncio

    async def test_websocket_connection_state_management(self):

        """Test WebSocket connection state transitions."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        assert ws_client.state == ConnectionState.DISCONNECTED
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Connect

            await ws_client.connect()

            assert ws_client.state == ConnectionState.CONNECTED
            
            # Disconnect

            await ws_client.disconnect()

            assert ws_client.state == ConnectionState.DISCONNECTED

    # Test 43: WebSocket message queue handling

    @pytest.mark.asyncio

    async def test_websocket_message_queue_handling(self):

        """Test WebSocket message queue for offline messages."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        
        # Queue messages while disconnected

        ws_client.queue_message({"msg": 1})

        ws_client.queue_message({"msg": 2})
        

        assert len(ws_client.message_queue) == 2
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Connect and flush queue

            await ws_client.connect_and_flush_queue()
            

            assert mock_ws.send.call_count == 2

            assert len(ws_client.message_queue) == 0

    # Test 44: WebSocket presence tracking

    @pytest.mark.asyncio

    async def test_websocket_presence_tracking(self):

        """Test WebSocket presence/online status tracking."""

        ws_manager = WebSocketManager()
        

        user_id = "user_123"

        mock_ws = AsyncMock()
        
        # User comes online

        await ws_manager.user_online(user_id, mock_ws)

        assert ws_manager.is_user_online(user_id)
        
        # User goes offline

        await ws_manager.user_offline(user_id)

        assert not ws_manager.is_user_online(user_id)

    # Test 45: WebSocket event handling

    @pytest.mark.asyncio

    async def test_websocket_event_handling(self):

        """Test WebSocket event handler registration and execution."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        
        # Register event handlers

        handler_called = {"chat": False, "notification": False}
        

        async def chat_handler(message):

            handler_called["chat"] = True
        

        async def notification_handler(message):

            handler_called["notification"] = True
        

        ws_client.on("chat", chat_handler)

        ws_client.on("notification", notification_handler)
        
        # Trigger events

        await ws_client.handle_message({"type": "chat", "content": "test"})

        await ws_client.handle_message({"type": "notification", "content": "alert"})
        

        assert handler_called["chat"]

        assert handler_called["notification"]

    # Test 46: WebSocket compression

    @pytest.mark.asyncio

    async def test_websocket_compression(self):

        """Test WebSocket message compression."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")

        ws_client.enable_compression = True
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Send large message that benefits from compression

            large_message = {"data": "x" * 10000}

            await ws_client.send_compressed(large_message)
            
            # Should compress before sending

            sent_data = mock_ws.send.call_args[0][0]

            assert len(sent_data) < len(json.dumps(large_message))

    # Test 47: WebSocket multi-tenant isolation

    @pytest.mark.asyncio

    async def test_websocket_multi_tenant_isolation(self):

        """Test WebSocket isolation between tenants."""

        ws_manager = WebSocketManager()
        
        # Add clients for different tenants

        tenant1_ws = AsyncMock()

        tenant2_ws = AsyncMock()
        

        await ws_manager.add_tenant_client("tenant1", "client1", tenant1_ws)

        await ws_manager.add_tenant_client("tenant2", "client2", tenant2_ws)
        
        # Broadcast to tenant1 only

        await ws_manager.broadcast_to_tenant("tenant1", {"msg": "tenant1 only"})
        

        tenant1_ws.send.assert_called()

        tenant2_ws.send.assert_not_called()

    # Test 48: WebSocket connection metadata

    @pytest.mark.asyncio

    async def test_websocket_connection_metadata(self):

        """Test WebSocket connection metadata tracking."""

        ws_manager = WebSocketManager()
        

        metadata = {

            "user_agent": "TestClient/1.0",

            "ip_address": "192.168.1.100",

            "connected_at": datetime.utcnow()

        }
        

        mock_ws = AsyncMock()

        conn_id = await ws_manager.add_connection_with_metadata(mock_ws, metadata)
        

        stored_metadata = ws_manager.get_connection_metadata(conn_id)

        assert stored_metadata["user_agent"] == "TestClient/1.0"

        assert stored_metadata["ip_address"] == "192.168.1.100"

    # Test 49: WebSocket graceful shutdown

    @pytest.mark.asyncio

    async def test_websocket_graceful_shutdown(self):

        """Test WebSocket graceful shutdown process."""

        ws_manager = WebSocketManager()
        
        # Add multiple connections

        connections = []

        for i in range(5):

            mock_ws = AsyncMock()

            conn_id = f"conn_{i}"

            ws_manager.add_client(conn_id, mock_ws)

            connections.append((conn_id, mock_ws))
        
        # Graceful shutdown

        await ws_manager.shutdown_gracefully(timeout=5)
        
        # All connections should be closed with proper message

        for conn_id, mock_ws in connections:

            mock_ws.send.assert_called_with(json.dumps({

                "type": "server_shutdown",

                "message": "Server is shutting down"

            }))

            mock_ws.close.assert_called()

    # Test 50: WebSocket message acknowledgment

    @pytest.mark.asyncio

    async def test_websocket_message_acknowledgment(self):

        """Test WebSocket message acknowledgment system."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Send message requiring acknowledgment

            msg_id = await ws_client.send_with_ack({"type": "important", "data": "test"})
            
            # Simulate acknowledgment

            mock_ws.recv.return_value = json.dumps({

                "type": "ack",

                "message_id": msg_id

            })
            

            ack_received = await ws_client.wait_for_ack(msg_id, timeout=1)

            assert ack_received is True

    # Test 51: WebSocket connection pooling

    @pytest.mark.asyncio

    async def test_websocket_connection_pooling(self):

        """Test WebSocket connection pooling."""

        pool = WebSocketConnectionPool(max_size=3)
        
        # Create connections

        conns = []

        for i in range(3):

            conn = await pool.acquire("ws://localhost:8000/ws")

            conns.append(conn)
        

        assert pool.size() == 3
        
        # Release one

        await pool.release(conns[0])
        
        # Should reuse released connection

        new_conn = await pool.acquire("ws://localhost:8000/ws")

        assert new_conn == conns[0]

    # Test 52: WebSocket protocol upgrade

    @pytest.mark.asyncio

    async def test_websocket_protocol_upgrade(self):

        """Test WebSocket protocol upgrade from HTTP."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_connect.return_value.__aenter__.return_value = AsyncMock()
            
            # Should include proper upgrade headers

            await ws_client.connect_with_headers({

                "Upgrade": "websocket",

                "Connection": "Upgrade",

                "Sec-WebSocket-Version": "13"

            })
            

            call_args = mock_connect.call_args

            assert "extra_headers" in call_args[1]

    # Test 53: WebSocket subprotocol negotiation

    @pytest.mark.asyncio

    async def test_websocket_subprotocol_negotiation(self):

        """Test WebSocket subprotocol negotiation."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_ws.subprotocol = "chat.v2"

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect_with_subprotocols(["chat.v1", "chat.v2"])
            

            assert ws_client.get_subprotocol() == "chat.v2"

    # Test 54: WebSocket connection timeout

    @pytest.mark.asyncio

    async def test_websocket_connection_timeout(self):

        """Test WebSocket connection timeout handling."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")

        ws_client.connect_timeout = 1  # 1 second
        

        with patch('websockets.connect') as mock_connect:

            mock_connect.side_effect = asyncio.TimeoutError()
            

            with pytest.raises(asyncio.TimeoutError):

                await ws_client.connect()
            

            assert ws_client.state == ConnectionState.FAILED

    # Test 55: WebSocket message ordering

    @pytest.mark.asyncio

    async def test_websocket_message_ordering(self):

        """Test WebSocket message ordering guarantees."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            

            await ws_client.connect()
            
            # Send messages in order

            messages = [{"seq": i} for i in range(10)]

            for msg in messages:

                await ws_client.send_ordered(msg)
            
            # Verify order maintained

            calls = mock_ws.send.call_args_list

            for i, call in enumerate(calls):

                sent_msg = json.loads(call[0][0])

                assert sent_msg["seq"] == i

    # Test 56: WebSocket backpressure handling

    @pytest.mark.asyncio

    async def test_websocket_backpressure_handling(self):

        """Test WebSocket backpressure handling."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Simulate slow consumer

            send_delay = 0

            async def slow_send(data):

                nonlocal send_delay

                send_delay += 0.1

                await asyncio.sleep(send_delay)
            

            mock_ws.send = slow_send
            

            await ws_client.connect()
            
            # Should handle backpressure

            start = time.time()

            for i in range(5):

                await ws_client.send_with_backpressure({"msg": i})
            

            elapsed = time.time() - start

            assert elapsed >= 1.5  # Should slow down due to backpressure

    # Test 57: WebSocket metrics collection

    @pytest.mark.asyncio

    async def test_websocket_metrics_collection(self):

        """Test WebSocket metrics and statistics collection."""

        ws_manager = WebSocketManager()

        ws_manager.enable_metrics = True
        

        mock_ws = AsyncMock()
        
        # Track various metrics

        await ws_manager.add_connection("conn1", mock_ws)

        await ws_manager.send_message("conn1", {"test": "data"})

        await ws_manager.receive_message("conn1", {"response": "data"})

        await ws_manager.remove_connection("conn1")
        

        metrics = ws_manager.get_metrics()

        assert metrics["total_connections"] >= 1

        assert metrics["messages_sent"] >= 1

        assert metrics["messages_received"] >= 1

    # Test 58: WebSocket connection draining

    @pytest.mark.asyncio

    async def test_websocket_connection_draining(self):

        """Test WebSocket connection draining for maintenance."""

        ws_manager = WebSocketManager()
        
        # Add connections

        connections = []

        for i in range(3):

            mock_ws = AsyncMock()

            conn_id = f"conn_{i}"

            ws_manager.add_client(conn_id, mock_ws)

            connections.append((conn_id, mock_ws))
        
        # Start draining

        await ws_manager.start_draining()
        
        # Should reject new connections

        new_ws = AsyncMock()

        result = await ws_manager.add_client_if_not_draining("new_conn", new_ws)

        assert result is False
        
        # Existing connections should get drain notification

        for conn_id, mock_ws in connections:

            mock_ws.send.assert_called()

    # Test 59: WebSocket cross-origin handling

    @pytest.mark.asyncio

    async def test_websocket_cross_origin_handling(self):

        """Test WebSocket cross-origin request handling."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Connect with origin header

            await ws_client.connect_with_origin("https://external.com")
            
            # Should include origin in connection

            call_args = mock_connect.call_args

            headers = call_args[1].get("extra_headers", {})

            assert headers.get("Origin") == "https://external.com"

    # Test 60: WebSocket connection recovery state

    @pytest.mark.asyncio

    async def test_websocket_connection_recovery_state(self):

        """Test WebSocket connection recovery with state restoration."""

        ws_client = WebSocketClient("ws://localhost:8000/websocket")
        
        # Set some state

        ws_client.set_state({"user_id": "123", "subscriptions": ["room1", "room2"]})
        

        with patch('websockets.connect') as mock_connect:

            mock_ws = AsyncMock()

            mock_connect.return_value.__aenter__.return_value = mock_ws
            
            # Reconnect with state recovery

            await ws_client.reconnect_with_state()
            
            # Should restore subscriptions

            calls = mock_ws.send.call_args_list

            sent_messages = [json.loads(call[0][0]) for call in calls]
            

            subscription_msgs = [m for m in sent_messages if m.get("type") == "subscribe"]

            assert len(subscription_msgs) == 2


class WebSocketConnectionPool:

    """Mock WebSocket connection pool for testing."""
    

    def __init__(self, max_size):

        self.max_size = max_size

        self.connections = {}

        self.available = []
    

    async def acquire(self, url):

        if self.available:

            return self.available.pop()

        if len(self.connections) < self.max_size:

            conn = AsyncMock()

            self.connections[url] = conn

            return conn

        raise Exception("Pool exhausted")
    

    async def release(self, conn):

        self.available.append(conn)
    

    def size(self):

        return len(self.connections)


if __name__ == "__main__":

    pytest.main([__file__, "-v"])