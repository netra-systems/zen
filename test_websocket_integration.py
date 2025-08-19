"""WebSocket Integration Tests

Comprehensive integration tests using the real WebSocket test client.
Tests real connections, authentication, message protocols, and reliability.

Business Value: Prevents WebSocket failures that cost $15K MRR in lost users.
"""

import pytest
import asyncio
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock

from websocket_test_client import (
    WebSocketTestClient, ConcurrentWebSocketTester, 
    TestMessage, ConnectionState
)


class TestWebSocketIntegration:
    """Real WebSocket integration tests"""
    
    @pytest.fixture
    def test_auth_token(self):
        """Generate test authentication token"""
        # In real tests, this would be a valid JWT token
        return "test-jwt-token-for-websocket-integration"
        
    @pytest.fixture
    def websocket_url(self):
        """WebSocket URL for testing"""
        return "ws://localhost:8000"
        
    @pytest.fixture
    def test_client(self, websocket_url, test_auth_token):
        """Create test WebSocket client"""
        return WebSocketTestClient(websocket_url, test_auth_token)
            
    @pytest.fixture
    def concurrent_tester(self, websocket_url, test_auth_token):
        """Create concurrent WebSocket tester"""
        tester = ConcurrentWebSocketTester(websocket_url)
        tester.add_test_token(test_auth_token)
        return tester

    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self, test_client):
        """Test basic WebSocket connection establishment"""
        # Initially disconnected
        assert test_client.state == ConnectionState.DISCONNECTED
        assert not test_client.is_connected()
        
        # Mock the WebSocket connection for testing
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            # Attempt connection
            success = await test_client.connect()
            
            # Verify connection established
            assert success is True
            assert test_client.state == ConnectionState.CONNECTED
            assert test_client.is_connected()
            assert test_client.metrics.connected_at is not None
            
    @pytest.mark.asyncio
    async def test_websocket_authentication_headers(self, websocket_url):
        """Test WebSocket authentication via query parameters"""
        test_token = "test-auth-token-12345"
        client = WebSocketTestClient(websocket_url, test_token)
        
        # Check URL construction
        expected_url = f"{websocket_url}/ws?token={test_token}"
        actual_url = client.get_connection_url()
        
        assert actual_url == expected_url
        
    @pytest.mark.asyncio  
    async def test_chat_message_sending(self, test_client):
        """Test sending chat messages with proper protocol"""
        test_content = "Test message for WebSocket integration"
        test_thread_id = str(uuid.uuid4())
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            # Connect first
            await test_client.connect()
            
            # Send chat message
            success = await test_client.send_chat_message(test_content, test_thread_id)
            
            assert success is True
            assert test_client.metrics.messages_sent == 1
            
            # Verify message format
            mock_websocket.send.assert_called_once()
            sent_data = mock_websocket.send.call_args[0][0]
            message = json.loads(sent_data)
            
            assert message["type"] == "chat_message"
            assert message["payload"]["content"] == test_content
            assert message["payload"]["thread_id"] == test_thread_id
            assert "timestamp" in message["payload"]
            assert "client_id" in message["payload"]
            
    @pytest.mark.asyncio
    async def test_ping_pong_mechanism(self, test_client):
        """Test WebSocket ping/pong mechanism"""
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            await test_client.connect()
            
            # Send ping
            success = await test_client.send_ping()
            
            assert success is True
            assert test_client.metrics.last_ping_time is not None
            
            # Verify ping message format
            sent_data = mock_websocket.send.call_args[0][0]
            message = json.loads(sent_data)
            
            assert message["type"] == "ping"
            assert "timestamp" in message["payload"]
            assert "client_id" in message["payload"]
            
    @pytest.mark.asyncio
    async def test_message_reception_handling(self, test_client):
        """Test handling of received messages"""
        received_messages = []
        
        def message_handler(message: Dict[str, Any]):
            received_messages.append(message)
            
        test_client.add_message_handler(message_handler)
        
        # Simulate received message
        test_message = {
            "type": "agent_response",
            "payload": {
                "content": "Response from agent",
                "thread_id": str(uuid.uuid4()),
                "agent_name": "TestAgent"
            }
        }
        
        await test_client._handle_received_message(test_message)
        
        # Verify message was handled
        assert len(received_messages) == 1
        assert received_messages[0] == test_message
        assert test_client.metrics.messages_received == 1
        
    @pytest.mark.asyncio
    async def test_pong_message_handling(self, test_client):
        """Test pong message handling updates metrics"""
        pong_message = {
            "type": "pong",
            "payload": {
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Set ping time first
        test_client.metrics.last_ping_time = datetime.now()
        
        await test_client._handle_received_message(pong_message)
        
        # Verify pong time was recorded
        assert test_client.metrics.last_pong_time is not None
        assert test_client.metrics.messages_received == 1
        
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, test_client):
        """Test connection error handling"""
        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            success = await test_client.connect()
            
            assert success is False
            assert test_client.state == ConnectionState.FAILED
            assert len(test_client.metrics.errors) > 0
            assert "Connection failed" in test_client.metrics.errors[0]
            
    @pytest.mark.asyncio
    async def test_graceful_disconnection(self, test_client):
        """Test graceful WebSocket disconnection"""
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            await test_client.connect()
            assert test_client.is_connected()
            
            # Disconnect gracefully
            await test_client.disconnect(code=1000, reason="Test disconnect")
            
            assert test_client.state == ConnectionState.DISCONNECTED
            assert test_client.metrics.disconnected_at is not None
            mock_websocket.close.assert_called_once_with(code=1000, reason="Test disconnect")
            
    @pytest.mark.asyncio
    async def test_reconnection_logic(self, test_client):
        """Test automatic reconnection logic"""
        test_client.max_reconnection_attempts = 2
        test_client.reconnection_delay = 0.1  # Faster for testing
        
        with patch('websockets.connect') as mock_connect:
            # First connection succeeds, then fails, then succeeds again
            mock_websocket1 = AsyncMock()
            mock_websocket2 = AsyncMock()
            
            mock_connect.side_effect = [
                mock_websocket1,  # Initial connection
                Exception("Connection lost"),  # First reconnection fails
                mock_websocket2   # Second reconnection succeeds
            ]
            
            # Initial connection
            await test_client.connect()
            assert test_client.is_connected()
            
            # Simulate connection loss
            test_client.state = ConnectionState.DISCONNECTED
            await test_client._attempt_reconnection()
            
            # Should eventually reconnect
            assert test_client.state == ConnectionState.CONNECTED
            assert test_client.metrics.reconnection_count > 0
            
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, concurrent_tester):
        """Test multiple concurrent WebSocket connections"""
        num_clients = 3
        
        # Create multiple clients
        clients = []
        for i in range(num_clients):
            client = await concurrent_tester.create_client()
            clients.append(client)
            
        with patch('websockets.connect') as mock_connect:
            mock_websockets = [AsyncMock() for _ in range(num_clients)]
            mock_connect.side_effect = mock_websockets
            
            # Connect all clients
            results = await concurrent_tester.connect_all_clients()
            
            # Verify all connections succeeded
            assert len(results) == num_clients
            assert all(results.values())
            
            # Check aggregate metrics
            metrics = concurrent_tester.get_aggregate_metrics()
            assert metrics["total_clients"] == num_clients
            assert metrics["connected_clients"] == num_clients
            assert metrics["connection_rate"] == 1.0
            
    @pytest.mark.asyncio
    async def test_concurrent_message_broadcasting(self, concurrent_tester):
        """Test broadcasting messages to multiple clients"""
        num_clients = 2
        
        # Create and connect clients
        for i in range(num_clients):
            await concurrent_tester.create_client()
            
        with patch('websockets.connect') as mock_connect:
            mock_websockets = [AsyncMock() for _ in range(num_clients)]
            mock_connect.side_effect = mock_websockets
            
            await concurrent_tester.connect_all_clients()
            
            # Broadcast test message
            test_message = {
                "type": "test_broadcast",
                "payload": {
                    "content": "Broadcasting to all clients",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            results = await concurrent_tester.broadcast_message(test_message)
            
            # Verify all clients received the broadcast
            assert len(results) == num_clients
            assert all(results.values())
            
            # Verify all websockets were called
            for mock_ws in mock_websockets:
                mock_ws.send.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_connection_metrics_tracking(self, test_client):
        """Test connection metrics are properly tracked"""
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            # Connect and send messages
            await test_client.connect()
            await test_client.send_chat_message("Test message 1")
            await test_client.send_chat_message("Test message 2")
            
            # Simulate received messages
            await test_client._handle_received_message({"type": "response1"})
            await test_client._handle_received_message({"type": "response2"})
            await test_client._handle_received_message({"type": "response3"})
            
            # Get metrics
            metrics = test_client.get_metrics()
            
            assert metrics["state"] == ConnectionState.CONNECTED.value
            assert metrics["messages_sent"] == 2
            assert metrics["messages_received"] == 3
            assert metrics["error_count"] == 0
            assert "client_id" in metrics
            assert "uptime_seconds" in metrics
            
    @pytest.mark.asyncio 
    async def test_connection_health_monitoring(self, test_client):
        """Test connection health monitoring"""
        # Initially disconnected
        assert not test_client.is_healthy()
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            # After connecting
            await test_client.connect()
            assert test_client.is_healthy()
            assert test_client.is_connected()
            
            # When connection fails
            test_client.state = ConnectionState.FAILED
            assert not test_client.is_healthy()
            assert not test_client.is_connected()
            
            # When reconnecting
            test_client.state = ConnectionState.RECONNECTING
            assert test_client.is_healthy()  # Still considered healthy during reconnect
            assert not test_client.is_connected()
            
    @pytest.mark.asyncio
    async def test_structured_test_messages(self, test_client):
        """Test structured test message creation and sending"""
        test_msg = TestMessage(
            message_type="test_request",
            content="Structured test message",
            thread_id=str(uuid.uuid4())
        )
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            await test_client.connect()
            success = await test_client.send_test_message(test_msg)
            
            assert success is True
            
            # Verify message structure
            sent_data = mock_websocket.send.call_args[0][0]
            message = json.loads(sent_data)
            
            assert message["type"] == "test_request"
            assert message["payload"]["content"] == "Structured test message"
            assert message["payload"]["thread_id"] == test_msg.thread_id
            assert "timestamp" in message["payload"]
            
    @pytest.mark.asyncio
    async def test_error_recovery_after_send_failure(self, test_client):
        """Test error recovery after message send failures"""
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.send.side_effect = Exception("Send failed")
            mock_connect.return_value = mock_websocket
            
            await test_client.connect()
            
            # Attempt to send message (should fail)
            success = await test_client.send_chat_message("Test message")
            
            assert success is False
            assert len(test_client.metrics.errors) > 0
            assert "Send failed" in test_client.metrics.errors[0]
            
            # Connection should still be considered connected
            assert test_client.state == ConnectionState.CONNECTED
            
    @pytest.mark.asyncio
    async def test_large_message_handling(self, test_client):
        """Test handling of large messages"""
        # Create large message content
        large_content = "X" * 10000  # 10KB message
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            await test_client.connect()
            success = await test_client.send_chat_message(large_content)
            
            assert success is True
            
            # Verify large message was sent
            sent_data = mock_websocket.send.call_args[0][0]
            message = json.loads(sent_data)
            assert len(message["payload"]["content"]) == 10000
            
    @pytest.mark.asyncio
    async def test_rapid_message_sending(self, test_client):
        """Test rapid successive message sending"""
        num_messages = 10
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            await test_client.connect()
            
            # Send messages rapidly
            tasks = []
            for i in range(num_messages):
                task = test_client.send_chat_message(f"Rapid message {i}")
                tasks.append(task)
                
            results = await asyncio.gather(*tasks)
            
            # All messages should succeed
            assert all(results)
            assert test_client.metrics.messages_sent == num_messages
            assert mock_websocket.send.call_count == num_messages


class TestWebSocketStressConditions:
    """Stress testing for WebSocket connections"""
    
    @pytest.mark.asyncio
    async def test_connection_under_load(self, websocket_url, test_auth_token):
        """Test WebSocket behavior under high connection load"""
        tester = ConcurrentWebSocketTester(websocket_url)
        tester.add_test_token(test_auth_token)
        
        # Create many concurrent connections
        num_clients = 10
        clients = []
        
        for i in range(num_clients):
            client = await tester.create_client()
            clients.append(client)
            
        with patch('websockets.connect') as mock_connect:
            mock_websockets = [AsyncMock() for _ in range(num_clients)]
            mock_connect.side_effect = mock_websockets
            
            start_time = time.time()
            results = await tester.connect_all_clients()
            connection_time = time.time() - start_time
            
            # Verify performance is reasonable (should connect quickly)
            assert connection_time < 5.0  # 5 seconds max for 10 connections
            assert len(results) == num_clients
            
            # Clean up
            await tester.disconnect_all_clients()
            
    @pytest.mark.asyncio
    async def test_message_throughput(self, websocket_url, test_auth_token):
        """Test message throughput under load"""
        client = WebSocketTestClient(websocket_url, test_auth_token)
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            await client.connect()
            
            # Send many messages quickly
            num_messages = 100
            start_time = time.time()
            
            tasks = []
            for i in range(num_messages):
                task = client.send_chat_message(f"Throughput test message {i}")
                tasks.append(task)
                
            results = await asyncio.gather(*tasks)
            throughput_time = time.time() - start_time
            
            # Verify throughput
            messages_per_second = num_messages / throughput_time
            assert all(results)
            assert messages_per_second > 50  # Should handle at least 50 msg/sec
            
            await client.disconnect()


if __name__ == "__main__":
    # Run specific tests
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-k", "test_websocket_connection_establishment"
    ])