"""
WebSocket Test Helpers for E2E Tests

Provides WebSocketTestManager and related utilities for E2E testing.
Uses SSOT patterns and imports from the centralized test framework.
"""

# Import from SSOT websocket test helpers
from test_framework.fixtures.websocket_test_helpers import (
    WebSocketTestClient,
    WebSocketTestSession,
    assert_websocket_events,
    assert_websocket_message_received,
    assert_websocket_message_sent,
    wait_for_websocket_connection,
    websocket_test_context
)


class WebSocketTestManager:
    """
    WebSocket Test Manager for E2E tests.
    
    Provides a high-level interface for managing WebSocket connections
    during E2E testing, with SSOT compliance and real service integration.
    """
    
    def __init__(self, base_url: str = "ws://localhost:8000/ws"):
        """
        Initialize WebSocket test manager.
        
        Args:
            base_url: Base WebSocket URL for connections
        """
        self.base_url = base_url
        self.session = WebSocketTestSession()
        self._client_counter = 0
        
    def create_client(self, client_id: str = None) -> WebSocketTestClient:
        """Create a new WebSocket test client."""
        if client_id is None:
            self._client_counter += 1
            client_id = f"test_client_{self._client_counter}"
            
        return self.session.create_client(client_id, self.base_url)
    
    async def connect_client(self, client_id: str, headers: dict = None) -> WebSocketTestClient:
        """Connect a client and return it."""
        await self.session.connect_client(client_id, headers=headers)
        return self.session.get_client(client_id)
        
    async def disconnect_client(self, client_id: str):
        """Disconnect a specific client."""
        await self.session.disconnect_client(client_id)
        
    async def disconnect_all(self):
        """Disconnect all clients."""
        await self.session.disconnect_all()
        
    def get_client(self, client_id: str) -> WebSocketTestClient:
        """Get a specific client."""
        return self.session.get_client(client_id)
        
    async def send_message(self, client_id: str, message: dict):
        """Send message via specific client."""
        client = self.session.get_client(client_id)
        await client.send_message(message)
        
    async def wait_for_message(self, client_id: str, message_type: str, timeout: float = 10.0):
        """Wait for specific message type on specific client."""
        client = self.session.get_client(client_id)
        return await client.wait_for_message(message_type, timeout)
        
    def get_received_messages(self, client_id: str, message_type: str = None):
        """Get received messages from specific client."""
        client = self.session.get_client(client_id)
        return client.get_received_messages(message_type)
        
    def assert_message_received(self, client_id: str, message_type: str, content: dict = None):
        """Assert that a message was received by specific client."""
        client = self.session.get_client(client_id)
        return assert_websocket_message_received(client, message_type, content)
        
    def assert_events_received(self, client_id: str, expected_event_types: list):
        """Assert that specific events were received by client."""
        client = self.session.get_client(client_id)
        messages = client.get_received_messages()
        assert_websocket_events(messages, expected_event_types)


# Export for backward compatibility
__all__ = [
    "WebSocketTestManager",
    "WebSocketTestClient", 
    "WebSocketTestSession",
    "assert_websocket_events",
    "assert_websocket_message_received",
    "assert_websocket_message_sent",
    "wait_for_websocket_connection",
    "websocket_test_context"
]