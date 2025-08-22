"""
WebSocket Test Utilities
Shared utilities, mocks, and fixtures for WebSocket testing.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.services.websocket.message_queue import (
    MessagePriority,
    QueuedMessage,
)


class MessageType(Enum):
    """Test message types enum."""
    START_AGENT = "start_agent"
    USER_MESSAGE = "user_message"
    SYSTEM_STATUS = "system_status"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"


class MockMessageHandler(BaseMessageHandler):
    """Mock message handler for testing."""
    
    def __init__(self, message_type: str):
        self.message_type = message_type
        self.handled_messages = []
        self.handle_delay = 0
        self.should_fail = False
        
    def get_message_type(self) -> str:
        """Return message type for this handler."""
        return self.message_type
        
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Handle message with optional delay and failure."""
        if self.handle_delay > 0:
            await asyncio.sleep(self.handle_delay)
            
        if self.should_fail:
            raise NetraException("Mock handler failure")
            
        self.handled_messages.append({
            'user_id': user_id,
            'payload': payload,
            'timestamp': datetime.now(UTC)
        })


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, connection_id: str, user_id: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.sent_messages = []
        self.is_closed = False
        self.close_code = None
        self.close_reason = None
        
    async def send_text(self, data: str) -> None:
        """Mock sending text data."""
        if self.is_closed:
            raise Exception("Connection closed")
        self.sent_messages.append(data)
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock sending JSON data."""
        if self.is_closed:
            raise Exception("Connection closed")
        self.sent_messages.append(data)
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Mock closing connection."""
        self.is_closed = True
        self.close_code = code
        self.close_reason = reason


class MockConnectionManager:
    """Mock connection manager for testing."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocketConnection] = {}
        self.user_connections: Dict[str, List[str]] = {}
        self.broadcast_calls = []
        
    def add_connection(self, connection: MockWebSocketConnection) -> None:
        """Add mock connection."""
        self.connections[connection.connection_id] = connection
        
        if connection.user_id not in self.user_connections:
            self.user_connections[connection.user_id] = []
        self.user_connections[connection.user_id].append(connection.connection_id)
        
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Mock sending message to user."""
        if user_id in self.user_connections:
            for conn_id in self.user_connections[user_id]:
                conn = self.connections.get(conn_id)
                if conn and not conn.is_closed:
                    await conn.send_json(message)
                    
    async def broadcast_to_all(self, message: Dict[str, Any]) -> None:
        """Mock broadcasting to all connections."""
        self.broadcast_calls.append(message)
        
        for connection in self.connections.values():
            if not connection.is_closed:
                await connection.send_json(message)


@pytest.fixture
def mock_handler_registry():
    """Fixture providing mock handler registry."""
    registry = {}
    
    def register_handler(handler: BaseMessageHandler):
        registry[handler.get_message_type()] = handler
        
    def get_handler(message_type: str) -> Optional[BaseMessageHandler]:
        return registry.get(message_type)
        
    def clear_handlers():
        registry.clear()
        
    return {
        'register': register_handler,
        'get': get_handler,
        'clear': clear_handlers,
        'handlers': registry
    }


@pytest.fixture
def mock_connection_manager():
    """Fixture providing mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def sample_handlers():
    """Fixture providing sample message handlers."""
    return [
        MockMessageHandler("start_agent"),
        MockMessageHandler("user_message"),
        MockMessageHandler("system_status")
    ]


def create_test_message(
    message_type: str,
    payload: Dict[str, Any] = None,
    user_id: str = "test_user"
) -> Dict[str, Any]:
    """Create test message with standard format."""
    return {
        "type": message_type,
        "payload": payload or {},
        "user_id": user_id,
        "timestamp": datetime.now(UTC).isoformat()
    }


def create_queued_message(
    message_type: str,
    user_id: str = "test_user",
    priority: MessagePriority = MessagePriority.NORMAL
) -> QueuedMessage:
    """Create test queued message."""
    return QueuedMessage(
        id=f"test_{message_type}_{user_id}",
        user_id=user_id,
        message_type=message_type,
        payload={"test": "data"},
        priority=priority,
        created_at=datetime.now(UTC)
    )