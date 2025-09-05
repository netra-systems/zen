"""
WebSocket Manager Mock Fixtures.

Provides mock WebSocket managers and related fixtures for testing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock

import pytest

logger = logging.getLogger(__name__)


# =============================================================================
# WEBSOCKET MANAGER MOCKS
# =============================================================================

class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.active_connections: Set[str] = set()
        self.user_connections: Dict[str, Set[str]] = {}
        self.connection_data: Dict[str, Dict[str, Any]] = {}
        self.messages_sent: List[Dict[str, Any]] = []
        self.broadcasts_sent: List[Dict[str, Any]] = []
        
    async def connect(self, connection_id: str, user_id: Optional[str] = None, **kwargs):
        """Mock connection method."""
        self.active_connections.add(connection_id)
        self.connection_data[connection_id] = {
            "user_id": user_id,
            "connected_at": "2024-01-01T00:00:00Z",
            **kwargs
        }
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
        logger.debug(f"Mock WebSocket connected: {connection_id}")
    
    async def disconnect(self, connection_id: str):
        """Mock disconnect method."""
        if connection_id in self.active_connections:
            self.active_connections.remove(connection_id)
            
            # Remove from user connections
            connection_data = self.connection_data.get(connection_id, {})
            user_id = connection_data.get("user_id")
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove connection data
            self.connection_data.pop(connection_id, None)
            
        logger.debug(f"Mock WebSocket disconnected: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """Mock send message method."""
        if connection_id in self.active_connections:
            self.messages_sent.append({
                "connection_id": connection_id,
                "message": message,
                "timestamp": "2024-01-01T00:00:00Z"
            })
            logger.debug(f"Mock message sent to {connection_id}: {message.get('type', 'unknown')}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Mock send to user method."""
        user_connections = self.user_connections.get(user_id, set())
        for connection_id in user_connections:
            await self.send_message(connection_id, message)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None):
        """Mock broadcast method."""
        exclude = exclude or set()
        target_connections = self.active_connections - exclude
        
        self.broadcasts_sent.append({
            "message": message,
            "target_connections": list(target_connections),
            "excluded_connections": list(exclude),
            "timestamp": "2024-01-01T00:00:00Z"
        })
        
        logger.debug(f"Mock broadcast sent to {len(target_connections)} connections: {message.get('type', 'unknown')}")
    
    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """Mock broadcast to room method."""
        # For simplicity, treat all active connections as in the room
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get connections for a specific user."""
        return self.user_connections.get(user_id, set()).copy()
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user has any active connections."""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection."""
        return self.connection_data.get(connection_id)
    
    async def shutdown(self):
        """Mock shutdown method."""
        connection_ids = list(self.active_connections)
        for connection_id in connection_ids:
            await self.disconnect(connection_id)
        logger.debug("Mock WebSocket manager shutdown")


class MockWebSocketConnection:
    """Mock individual WebSocket connection for testing."""
    
    def __init__(self, connection_id: str, user_id: Optional[str] = None):
        self.connection_id = connection_id
        self.user_id = user_id
        self.is_connected = True
        self.messages_received: List[Dict[str, Any]] = []
        self.messages_sent: List[Dict[str, Any]] = []
    
    async def send(self, message: Dict[str, Any]):
        """Mock send method."""
        if self.is_connected:
            self.messages_sent.append({
                "message": message,
                "timestamp": "2024-01-01T00:00:00Z"
            })
            logger.debug(f"Mock connection {self.connection_id} sent: {message.get('type', 'unknown')}")
    
    async def receive(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Mock receive method."""
        if not self.is_connected:
            raise ConnectionError("Connection closed")
            
        if self.messages_received:
            return self.messages_received.pop(0)
        else:
            # Return a default message for testing
            return {"type": "ping", "data": "test message"}
    
    def add_received_message(self, message: Dict[str, Any]):
        """Add a message to the received queue for testing."""
        self.messages_received.append(message)
    
    async def close(self):
        """Mock close method."""
        self.is_connected = False
        logger.debug(f"Mock connection {self.connection_id} closed")


# =============================================================================
# WEBSOCKET NOTIFICATION MOCKS
# =============================================================================

class MockWebSocketNotifier:
    """Mock WebSocket notifier for agent events."""
    
    def __init__(self):
        self.notifications_sent: List[Dict[str, Any]] = []
        self.enabled = True
    
    async def send_agent_started(self, user_id: str, agent_type: str, **kwargs):
        """Mock agent started notification."""
        if self.enabled:
            self.notifications_sent.append({
                "type": "agent_started",
                "user_id": user_id,
                "agent_type": agent_type,
                "timestamp": "2024-01-01T00:00:00Z",
                **kwargs
            })
    
    async def send_agent_thinking(self, user_id: str, message: str, **kwargs):
        """Mock agent thinking notification."""
        if self.enabled:
            self.notifications_sent.append({
                "type": "agent_thinking",
                "user_id": user_id,
                "message": message,
                "timestamp": "2024-01-01T00:00:00Z",
                **kwargs
            })
    
    async def send_tool_executing(self, user_id: str, tool_name: str, **kwargs):
        """Mock tool executing notification."""
        if self.enabled:
            self.notifications_sent.append({
                "type": "tool_executing",
                "user_id": user_id,
                "tool_name": tool_name,
                "timestamp": "2024-01-01T00:00:00Z",
                **kwargs
            })
    
    async def send_tool_completed(self, user_id: str, tool_name: str, result: Any, **kwargs):
        """Mock tool completed notification."""
        if self.enabled:
            self.notifications_sent.append({
                "type": "tool_completed",
                "user_id": user_id,
                "tool_name": tool_name,
                "result": result,
                "timestamp": "2024-01-01T00:00:00Z",
                **kwargs
            })
    
    async def send_agent_completed(self, user_id: str, response: str, **kwargs):
        """Mock agent completed notification."""
        if self.enabled:
            self.notifications_sent.append({
                "type": "agent_completed",
                "user_id": user_id,
                "response": response,
                "timestamp": "2024-01-01T00:00:00Z",
                **kwargs
            })
    
    async def send_error(self, user_id: str, error_message: str, **kwargs):
        """Mock error notification."""
        if self.enabled:
            self.notifications_sent.append({
                "type": "error",
                "user_id": user_id,
                "error_message": error_message,
                "timestamp": "2024-01-01T00:00:00Z",
                **kwargs
            })
    
    def enable(self):
        """Enable notifications."""
        self.enabled = True
    
    def disable(self):
        """Disable notifications."""
        self.enabled = False
    
    def get_notifications(self, notification_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sent notifications, optionally filtered by type."""
        if notification_type:
            return [n for n in self.notifications_sent if n.get("type") == notification_type]
        return self.notifications_sent.copy()
    
    def clear_notifications(self):
        """Clear all sent notifications."""
        self.notifications_sent.clear()


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_websocket_manager():
    """Provide a mock WebSocket manager for testing."""
    return MockWebSocketManager()


@pytest.fixture
def mock_websocket_connection():
    """Provide a mock WebSocket connection for testing."""
    return MockWebSocketConnection("test_connection_123", "test_user_456")


@pytest.fixture
def mock_websocket_notifier():
    """Provide a mock WebSocket notifier for testing."""
    return MockWebSocketNotifier()


@pytest.fixture
async def websocket_test_setup(mock_websocket_manager, mock_websocket_notifier):
    """Set up WebSocket test environment."""
    # Connect a few test connections
    await mock_websocket_manager.connect("conn_1", "user_1")
    await mock_websocket_manager.connect("conn_2", "user_2")
    await mock_websocket_manager.connect("conn_3", "user_1")  # User 1 has 2 connections
    
    yield {
        "manager": mock_websocket_manager,
        "notifier": mock_websocket_notifier,
        "connections": ["conn_1", "conn_2", "conn_3"],
        "users": ["user_1", "user_2"]
    }
    
    # Cleanup
    await mock_websocket_manager.shutdown()
    mock_websocket_notifier.clear_notifications()


@pytest.fixture
def websocket_manager_factory():
    """Factory for creating WebSocket manager mocks."""
    def create_manager(**kwargs):
        manager = MockWebSocketManager()
        # Apply any configuration from kwargs
        for key, value in kwargs.items():
            setattr(manager, key, value)
        return manager
    return create_manager


@pytest.fixture
def websocket_connection_factory():
    """Factory for creating WebSocket connection mocks."""
    def create_connection(connection_id: str, user_id: Optional[str] = None, **kwargs):
        connection = MockWebSocketConnection(connection_id, user_id)
        # Apply any configuration from kwargs
        for key, value in kwargs.items():
            setattr(connection, key, value)
        return connection
    return create_connection


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def assert_websocket_message_sent(mock_manager: MockWebSocketManager, message_type: str):
    """Assert that a WebSocket message of specific type was sent."""
    messages = [msg for msg in mock_manager.messages_sent if msg["message"].get("type") == message_type]
    assert len(messages) > 0, f"No WebSocket message of type '{message_type}' was sent"
    return messages[-1]  # Return the most recent message


def assert_websocket_broadcast_sent(mock_manager: MockWebSocketManager, message_type: str):
    """Assert that a WebSocket broadcast of specific type was sent."""
    broadcasts = [b for b in mock_manager.broadcasts_sent if b["message"].get("type") == message_type]
    assert len(broadcasts) > 0, f"No WebSocket broadcast of type '{message_type}' was sent"
    return broadcasts[-1]  # Return the most recent broadcast


def assert_agent_notification_sent(mock_notifier: MockWebSocketNotifier, notification_type: str):
    """Assert that an agent notification of specific type was sent."""
    notifications = mock_notifier.get_notifications(notification_type)
    assert len(notifications) > 0, f"No agent notification of type '{notification_type}' was sent"
    return notifications[-1]  # Return the most recent notification


def create_mock_websocket_context(user_id: str, connection_id: Optional[str] = None):
    """Create a mock WebSocket context for testing."""
    import uuid
    
    if connection_id is None:
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"
    
    context = {
        "connection_id": connection_id,
        "user_id": user_id,
        "connected_at": "2024-01-01T00:00:00Z",
        "authenticated": True,
        "session_data": {}
    }
    
    return context


# =============================================================================
# EXPORT ALL FIXTURES AND UTILITIES
# =============================================================================

__all__ = [
    # Mock classes
    'MockWebSocketManager',
    'MockWebSocketConnection',
    'MockWebSocketNotifier',
    
    # Pytest fixtures
    'mock_websocket_manager',
    'mock_websocket_connection',
    'mock_websocket_notifier',
    'websocket_test_setup',
    'websocket_manager_factory',
    'websocket_connection_factory',
    
    # Helper functions
    'assert_websocket_message_sent',
    'assert_websocket_broadcast_sent',
    'assert_agent_notification_sent',
    'create_mock_websocket_context'
]