"""
WebSocket mock utilities for integration tests.
Provides mock implementations for WebSocket testing scenarios.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import AsyncMock, MagicMock
import json
import pytest


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, connection_id: str = "test_connection_001"):
        self.connection_id = connection_id
        self.is_open = True
        self.received_messages: List[Dict[str, Any]] = []
        self.sent_messages: List[Dict[str, Any]] = []
        self.close_code: Optional[int] = None
        self.close_reason: Optional[str] = None
        
    async def send_text(self, message: str):
        """Mock send_text method."""
        if not self.is_open:
            raise RuntimeError("WebSocket connection is closed")
        try:
            message_data = json.loads(message) if isinstance(message, str) else message
            self.sent_messages.append(message_data)
        except json.JSONDecodeError:
            self.sent_messages.append({"raw_text": message})
    
    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method."""
        if not self.is_open:
            raise RuntimeError("WebSocket connection is closed")
        self.sent_messages.append(data)
    
    async def receive_text(self) -> str:
        """Mock receive_text method."""
        if not self.is_open:
            raise RuntimeError("WebSocket connection is closed")
        if self.received_messages:
            message = self.received_messages.pop(0)
            return json.dumps(message) if isinstance(message, dict) else str(message)
        await asyncio.sleep(0.1)  # Simulate waiting
        return '{"type": "heartbeat"}'
    
    async def receive_json(self) -> Dict[str, Any]:
        """Mock receive_json method."""
        if not self.is_open:
            raise RuntimeError("WebSocket connection is closed")
        if self.received_messages:
            return self.received_messages.pop(0)
        await asyncio.sleep(0.1)  # Simulate waiting
        return {"type": "heartbeat"}
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Mock close method."""
        self.is_open = False
        self.close_code = code
        self.close_reason = reason
    
    def add_received_message(self, message: Dict[str, Any]):
        """Add a message to the received queue for testing."""
        self.received_messages.append(message)


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocketConnection] = {}
        self.connection_handlers: Dict[str, Callable] = {}
        self.global_handlers: List[Callable] = []
        
    def add_connection(self, connection_id: str, connection: MockWebSocketConnection = None):
        """Add a mock connection."""
        if connection is None:
            connection = MockWebSocketConnection(connection_id)
        self.connections[connection_id] = connection
        return connection
    
    def remove_connection(self, connection_id: str):
        """Remove a mock connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """Mock broadcast to all connections."""
        for conn_id, connection in self.connections.items():
            if exclude_connection and conn_id == exclude_connection:
                continue
            await connection.send_json(message)
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Mock send to specific connection."""
        if connection_id in self.connections:
            await self.connections[connection_id].send_json(message)
    
    def get_connection(self, connection_id: str) -> Optional[MockWebSocketConnection]:
        """Get a connection by ID."""
        return self.connections.get(connection_id)
    
    def get_all_connections(self) -> Dict[str, MockWebSocketConnection]:
        """Get all connections."""
        return self.connections.copy()


class MockWebSocketState:
    """Mock WebSocket state for testing."""
    
    def __init__(self):
        self.connection_states: Dict[str, Dict[str, Any]] = {}
        self.message_history: List[Dict[str, Any]] = []
        
    def set_connection_state(self, connection_id: str, state: Dict[str, Any]):
        """Set state for a connection."""
        self.connection_states[connection_id] = state
    
    def get_connection_state(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get state for a connection."""
        return self.connection_states.get(connection_id)
    
    def add_message_to_history(self, message: Dict[str, Any]):
        """Add message to history."""
        self.message_history.append(message)
    
    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get message history."""
        return self.message_history.copy()
    
    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()


@pytest.fixture
def mock_websocket_connection():
    """Fixture providing a mock WebSocket connection."""
    return MockWebSocketConnection()


@pytest.fixture
def mock_websocket_manager():
    """Fixture providing a mock WebSocket manager."""
    return MockWebSocketManager()


@pytest.fixture
def mock_websocket_state():
    """Fixture providing a mock WebSocket state."""
    return MockWebSocketState()


# Additional mock utilities

def create_mock_websocket_message(
    message_type: str = "test_message",
    data: Optional[Dict[str, Any]] = None,
    connection_id: str = "test_connection_001",
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Create a mock WebSocket message."""
    import datetime
    from datetime import timezone
    return {
        "type": message_type,
        "data": data or {},
        "connection_id": connection_id,
        "timestamp": timestamp or datetime.datetime.now(timezone.utc).isoformat()
    }


async def simulate_websocket_flow(
    connection: MockWebSocketConnection,
    messages: List[Dict[str, Any]],
    delay_between_messages: float = 0.01
):
    """Simulate a WebSocket message flow."""
    for message in messages:
        connection.add_received_message(message)
        await asyncio.sleep(delay_between_messages)


class MockWebSocketError(Exception):
    """Mock WebSocket error for testing error scenarios."""
    
    def __init__(self, message: str, code: int = 1000):
        self.message = message
        self.code = code
        super().__init__(message)


def create_error_scenario_mock(error_type: str = "connection_lost") -> MockWebSocketConnection:
    """Create a mock connection that simulates various error scenarios."""
    connection = MockWebSocketConnection()
    
    if error_type == "connection_lost":
        connection.is_open = False
        connection.close_code = 1006
        connection.close_reason = "Connection lost"
    elif error_type == "auth_failure":
        connection.add_received_message({
            "type": "error", 
            "code": "AUTH_FAILED",
            "message": "Authentication failed"
        })
    elif error_type == "rate_limit":
        connection.add_received_message({
            "type": "error",
            "code": "RATE_LIMITED", 
            "message": "Rate limit exceeded"
        })
    
    return connection