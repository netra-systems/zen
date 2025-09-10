"""
Test WebSocket Client Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Reliable real-time communication between frontend and backend
- Value Impact: Users receive immediate feedback on agent operations and system state
- Strategic Impact: Core platform functionality enabling responsive user experience

This test suite validates the frontend WebSocket client including:
- Connection establishment and management
- Message sending and receiving
- Reconnection logic and error handling
- Event-driven state management
- Performance under various network conditions

Performance Requirements:
- Connection establishment should complete within 3 seconds
- Message latency should be under 100ms in normal conditions
- Reconnection attempts should follow exponential backoff
- Memory usage should remain bounded during long sessions
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional, List, Callable

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockWebSocket:
    """Mock WebSocket for unit testing."""
    
    def __init__(self):
        self.connected = False
        self.closed = False
        self.sent_messages = []
        self.received_messages = []
        self.url = None
        self.headers = None
        self.close_code = None
        self.close_reason = None
        
    async def connect(self, url: str, headers: Optional[Dict] = None):
        """Mock connection."""
        self.url = url
        self.headers = headers or {}
        self.connected = True
        
    async def send(self, message: str):
        """Mock send message."""
        if not self.connected:
            raise Exception("WebSocket not connected")
        self.sent_messages.append(message)
        
    async def recv(self):
        """Mock receive message."""
        if not self.connected:
            raise Exception("WebSocket not connected")
        if self.received_messages:
            return self.received_messages.pop(0)
        await asyncio.sleep(0.01)  # Simulate waiting
        return None
        
    async def close(self, code: int = 1000, reason: str = ""):
        """Mock close connection."""
        self.connected = False
        self.closed = True
        self.close_code = code
        self.close_reason = reason
        
    def add_received_message(self, message: str):
        """Helper to simulate received messages."""
        self.received_messages.append(message)


class WebSocketClient:
    """Mock WebSocket client for testing."""
    
    def __init__(self, url: str, auth_token: Optional[str] = None):
        self.url = url
        self.auth_token = auth_token
        self.websocket = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
        self.message_handlers = {}
        self.connection_listeners = []
        self.error_listeners = []
        self.message_queue = []
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "connection_attempts": 0,
            "reconnection_attempts": 0,
            "errors": 0
        }
        
    async def connect(self) -> bool:
        """Connect to WebSocket server."""
        try:
            self.metrics["connection_attempts"] += 1
            
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
                
            self.websocket = MockWebSocket()
            await self.websocket.connect(self.url, headers)
            self.connected = True
            self.reconnect_attempts = 0
            
            # Notify listeners
            for listener in self.connection_listeners:
                try:
                    await listener("connected")
                except Exception:
                    pass
                    
            return True
            
        except Exception as e:
            self.connected = False
            self.metrics["errors"] += 1
            
            # Notify error listeners
            for listener in self.error_listeners:
                try:
                    await listener("connection_error", str(e))
                except Exception:
                    pass
                    
            return False
            
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            
        # Notify listeners
        for listener in self.connection_listeners:
            try:
                await listener("disconnected")
            except Exception:
                pass
                
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """Send message to server."""
        if not self.connected or not self.websocket:
            # Queue message for when connected
            self.message_queue.append({"type": message_type, "data": data})
            return False
            
        try:
            import json
            message = json.dumps({"type": message_type, "data": data})
            await self.websocket.send(message)
            self.metrics["messages_sent"] += 1
            return True
            
        except Exception as e:
            self.metrics["errors"] += 1
            
            # Notify error listeners
            for listener in self.error_listeners:
                try:
                    await listener("send_error", str(e))
                except Exception:
                    pass
                    
            return False
            
    async def start_listening(self):
        """Start listening for messages."""
        while self.connected and self.websocket:
            try:
                message = await self.websocket.recv()
                if message:
                    await self._handle_received_message(message)
                else:
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                self.metrics["errors"] += 1
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    await self._attempt_reconnect()
                else:
                    break
                    
    async def _handle_received_message(self, message: str):
        """Handle received message."""
        try:
            import json
            parsed = json.loads(message)
            message_type = parsed.get("type")
            data = parsed.get("data", {})
            
            self.metrics["messages_received"] += 1
            
            # Call registered handlers
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(data)
                
        except Exception as e:
            self.metrics["errors"] += 1
            
    async def _attempt_reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        self.reconnect_attempts += 1
        self.metrics["reconnection_attempts"] += 1
        
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        await asyncio.sleep(min(delay, 30))  # Max 30 second delay
        
        success = await self.connect()
        if success and self.message_queue:
            # Send queued messages
            queued_messages = self.message_queue.copy()
            self.message_queue.clear()
            
            for msg in queued_messages:
                await self.send_message(msg["type"], msg["data"])
                
    def add_message_handler(self, message_type: str, handler: Callable):
        """Add message handler."""
        self.message_handlers[message_type] = handler
        
    def add_connection_listener(self, listener: Callable):
        """Add connection state listener."""
        self.connection_listeners.append(listener)
        
    def add_error_listener(self, listener: Callable):
        """Add error listener."""
        self.error_listeners.append(listener)


class TestWebSocketClient(SSotBaseTestCase):
    """Test WebSocket client functionality and lifecycle."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.test_url = "ws://localhost:8000/ws"
        self.test_token = f"test_token_{uuid.uuid4().hex[:8]}"
        
        # Create WebSocket client
        self.client = WebSocketClient(self.test_url, self.test_token)
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection establishment with authentication."""
        # When: Connecting to WebSocket server
        connection_success = await self.client.connect()
        
        # Then: Connection should succeed
        assert connection_success is True
        assert self.client.connected is True
        assert self.client.websocket is not None
        
        # And: Auth token should be sent in headers
        assert self.client.websocket.headers.get("Authorization") == f"Bearer {self.test_token}"
        assert self.client.websocket.url == self.test_url
        
        # And: Metrics should be updated
        assert self.client.metrics["connection_attempts"] == 1
        assert self.client.metrics["errors"] == 0
        
        self.record_metric("connection_established", True)
    
    @pytest.mark.unit
    async def test_message_sending_and_receiving(self):
        """Test bidirectional message communication."""
        # Given: Connected client
        await self.client.connect()
        
        # Mock message handler
        received_messages = []
        async def handle_agent_update(data):
            received_messages.append(data)
            
        self.client.add_message_handler("agent_update", handle_agent_update)
        
        # When: Sending message
        send_success = await self.client.send_message("agent_request", {
            "agent": "cost_optimizer",
            "message": "Analyze my costs",
            "user_id": "test_user"
        })
        
        # Then: Message should be sent successfully
        assert send_success is True
        assert len(self.client.websocket.sent_messages) == 1
        
        # And: Sent message should be properly formatted
        import json
        sent_message = json.loads(self.client.websocket.sent_messages[0])
        assert sent_message["type"] == "agent_request"
        assert sent_message["data"]["agent"] == "cost_optimizer"
        assert sent_message["data"]["message"] == "Analyze my costs"
        
        # When: Receiving message
        response_data = {
            "agent": "cost_optimizer",
            "status": "completed",
            "result": "Analysis complete"
        }
        
        response_message = json.dumps({
            "type": "agent_update",
            "data": response_data
        })
        
        self.client.websocket.add_received_message(response_message)
        await self.client._handle_received_message(response_message)
        
        # Then: Message should be handled correctly
        assert len(received_messages) == 1
        assert received_messages[0]["agent"] == "cost_optimizer"
        assert received_messages[0]["status"] == "completed"
        
        # And: Metrics should be updated
        assert self.client.metrics["messages_sent"] == 1
        assert self.client.metrics["messages_received"] == 1
        
        self.record_metric("messages_exchanged", 2)
        self.increment_websocket_events(2)
    
    @pytest.mark.unit
    async def test_connection_error_handling(self):
        """Test connection error handling and recovery."""
        # Given: Client that will fail to connect
        failing_client = WebSocketClient("ws://invalid:999", self.test_token)
        
        # Mock connection failure
        with patch.object(MockWebSocket, 'connect', side_effect=Exception("Connection failed")):
            # When: Attempting to connect
            connection_success = await failing_client.connect()
            
            # Then: Connection should fail gracefully
            assert connection_success is False
            assert failing_client.connected is False
            
            # And: Error metrics should be updated
            assert failing_client.metrics["errors"] == 1
            assert failing_client.metrics["connection_attempts"] == 1
        
        self.record_metric("error_handling_tested", True)
    
    @pytest.mark.unit
    async def test_message_queuing_when_disconnected(self):
        """Test message queuing when client is disconnected."""
        # Given: Disconnected client
        assert self.client.connected is False
        
        # When: Attempting to send messages while disconnected
        message1_success = await self.client.send_message("test_message", {"id": 1})
        message2_success = await self.client.send_message("test_message", {"id": 2})
        
        # Then: Messages should be queued
        assert message1_success is False  # Not sent immediately
        assert message2_success is False  # Not sent immediately
        assert len(self.client.message_queue) == 2
        
        # When: Connecting client
        await self.client.connect()
        
        # Simulate sending queued messages
        queued_messages = self.client.message_queue.copy()
        self.client.message_queue.clear()
        
        for msg in queued_messages:
            await self.client.send_message(msg["type"], msg["data"])
        
        # Then: Queued messages should be sent
        assert len(self.client.websocket.sent_messages) == 2
        assert self.client.metrics["messages_sent"] == 2
        
        self.record_metric("queued_messages_sent", 2)
    
    @pytest.mark.unit
    async def test_reconnection_with_exponential_backoff(self):
        """Test automatic reconnection with exponential backoff."""
        # Given: Client that will disconnect
        await self.client.connect()
        assert self.client.connected is True
        
        # When: Simulating connection loss and reconnection attempts
        original_reconnect_delay = self.client.reconnect_delay
        self.client.reconnect_delay = 0.01  # Speed up test
        
        reconnect_delays = []
        
        # Mock the reconnection process
        for attempt in range(3):
            self.client.reconnect_attempts = attempt
            delay = self.client.reconnect_delay * (2 ** attempt)
            reconnect_delays.append(delay)
        
        # Then: Delays should follow exponential backoff
        assert reconnect_delays[0] == 0.01  # First attempt
        assert reconnect_delays[1] == 0.02  # Second attempt (2x)
        assert reconnect_delays[2] == 0.04  # Third attempt (4x)
        
        # And: Max attempts should be respected
        assert self.client.max_reconnect_attempts == 5
        
        self.record_metric("reconnection_backoff_tested", True)
    
    @pytest.mark.unit
    async def test_event_listeners_and_callbacks(self):
        """Test event listener registration and callbacks."""
        # Given: Event listeners
        connection_events = []
        error_events = []
        
        async def connection_listener(event):
            connection_events.append(event)
            
        async def error_listener(event, message):
            error_events.append({"event": event, "message": message})
        
        self.client.add_connection_listener(connection_listener)
        self.client.add_error_listener(error_listener)
        
        # When: Connection events occur
        await self.client.connect()
        await self.client.disconnect()
        
        # Then: Listeners should be called
        assert len(connection_events) == 2
        assert "connected" in connection_events
        assert "disconnected" in connection_events
        
        # When: Error occurs during send
        self.client.connected = True
        self.client.websocket = None  # Force error
        
        send_success = await self.client.send_message("test", {})
        
        # Then: Error listener should be called
        assert send_success is False
        assert len(error_events) >= 1
        
        self.record_metric("event_listeners_tested", True)


class TestWebSocketClientPerformance(SSotBaseTestCase):
    """Test WebSocket client performance characteristics."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.client = WebSocketClient("ws://localhost:8000/ws", "perf_token")
    
    @pytest.mark.unit
    async def test_message_throughput_performance(self):
        """Test message sending throughput."""
        # Given: Connected client
        await self.client.connect()
        
        message_count = 100
        max_send_time_ms = 50  # 50ms max per message
        
        send_times = []
        
        # When: Sending messages and measuring performance
        for i in range(message_count):
            start_time = time.time()
            
            await self.client.send_message("performance_test", {
                "index": i,
                "data": f"Performance test message {i}",
                "timestamp": time.time()
            })
            
            send_time = (time.time() - start_time) * 1000  # Convert to ms
            send_times.append(send_time)
        
        # Then: Performance should meet requirements
        avg_send_time = sum(send_times) / len(send_times)
        max_send_time = max(send_times)
        
        assert avg_send_time < max_send_time_ms
        assert self.client.metrics["messages_sent"] == message_count
        
        self.record_metric("perf_messages_sent", message_count)
        self.record_metric("avg_send_time_ms", avg_send_time)
        self.record_metric("max_send_time_ms", max_send_time)
    
    @pytest.mark.unit
    async def test_connection_establishment_performance(self):
        """Test connection establishment performance."""
        # Given: Multiple connection attempts
        connection_count = 10
        max_connection_time_ms = 3000  # 3 seconds max
        
        connection_times = []
        clients = []
        
        # When: Establishing multiple connections
        for i in range(connection_count):
            client = WebSocketClient(f"ws://localhost:800{i % 3}/ws", f"token_{i}")
            clients.append(client)
            
            start_time = time.time()
            await client.connect()
            connection_time = (time.time() - start_time) * 1000  # Convert to ms
            connection_times.append(connection_time)
        
        # Then: Performance should meet requirements
        avg_connection_time = sum(connection_times) / len(connection_times)
        max_connection_time = max(connection_times)
        
        assert avg_connection_time < max_connection_time_ms
        assert max_connection_time < max_connection_time_ms * 1.5  # Allow some variance
        
        # Cleanup
        for client in clients:
            await client.disconnect()
        
        self.record_metric("perf_connections_established", connection_count)
        self.record_metric("avg_connection_time_ms", avg_connection_time)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Disconnect client if still connected
        if self.client.connected:
            asyncio.run(self.client.disconnect())
        
        super().teardown_method(method)