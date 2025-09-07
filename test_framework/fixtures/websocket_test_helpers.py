"""
WebSocket Test Helpers.

Provides utilities and helpers for testing WebSocket functionality.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import pytest

logger = logging.getLogger(__name__)


# =============================================================================
# WEBSOCKET TEST CLIENT
# =============================================================================

class WebSocketTestClient:
    """Test client for WebSocket connections."""
    
    def __init__(self, url: str = "ws://localhost:8000/ws"):
        self.url = url
        self.websocket = None
        self.connected = False
        self.received_messages: List[Dict[str, Any]] = []
        self.sent_messages: List[Dict[str, Any]] = []
        self.connection_id: Optional[str] = None
        self.user_id: Optional[str] = None
    
    async def connect(self, headers: Optional[Dict[str, str]] = None, **kwargs):
        """Connect to WebSocket."""
        try:
            import websockets
            self.websocket = await websockets.connect(
                self.url,
                extra_headers=headers or {},
                **kwargs
            )
            self.connected = True
            logger.info(f"WebSocket test client connected to {self.url}")
        except ImportError:
            # Mock WebSocket for testing without websockets library
            self.websocket = AsyncMock()
            self.connected = True
            logger.info("Using mock WebSocket connection")
        except Exception as e:
            logger.error(f"Failed to connect WebSocket test client: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket and self.connected:
            try:
                if hasattr(self.websocket, 'close') and not isinstance(self.websocket, AsyncMock):
                    await self.websocket.close()
                self.connected = False
                logger.info("WebSocket test client disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting WebSocket: {e}")
                self.connected = False
    
    async def send_message(self, message: Union[Dict[str, Any], str]):
        """Send message to WebSocket."""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")
        
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = message
            
        try:
            if hasattr(self.websocket, 'send') and not isinstance(self.websocket, AsyncMock):
                await self.websocket.send(message_str)
            
            # Track sent message
            self.sent_messages.append({
                "message": message if isinstance(message, dict) else {"raw": message},
                "timestamp": "2024-01-01T00:00:00Z"
            })
            
            logger.debug(f"WebSocket test client sent message: {message}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise
    
    async def receive_message(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Receive message from WebSocket."""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")
        
        try:
            if isinstance(self.websocket, AsyncMock):
                # Return mock message
                message_str = '{"type": "test", "data": "mock message"}'
            else:
                message_str = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=timeout
                )
            
            message = json.loads(message_str)
            
            # Track received message
            self.received_messages.append({
                "message": message,
                "timestamp": "2024-01-01T00:00:00Z"
            })
            
            logger.debug(f"WebSocket test client received message: {message}")
            return message
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"No message received within {timeout} seconds")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode WebSocket message: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to receive WebSocket message: {e}")
            raise
    
    async def wait_for_message(self, message_type: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Wait for a specific type of message."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                message = await self.receive_message(timeout=1.0)
                if message.get("type") == message_type:
                    return message
            except TimeoutError:
                continue  # Keep waiting
        
        raise TimeoutError(f"Message type '{message_type}' not received within {timeout} seconds")
    
    def get_received_messages(self, message_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get received messages, optionally filtered by type."""
        messages = [msg["message"] for msg in self.received_messages]
        if message_type:
            messages = [msg for msg in messages if msg.get("type") == message_type]
        return messages
    
    def get_sent_messages(self, message_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sent messages, optionally filtered by type."""
        messages = [msg["message"] for msg in self.sent_messages]
        if message_type:
            messages = [msg for msg in messages if msg.get("type") == message_type]
        return messages
    
    def clear_message_history(self):
        """Clear message history."""
        self.received_messages.clear()
        self.sent_messages.clear()


# =============================================================================
# WEBSOCKET TEST UTILITIES
# =============================================================================

class WebSocketTestSession:
    """Test session for managing multiple WebSocket connections."""
    
    def __init__(self):
        self.clients: Dict[str, WebSocketTestClient] = {}
        self.active_sessions: List[str] = []
    
    def create_client(self, client_id: str, url: str = "ws://localhost:8000/ws") -> WebSocketTestClient:
        """Create a new WebSocket test client."""
        client = WebSocketTestClient(url)
        self.clients[client_id] = client
        return client
    
    async def connect_client(self, client_id: str, headers: Optional[Dict[str, str]] = None):
        """Connect a specific client."""
        if client_id not in self.clients:
            raise ValueError(f"Client '{client_id}' not found")
        
        client = self.clients[client_id]
        await client.connect(headers=headers)
        if client_id not in self.active_sessions:
            self.active_sessions.append(client_id)
    
    async def disconnect_client(self, client_id: str):
        """Disconnect a specific client."""
        if client_id in self.clients:
            await self.clients[client_id].disconnect()
            if client_id in self.active_sessions:
                self.active_sessions.remove(client_id)
    
    async def disconnect_all(self):
        """Disconnect all clients."""
        for client_id in list(self.active_sessions):
            await self.disconnect_client(client_id)
    
    def get_client(self, client_id: str) -> WebSocketTestClient:
        """Get a specific client."""
        if client_id not in self.clients:
            raise ValueError(f"Client '{client_id}' not found")
        return self.clients[client_id]
    
    async def broadcast_message(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """Send message to all connected clients."""
        exclude = exclude or []
        for client_id in self.active_sessions:
            if client_id not in exclude:
                await self.clients[client_id].send_message(message)
    
    def get_all_received_messages(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get received messages from all clients."""
        return {
            client_id: client.get_received_messages()
            for client_id, client in self.clients.items()
        }


# =============================================================================
# WEBSOCKET ASSERTION HELPERS
# =============================================================================

def assert_websocket_events(events: List[Dict[str, Any]], expected_event_types: List[str]):
    """
    Assert that WebSocket events contain all expected event types.
    
    This function validates the 5 MISSION CRITICAL WebSocket events that enable
    chat business value: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed.
    
    Args:
        events: List of WebSocket event dictionaries
        expected_event_types: List of expected event type strings
        
    Raises:
        AssertionError: If any expected event type is missing
    """
    actual_event_types = [event.get("type", "unknown") for event in events]
    
    for expected_type in expected_event_types:
        assert expected_type in actual_event_types, (
            f"Missing expected WebSocket event type: {expected_type}. "
            f"Actual events: {actual_event_types}"
        )


def assert_websocket_message_received(
    client: WebSocketTestClient, 
    message_type: str,
    content: Optional[Dict[str, Any]] = None
):
    """Assert that a WebSocket message was received."""
    messages = client.get_received_messages(message_type)
    assert len(messages) > 0, f"No message of type '{message_type}' received"
    
    if content:
        latest_message = messages[-1]
        for key, expected_value in content.items():
            assert key in latest_message, f"Key '{key}' not found in message"
            assert latest_message[key] == expected_value, f"Expected {key}='{expected_value}', got '{latest_message[key]}'"
    
    return messages[-1]


def assert_websocket_message_sent(
    client: WebSocketTestClient,
    message_type: str,
    content: Optional[Dict[str, Any]] = None
):
    """Assert that a WebSocket message was sent."""
    messages = client.get_sent_messages(message_type)
    assert len(messages) > 0, f"No message of type '{message_type}' sent"
    
    if content:
        latest_message = messages[-1]
        for key, expected_value in content.items():
            assert key in latest_message, f"Key '{key}' not found in message"
            assert latest_message[key] == expected_value, f"Expected {key}='{expected_value}', got '{latest_message[key]}'"
    
    return messages[-1]


async def wait_for_websocket_connection(client: WebSocketTestClient, timeout: float = 5.0):
    """Wait for WebSocket connection to be established."""
    start_time = asyncio.get_event_loop().time()
    
    while not client.connected:
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"WebSocket connection not established within {timeout} seconds")
        await asyncio.sleep(0.1)


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
async def websocket_test_client():
    """Provide a WebSocket test client."""
    client = WebSocketTestClient()
    yield client
    await client.disconnect()


@pytest.fixture
async def websocket_test_session():
    """Provide a WebSocket test session."""
    session = WebSocketTestSession()
    yield session
    await session.disconnect_all()


@pytest.fixture
def websocket_message_factory():
    """Factory for creating WebSocket test messages."""
    def create_message(message_type: str, **data):
        return {
            "type": message_type,
            "timestamp": "2024-01-01T00:00:00Z",
            **data
        }
    return create_message


@pytest.fixture
async def connected_websocket_client():
    """Provide a connected WebSocket test client."""
    client = WebSocketTestClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def multi_user_websocket_session():
    """Provide a multi-user WebSocket test session."""
    session = WebSocketTestSession()
    
    # Create clients for different users
    user1_client = session.create_client("user1", "ws://localhost:8000/ws")
    user2_client = session.create_client("user2", "ws://localhost:8000/ws")
    user3_client = session.create_client("user3", "ws://localhost:8000/ws")
    
    await session.connect_client("user1", headers={"Authorization": "Bearer user1_token"})
    await session.connect_client("user2", headers={"Authorization": "Bearer user2_token"})
    await session.connect_client("user3", headers={"Authorization": "Bearer user3_token"})
    
    yield {
        "session": session,
        "users": {
            "user1": user1_client,
            "user2": user2_client,
            "user3": user3_client
        }
    }
    
    await session.disconnect_all()


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

@asynccontextmanager
async def websocket_test_context(url: str = "ws://localhost:8000/ws", headers: Optional[Dict[str, str]] = None):
    """Context manager for WebSocket testing."""
    client = WebSocketTestClient(url)
    try:
        await client.connect(headers=headers)
        yield client
    finally:
        await client.disconnect()


@asynccontextmanager
async def multiple_websocket_context(count: int, base_url: str = "ws://localhost:8000/ws"):
    """Context manager for multiple WebSocket connections."""
    clients = []
    try:
        for i in range(count):
            client = WebSocketTestClient(f"{base_url}?client_id=test_client_{i}")
            await client.connect()
            clients.append(client)
        yield clients
    finally:
        for client in clients:
            await client.disconnect()


# =============================================================================
# EXPORT ALL HELPERS AND FIXTURES
# =============================================================================

__all__ = [
    # Test client classes
    'WebSocketTestClient',
    'WebSocketTestSession',
    
    # Assertion helpers
    'assert_websocket_events',
    'assert_websocket_message_received',
    'assert_websocket_message_sent',
    'wait_for_websocket_connection',
    
    # Pytest fixtures
    'websocket_test_client',
    'websocket_test_session',
    'websocket_message_factory',
    'connected_websocket_client',
    'multi_user_websocket_session',
    
    # Context managers
    'websocket_test_context',
    'multiple_websocket_context'
]