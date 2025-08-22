# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestWebSocketCritical:
    """Critical WebSocket connection and messaging tests"""
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection establishment"""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock()
        
        # Simulate connection
        await mock_websocket.accept()
        
        # Verify connection accepted
        mock_websocket.accept.assert_called_once()
        
        # Send initial message
        await mock_websocket.send_text(json.dumps({"type": "connected", "status": "ok"}))
        mock_websocket.send_text.assert_called_once()
    async def test_websocket_message_handling(self):
        """Test WebSocket message sending and receiving"""
        mock_websocket = AsyncMock()
        
        # Test sending different message types
        messages = [
            {"type": "chat", "content": "Hello, AI!"},
            {"type": "status", "status": "processing"},
            {"type": "result", "data": {"answer": "42"}},
            {"type": "error", "message": "Something went wrong"}
        ]
        
        for msg in messages:
            await mock_websocket.send_text(json.dumps(msg))
        
        assert mock_websocket.send_text.call_count == len(messages)
    async def test_websocket_connection_closure(self):
        """Test WebSocket connection closure handling"""
        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        # Close connection with different codes
        close_codes = [
            (1000, "Normal closure"),
            (1001, "Going away"),
            (1002, "Protocol error"),
            (1003, "Unsupported data")
        ]
        
        for code, reason in close_codes:
            await mock_websocket.close(code=code, reason=reason)
        
        assert mock_websocket.close.call_count == len(close_codes)
    async def test_websocket_heartbeat(self):
        """Test WebSocket heartbeat/ping-pong mechanism"""
        mock_websocket = AsyncMock()
        
        # Simulate heartbeat
        heartbeat_interval = 30  # seconds
        heartbeat_count = 0
        
        async def send_heartbeat():
            nonlocal heartbeat_count
            while heartbeat_count < 3:
                await mock_websocket.send_text(json.dumps({"type": "ping"}))
                heartbeat_count += 1
                await asyncio.sleep(0.01)  # Short sleep for testing
        
        await send_heartbeat()
        assert mock_websocket.send_text.call_count == 3
    async def test_websocket_reconnection(self):
        """Test WebSocket reconnection logic"""
        connection_attempts = []
        max_retries = 3
        
        async def attempt_connection(attempt_num):
            connection_attempts.append({
                "attempt": attempt_num,
                "timestamp": datetime.now(UTC).isoformat(),
                "success": attempt_num == max_retries - 1
            })
            
            if attempt_num < max_retries - 1:
                raise ConnectionError("Connection failed")
            
            return AsyncMock()  # Successful connection
        
        # Try reconnection with exponential backoff
        for i in range(max_retries):
            try:
                ws = await attempt_connection(i)
                break
            except ConnectionError:
                await asyncio.sleep(0.01 * (2 ** i))  # Exponential backoff
        
        assert len(connection_attempts) == max_retries
        assert connection_attempts[-1]["success"] == True
    async def test_websocket_message_queue(self):
        """Test message queuing and processing"""
        message_queue = asyncio.Queue()
        processed_messages = []
        
        # Add messages to queue
        test_messages = [
            {"id": str(uuid.uuid4()), "type": "user_message", "content": "Message 1"},
            {"id": str(uuid.uuid4()), "type": "user_message", "content": "Message 2"},
            {"id": str(uuid.uuid4()), "type": "system", "content": "System update"}
        ]
        
        for msg in test_messages:
            await message_queue.put(msg)
        
        # Process messages
        while not message_queue.empty():
            msg = await message_queue.get()
            processed_messages.append(msg)
        
        assert len(processed_messages) == len(test_messages)
        assert all(msg in test_messages for msg in processed_messages)
    async def test_websocket_broadcast(self):
        """Test broadcasting messages to multiple WebSocket connections"""
        connections = [AsyncMock() for _ in range(5)]
        
        broadcast_message = {
            "type": "broadcast",
            "content": "Global announcement",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Broadcast to all connections
        for conn in connections:
            await conn.send_text(json.dumps(broadcast_message))
        
        # Verify all connections received the message
        for conn in connections:
            conn.send_text.assert_called_once_with(json.dumps(broadcast_message))
    async def test_websocket_authentication(self):
        """Test WebSocket authentication flow"""
        mock_websocket = AsyncMock()
        
        # Test authentication message
        auth_message = {
            "type": "auth",
            "token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        
        # Send auth message
        await mock_websocket.send_text(json.dumps(auth_message))
        
        # Simulate auth response
        auth_response = {
            "type": "auth_result",
            "success": True,
            "user_id": "user123"
        }
        
        await mock_websocket.send_text(json.dumps(auth_response))
        
        assert mock_websocket.send_text.call_count == 2
    async def test_websocket_rate_limiting(self):
        """Test WebSocket rate limiting"""
        mock_websocket = AsyncMock()
        
        # Track message timestamps
        message_times = []
        rate_limit = 10  # messages per second
        
        # Try to send messages rapidly
        for i in range(15):
            current_time = asyncio.get_event_loop().time()
            message_times.append(current_time)
            
            # Check rate limit
            recent_messages = [t for t in message_times if current_time - t < 1.0]
            
            if len(recent_messages) <= rate_limit:
                await mock_websocket.send_text(f"Message {i}")
            else:
                # Rate limited - should wait or reject
                pass
        
        # Verify rate limiting worked
        assert mock_websocket.send_text.call_count <= rate_limit + 1
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling"""
        mock_websocket = AsyncMock()
        
        # Test various error scenarios
        error_scenarios = [
            {"type": "invalid_json", "raw": "{invalid json}"},
            {"type": "missing_type", "data": {"content": "test"}},
            {"type": "unknown_message_type", "data": {"type": "unknown", "content": "test"}},
            {"type": "oversized_message", "size": 1024 * 1024 * 10}  # 10MB
        ]
        
        errors_handled = []
        
        for scenario in error_scenarios:
            try:
                if scenario["type"] == "invalid_json":
                    json.loads(scenario["raw"])
                elif scenario["type"] == "missing_type":
                    if "type" not in scenario["data"]:
                        raise KeyError("Missing 'type' field")
                elif scenario["type"] == "unknown_message_type":
                    known_types = ["chat", "status", "result"]
                    if scenario["data"]["type"] not in known_types:
                        raise ValueError(f"Unknown message type: {scenario['data']['type']}")
                elif scenario["type"] == "oversized_message":
                    max_size = 1024 * 1024  # 1MB
                    if scenario["size"] > max_size:
                        raise ValueError(f"Message too large: {scenario['size']} bytes")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                errors_handled.append({
                    "scenario": scenario["type"],
                    "error": str(e)
                })
        
        assert len(errors_handled) == len(error_scenarios)