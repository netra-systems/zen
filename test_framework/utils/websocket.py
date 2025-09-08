"""
WebSocket Test Utilities

Utilities for testing WebSocket functionality.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


def create_test_message(
    message_type: str = "user_message",
    content: str = "Test message", 
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a test WebSocket message."""
    # SSOT COMPLIANCE FIX: Use UnifiedIdGenerator instead of direct UUID
    from shared.id_generation import UnifiedIdGenerator
    
    return {
        "id": UnifiedIdGenerator.generate_message_id(message_type, user_id or "test_user"),
        "type": message_type,
        "content": content,
        "thread_id": thread_id or UnifiedIdGenerator.generate_base_id("thread"),
        "user_id": user_id or UnifiedIdGenerator.generate_base_id("user"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {}
    }


def create_websocket_mock(user_id: Optional[str] = None) -> MagicMock:
    """Create a mock WebSocket connection."""
    # SSOT COMPLIANCE FIX: Use UnifiedIdGenerator instead of direct UUID
    from shared.id_generation import UnifiedIdGenerator
    
    mock = MagicMock()
    mock.user_id = user_id or UnifiedIdGenerator.generate_base_id("user")
    mock.connected = True
    mock.send_json = AsyncMock()
    mock.receive_json = AsyncMock()
    mock.close = AsyncMock()
    
    # Mock message queue for testing
    mock._message_queue = []
    
    async def mock_receive():
        if mock._message_queue:
            return mock._message_queue.pop(0)
        await asyncio.sleep(0.1)  # Simulate waiting
        return {"type": "ping"}
    
    mock.receive_json.side_effect = mock_receive
    
    def add_message(message):
        mock._message_queue.append(message)
    
    mock.add_test_message = add_message
    
    return mock


def create_websocket_manager_mock() -> MagicMock:
    """Create a mock WebSocket manager."""
    mock = MagicMock()
    mock.connections = {}
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.broadcast = AsyncMock()
    mock.send_to_user = AsyncMock()
    mock.get_user_connections = MagicMock(return_value=[])
    
    return mock


class WebSocketTestHelper:
    """Helper class for WebSocket testing."""
    
    def __init__(self):
        """Initialize WebSocket test helper."""
        self.connections: Dict[str, MagicMock] = {}
        self.messages: List[Dict[str, Any]] = []
    
    def create_connection(self, user_id: str) -> MagicMock:
        """Create a test WebSocket connection."""
        connection = create_websocket_mock(user_id)
        self.connections[user_id] = connection
        return connection
    
    def add_test_message(self, user_id: str, message: Dict[str, Any]):
        """Add a test message to a connection."""
        if user_id in self.connections:
            self.connections[user_id].add_test_message(message)
    
    def track_sent_message(self, message: Dict[str, Any]):
        """Track a sent message."""
        self.messages.append({
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "direction": "sent"
        })
    
    def track_received_message(self, message: Dict[str, Any]):
        """Track a received message."""
        self.messages.append({
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "direction": "received"
        })
    
    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages by type."""
        return [
            msg for msg in self.messages 
            if msg["message"].get("type") == message_type
        ]
    
    def clear(self):
        """Clear all data."""
        self.connections.clear()
        self.messages.clear()