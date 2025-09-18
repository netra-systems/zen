"""
WebSocket Test Helpers - SSOT Implementation

Provides centralized WebSocket testing utilities for all test frameworks.
This is the Single Source of Truth for WebSocket testing functionality.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Union
from unittest.mock import AsyncMock, MagicMock
import pytest


class WebSocketTestClient:
    """
    Mock WebSocket client for testing.

    Provides a standardized interface for WebSocket testing across
    all test suites, with SSOT compliance.
    """

    def __init__(self, url: str):
        self.url = url
        self.connected = False
        self.messages_received: List[Dict[str, Any]] = []
        self.messages_sent: List[Dict[str, Any]] = []
        self.connection_id = str(uuid.uuid4())

    async def connect(self):
        """Simulate WebSocket connection."""
        self.connected = True

    async def disconnect(self):
        """Simulate WebSocket disconnection."""
        self.connected = False

    async def send(self, message: Union[str, Dict[str, Any]]):
        """Send message to WebSocket."""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")

        if isinstance(message, str):
            try:
                parsed = json.loads(message)
            except json.JSONDecodeError:
                parsed = {"type": "text", "data": message}
        else:
            parsed = message

        self.messages_sent.append({
            "message": parsed,
            "timestamp": time.time(),
            "connection_id": self.connection_id
        })

    async def receive(self) -> Dict[str, Any]:
        """Receive message from WebSocket."""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")

        if self.messages_received:
            return self.messages_received.pop(0)

        # Return default test message
        return {
            "type": "test_message",
            "data": "Mock WebSocket message",
            "timestamp": time.time()
        }

    def add_received_message(self, message: Dict[str, Any]):
        """Add message to receive queue for testing."""
        self.messages_received.append(message)


class WebSocketTestSession:
    """
    WebSocket test session manager.

    Manages multiple WebSocket connections for testing complex scenarios.
    """

    def __init__(self):
        self.clients: Dict[str, WebSocketTestClient] = {}
        self.active_connections: Set[str] = set()

    def create_client(self, client_id: str, url: str = "ws://localhost:8000/ws") -> WebSocketTestClient:
        """Create a new WebSocket test client."""
        client = WebSocketTestClient(url)
        self.clients[client_id] = client
        return client

    async def connect_all(self):
        """Connect all clients."""
        for client_id, client in self.clients.items():
            await client.connect()
            self.active_connections.add(client_id)

    async def disconnect_all(self):
        """Disconnect all clients."""
        for client_id, client in self.clients.items():
            await client.disconnect()
        self.active_connections.clear()

    def get_client(self, client_id: str) -> Optional[WebSocketTestClient]:
        """Get client by ID."""
        return self.clients.get(client_id)


# Helper functions
def assert_websocket_events(events: List[Dict[str, Any]], expected_types: List[str]):
    """Assert that WebSocket events contain expected types in order."""
    actual_types = [event.get("type", "unknown") for event in events]
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"


def assert_websocket_message_received(client: WebSocketTestClient, message_type: str):
    """Assert that a WebSocket message of specific type was received."""
    received_messages = [msg["message"] for msg in client.messages_sent]
    matching_messages = [msg for msg in received_messages if msg.get("type") == message_type]
    assert len(matching_messages) > 0, f"No message of type '{message_type}' was received"
    return matching_messages[-1]


def assert_websocket_message_sent(client: WebSocketTestClient, message_type: str):
    """Assert that a WebSocket message of specific type was sent."""
    sent_messages = [msg["message"] for msg in client.messages_sent]
    matching_messages = [msg for msg in sent_messages if msg.get("type") == message_type]
    assert len(matching_messages) > 0, f"No message of type '{message_type}' was sent"
    return matching_messages[-1]


async def wait_for_websocket_connection(client: WebSocketTestClient, timeout: float = 5.0):
    """Wait for WebSocket connection to be established."""
    start_time = time.time()
    while not client.connected and (time.time() - start_time) < timeout:
        await asyncio.sleep(0.1)

    if not client.connected:
        raise TimeoutError(f"WebSocket connection not established within {timeout} seconds")


def websocket_test_context():
    """Create WebSocket test context."""
    return {
        "session": WebSocketTestSession(),
        "start_time": time.time(),
        "event_log": []
    }


# Pytest fixtures
@pytest.fixture
def websocket_test_client():
    """Provide WebSocket test client fixture."""
    return WebSocketTestClient("ws://localhost:8000/ws")


@pytest.fixture
def websocket_test_session():
    """Provide WebSocket test session fixture."""
    return WebSocketTestSession()


__all__ = [
    "WebSocketTestClient",
    "WebSocketTestSession",
    "assert_websocket_events",
    "assert_websocket_message_received",
    "assert_websocket_message_sent",
    "wait_for_websocket_connection",
    "websocket_test_context",
    "websocket_test_client",
    "websocket_test_session"
]