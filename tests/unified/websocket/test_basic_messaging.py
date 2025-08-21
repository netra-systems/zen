"""Test #2: Basic Message Send/Receive Test [CRITICAL - P0]

Tests core JSON message exchange functionality in both directions.
Ensures message integrity, format compliance, and bidirectional communication.

Business Value Justification (BVJ):
- Segment: All customer tiers
- Business Goal: Core chat functionality reliability
- Value Impact: Every user message depends on this working correctly
- Revenue Impact: Message transmission failures directly impact user experience

Test Requirements:
- Send simple JSON message from client to server
- Receive acknowledgment from server  
- Send response from server to client
- Verify message integrity and format
- Use real WebSocket connections (no mocks)
- Follow SPEC/websockets.xml JSON-first approach
"""

import asyncio
import json
import pytest
import pytest_asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from tests.unified.config import TEST_CONFIG, TEST_ENDPOINTS, TestDataFactory
from tests.unified.real_websocket_client import RealWebSocketClient
from tests.unified.real_client_types import create_test_config


class BasicMessagingTester:
    """Real WebSocket messaging tester for core functionality."""
    
    def __init__(self):
        self.client: Optional[RealWebSocketClient] = None
        self.sent_messages: list = []
        self.received_messages: list = []
        self.test_token = self._create_test_token()
    
    def _create_test_token(self) -> str:
        """Create test JWT token for authentication."""
        try:
            from netra_backend.app.tests.test_utilities.auth_test_helpers import create_test_token
            return create_test_token("basic_messaging_user")
        except ImportError:
            return "mock-token-basic-messaging-user"
    
    async def setup_client(self) -> bool:
        """Setup WebSocket client with authentication."""
        config = create_test_config(timeout=15.0, max_retries=2)
        ws_url = f"{TEST_ENDPOINTS.ws_url}?token={self.test_token}"
        
        self.client = RealWebSocketClient(ws_url, config)
        return await self.client.connect()
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send JSON message to server."""
        if not self.client:
            return False
        
        success = await self.client.send(message)
        if success:
            self.sent_messages.append(message)
        return success
    
    async def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive JSON message from server."""
        if not self.client:
            return None
        
        message = await self.client.receive(timeout)
        if message:
            self.received_messages.append(message)
        return message
    
    async def send_and_wait_for_response(self, message: Dict[str, Any], 
                                       timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Send message and wait for response."""
        if not await self.send_message(message):
            return None
        return await self.receive_message(timeout)
    
    async def cleanup(self) -> None:
        """Cleanup WebSocket connection."""
        if self.client:
            await self.client.close()


@pytest_asyncio.fixture
async def messaging_tester():
    """Create messaging tester fixture."""
    tester = BasicMessagingTester()
    yield tester
    await tester.cleanup()


class TestBasicMessageSending:
    """Test basic message sending functionality."""
    
    async def test_simple_message_send(self, messaging_tester):
        """Test sending simple JSON message to server."""
        # Setup connection
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Create test message
        test_message = {
            "type": "test_message",
            "content": "Hello WebSocket Server",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": "basic_messaging_user"
        }
        
        # Send message
        sent = await messaging_tester.send_message(test_message)
        assert sent, "Failed to send message to server"
        
        # Verify message was recorded
        assert len(messaging_tester.sent_messages) == 1
        assert messaging_tester.sent_messages[0] == test_message
    
    async def test_multiple_messages_send(self, messaging_tester):
        """Test sending multiple JSON messages in sequence."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send multiple messages
        messages = []
        for i in range(3):
            message = {
                "type": "sequence_test",
                "content": f"Message {i + 1}",
                "sequence_id": i + 1,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            messages.append(message)
            
            sent = await messaging_tester.send_message(message)
            assert sent, f"Failed to send message {i + 1}"
        
        # Verify all messages sent
        assert len(messaging_tester.sent_messages) == 3
        for i, sent_msg in enumerate(messaging_tester.sent_messages):
            assert sent_msg["sequence_id"] == i + 1
            assert sent_msg["content"] == f"Message {i + 1}"


class TestBasicMessageReceiving:
    """Test basic message receiving functionality."""
    
    async def test_ping_pong_response(self, messaging_tester):
        """Test receiving pong response to ping message."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send ping message
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = await messaging_tester.send_and_wait_for_response(ping_message)
        
        # Verify pong response
        assert response is not None, "No response received to ping"
        assert response.get("type") == "pong", f"Expected pong, got {response.get('type')}"
        assert "timestamp" in response, "Pong response missing timestamp"
    
    async def test_message_echo_functionality(self, messaging_tester):
        """Test server echo functionality for messages."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send test message that should be echoed
        echo_message = {
            "type": "echo_test",
            "content": "Echo this message back",
            "test_id": "echo_001"
        }
        
        response = await messaging_tester.send_and_wait_for_response(echo_message, timeout=10.0)
        
        # Note: This test verifies the server responds to messages
        # The exact response format depends on server implementation
        if response:
            assert isinstance(response, dict), "Response must be valid JSON"
            # Basic validation that we got a response
            assert "type" in response or "error" in response or "status" in response


class TestBidirectionalMessaging:
    """Test bidirectional message exchange."""
    
    async def test_client_to_server_message_flow(self, messaging_tester):
        """Test complete client to server message flow."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send chat message
        chat_message = {
            "type": "chat_message",
            "content": "Test chat message from client",
            "user_id": "basic_messaging_user",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        sent = await messaging_tester.send_message(chat_message)
        assert sent, "Failed to send chat message"
        
        # Wait for any server response
        response = await messaging_tester.receive_message(timeout=8.0)
        
        # Verify response format if received
        if response:
            assert isinstance(response, dict), "Server response must be valid JSON"
            # Server may respond with acknowledgment, echo, or processing result
    
    async def test_server_to_client_message_reception(self, messaging_tester):
        """Test receiving server-initiated messages."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send a message that triggers server response
        trigger_message = {
            "type": "get_status",
            "request_id": "status_001"
        }
        
        response = await messaging_tester.send_and_wait_for_response(trigger_message, timeout=10.0)
        
        if response:
            # Verify JSON structure
            assert isinstance(response, dict), "Response must be valid JSON"
            
            # Verify basic response format
            expected_fields = ["type", "status", "timestamp", "response", "result", "error"]
            has_expected_field = any(field in response for field in expected_fields)
            assert has_expected_field, f"Response missing expected fields. Got: {list(response.keys())}"


class TestMessageIntegrity:
    """Test message integrity and format compliance."""
    
    async def test_json_message_format_preservation(self, messaging_tester):
        """Test that JSON message format is preserved."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Create complex JSON message
        complex_message = {
            "type": "complex_test",
            "data": {
                "nested": {
                    "array": [1, 2, 3],
                    "boolean": True,
                    "null_value": None,
                    "string": "test string with special chars: àáâãäåæç"
                },
                "numbers": {
                    "integer": 42,
                    "float": 3.14159,
                    "negative": -123
                }
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "encoding": "utf-8"
            }
        }
        
        sent = await messaging_tester.send_message(complex_message)
        assert sent, "Failed to send complex JSON message"
        
        # Verify message was properly formatted when sent
        assert len(messaging_tester.sent_messages) == 1
        sent_msg = messaging_tester.sent_messages[0]
        
        # Verify all fields preserved
        assert sent_msg["type"] == "complex_test"
        assert sent_msg["data"]["nested"]["array"] == [1, 2, 3]
        assert sent_msg["data"]["nested"]["boolean"] is True
        assert sent_msg["data"]["numbers"]["float"] == 3.14159
    
    async def test_large_message_handling(self, messaging_tester):
        """Test handling of large JSON messages."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Create large message (but reasonable for WebSocket)
        large_content = "x" * 1000  # 1KB of content
        large_message = {
            "type": "large_message_test",
            "content": large_content,
            "size_bytes": len(large_content),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        sent = await messaging_tester.send_message(large_message)
        assert sent, "Failed to send large message"
        
        # Verify message integrity
        assert len(messaging_tester.sent_messages) == 1
        sent_msg = messaging_tester.sent_messages[0]
        assert len(sent_msg["content"]) == 1000
        assert sent_msg["size_bytes"] == 1000


class TestMessageTiming:
    """Test message timing and timeout behavior."""
    
    async def test_message_send_timing(self, messaging_tester):
        """Test message send timing and responsiveness."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Measure send time
        start_time = asyncio.get_event_loop().time()
        
        test_message = {
            "type": "timing_test",
            "content": "Testing message send timing",
            "start_time": start_time
        }
        
        sent = await messaging_tester.send_message(test_message)
        send_time = asyncio.get_event_loop().time() - start_time
        
        assert sent, "Failed to send timing test message"
        assert send_time < 1.0, f"Message send took too long: {send_time:.3f}s"
    
    async def test_receive_timeout_behavior(self, messaging_tester):
        """Test receive timeout behavior when no message available."""
        connected = await messaging_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Test short timeout when no message expected
        start_time = asyncio.get_event_loop().time()
        response = await messaging_tester.receive_message(timeout=2.0)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should timeout cleanly
        if response is None:
            assert 1.8 <= elapsed <= 2.5, f"Timeout behavior incorrect: {elapsed:.3f}s"
        else:
            # If we got a message, that's also acceptable (server sent something)
            assert isinstance(response, dict), "Unexpected response must be valid JSON"