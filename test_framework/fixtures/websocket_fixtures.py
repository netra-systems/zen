"""
WebSocket Test Fixtures - SSOT for WebSocket Testing

This module provides WebSocket fixtures and mock utilities for testing.
Following CLAUDE.md principles, these are minimal mocks for UNIT tests only.
Integration and E2E tests should use REAL WebSocket connections.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Testing Infrastructure
- Business Goal: Enable reliable WebSocket unit testing
- Value Impact: Provides controlled WebSocket testing environment
- Strategic Impact: Supports WebSocket auth compliance testing
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock
from dataclasses import dataclass, field

from tests.helpers.auth_test_utils import TestAuthHelper


@dataclass
class MockWebSocketState:
    """State tracking for mock WebSocket connections."""
    connected: bool = False
    closed: bool = False
    messages_sent: List[str] = field(default_factory=list)
    messages_received: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    close_code: Optional[int] = None
    close_reason: Optional[str] = None


class MockWebSocket:
    """
    Mock WebSocket for UNIT testing only.
    
    CRITICAL: This is for UNIT tests only. Integration and E2E tests
    MUST use real WebSocket connections per CLAUDE.md standards.
    """
    
    def __init__(self, headers: Optional[Dict[str, str]] = None, 
                 query_params: Optional[Dict[str, str]] = None):
        """Initialize mock WebSocket with optional headers and query params."""
        self.state = MockWebSocketState(
            headers=headers or {},
            query_params=query_params or {}
        )
        
        # Mock async methods
        self.send = AsyncMock(side_effect=self._mock_send)
        self.recv = AsyncMock(side_effect=self._mock_recv)
        self.close = AsyncMock(side_effect=self._mock_close)
        self.ping = AsyncMock(return_value=AsyncMock())
        self.pong = AsyncMock()
        
        # Properties
        self.headers = self.state.headers
        self.query_params = self.state.query_params
        
        # Connection state
        self.closed = False
        self.close_code = None
        self.close_reason = None
        
        # Message queues for simulation
        self._outbound_queue: List[str] = []
        self._inbound_queue: List[str] = []
        
    async def _mock_send(self, message: Union[str, bytes]):
        """Mock send implementation that tracks messages."""
        if isinstance(message, bytes):
            message = message.decode('utf-8')
            
        self.state.messages_sent.append(message)
        self._outbound_queue.append(message)
        
    async def _mock_recv(self) -> str:
        """Mock receive implementation that returns queued messages."""
        if self._inbound_queue:
            message = self._inbound_queue.pop(0)
            self.state.messages_received.append(message)
            return message
        else:
            # If no messages queued, simulate empty response or timeout
            await asyncio.sleep(0.1)
            return json.dumps({"type": "heartbeat", "timestamp": time.time()})
            
    async def _mock_close(self, code: int = 1000, reason: str = ""):
        """Mock close implementation."""
        self.closed = True
        self.close_code = code
        self.close_reason = reason
        self.state.connected = False
        self.state.closed = True
        self.state.close_code = code
        self.state.close_reason = reason
        
    def queue_inbound_message(self, message: Union[str, Dict[str, Any]]):
        """Queue a message to be received by the mock WebSocket."""
        if isinstance(message, dict):
            message = json.dumps(message)
        self._inbound_queue.append(message)
        
    def get_sent_messages(self) -> List[str]:
        """Get all messages that were sent through this WebSocket."""
        return self.state.messages_sent.copy()
        
    def get_received_messages(self) -> List[str]:
        """Get all messages that were received by this WebSocket."""
        return self.state.messages_received.copy()
        
    def simulate_connection_error(self):
        """Simulate a connection error."""
        self.recv.side_effect = ConnectionError("Simulated connection error")
        self.send.side_effect = ConnectionError("Simulated connection error")


def create_mock_websocket(
    headers: Optional[Dict[str, str]] = None,
    query_params: Optional[Dict[str, str]] = None,
    authenticated: bool = False,
    user_id: str = "test-user-123"
) -> MockWebSocket:
    """
    Create a mock WebSocket for UNIT testing.
    
    CRITICAL: This is for UNIT tests only. Integration and E2E tests
    MUST use real WebSocket connections per CLAUDE.md standards.
    
    Args:
        headers: Optional headers dict
        query_params: Optional query parameters dict
        authenticated: Whether to include authentication headers
        user_id: User ID for authenticated connections
        
    Returns:
        MockWebSocket instance configured for testing
    """
    # Start with provided headers or empty dict
    mock_headers = headers or {}
    mock_query_params = query_params or {}
    
    # Add authentication if requested
    if authenticated:
        auth_helper = TestAuthHelper()
        token = auth_helper.create_test_token(user_id)
        mock_headers["authorization"] = f"Bearer {token}"
        mock_headers["x-user-id"] = user_id
        mock_headers["x-test-mode"] = "true"
    
    # Add common WebSocket headers
    mock_headers.update({
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-version": "13",
        "sec-websocket-key": "test-websocket-key-123",
        "user-agent": "Test WebSocket Client"
    })
    
    return MockWebSocket(headers=mock_headers, query_params=mock_query_params)


def create_authenticated_mock_websocket(
    user_id: str = "test-user-123",
    email: Optional[str] = None,
    permissions: Optional[List[str]] = None
) -> MockWebSocket:
    """
    Create an authenticated mock WebSocket with proper JWT token.
    
    Args:
        user_id: User ID for the token
        email: Optional email (defaults to {user_id}@test.com)
        permissions: Optional permissions list
        
    Returns:
        MockWebSocket with proper authentication headers
    """
    auth_helper = TestAuthHelper()
    
    if permissions:
        token = auth_helper.create_test_token_with_permissions(
            user_id, permissions, email=email
        )
    else:
        token = auth_helper.create_test_token(user_id, email)
    
    headers = {
        "authorization": f"Bearer {token}",
        "x-user-id": user_id,
        "x-test-mode": "true",
        "x-test-type": "unit",
        "content-type": "application/json"
    }
    
    return create_mock_websocket(headers=headers, authenticated=False)  # Don't double-authenticate


def create_unauthenticated_mock_websocket() -> MockWebSocket:
    """
    Create an unauthenticated mock WebSocket for testing auth failures.
    
    Returns:
        MockWebSocket without authentication headers
    """
    headers = {
        "connection": "upgrade", 
        "upgrade": "websocket",
        "sec-websocket-version": "13",
        "user-agent": "Test WebSocket Client"
    }
    
    return MockWebSocket(headers=headers)


class MockWebSocketManager:
    """
    Mock WebSocket manager for testing WebSocket event systems.
    
    CRITICAL: For UNIT tests only. Integration tests must use real WebSocket manager.
    """
    
    def __init__(self):
        """Initialize mock WebSocket manager."""
        self.events_sent: List[Dict[str, Any]] = []
        self.connections: Dict[str, MockWebSocket] = {}
        self.thread_mappings: Dict[str, str] = {}  # thread_id -> connection_id
        
        # Mock async methods
        self.send_to_thread = AsyncMock(side_effect=self._mock_send_to_thread)
        self.broadcast = AsyncMock(side_effect=self._mock_broadcast)
        self.register_thread_connection = AsyncMock(side_effect=self._mock_register)
        self.unregister_thread_connection = AsyncMock(side_effect=self._mock_unregister)
        
    async def _mock_send_to_thread(
        self, 
        thread_id: str, 
        event_type: str, 
        data: Dict[str, Any]
    ) -> bool:
        """Mock implementation of sending event to specific thread."""
        event = {
            "thread_id": thread_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.events_sent.append(event)
        
        # If we have a connection for this thread, queue the message
        connection_id = self.thread_mappings.get(thread_id)
        if connection_id and connection_id in self.connections:
            websocket = self.connections[connection_id]
            websocket.queue_inbound_message(event)
            
        return True
        
    async def _mock_broadcast(self, event_type: str, data: Dict[str, Any]) -> int:
        """Mock implementation of broadcasting to all connections."""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "broadcast": True
        }
        
        self.events_sent.append(event)
        
        # Queue message to all connections
        for websocket in self.connections.values():
            websocket.queue_inbound_message(event)
            
        return len(self.connections)
        
    async def _mock_register(self, thread_id: str, connection_id: str) -> bool:
        """Mock thread connection registration."""
        self.thread_mappings[thread_id] = connection_id
        return True
        
    async def _mock_unregister(self, thread_id: str) -> bool:
        """Mock thread connection unregistration."""
        self.thread_mappings.pop(thread_id, None)
        return True
        
    def add_connection(self, connection_id: str, websocket: MockWebSocket):
        """Add a mock WebSocket connection."""
        self.connections[connection_id] = websocket
        
    def remove_connection(self, connection_id: str):
        """Remove a mock WebSocket connection."""
        self.connections.pop(connection_id, None)
        
    def get_events_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all events sent to a specific thread."""
        return [event for event in self.events_sent 
                if event.get("thread_id") == thread_id]
                
    def get_broadcast_events(self) -> List[Dict[str, Any]]:
        """Get all broadcast events."""
        return [event for event in self.events_sent 
                if event.get("broadcast", False)]


# Convenience fixtures for common test scenarios
def websocket_auth_test_scenario():
    """Create a complete WebSocket auth testing scenario."""
    return {
        "authenticated_ws": create_authenticated_mock_websocket("auth-user-123"),
        "unauthenticated_ws": create_unauthenticated_mock_websocket(),
        "admin_ws": create_authenticated_mock_websocket(
            "admin-user", permissions=["read", "write", "admin"]
        ),
        "readonly_ws": create_authenticated_mock_websocket(
            "readonly-user", permissions=["read"]
        )
    }


def websocket_event_test_scenario():
    """Create a complete WebSocket event testing scenario."""
    manager = MockWebSocketManager()
    
    # Add some test connections
    user_ws = create_authenticated_mock_websocket("event-user-123")
    admin_ws = create_authenticated_mock_websocket("event-admin", permissions=["admin"])
    
    manager.add_connection("user_conn", user_ws)
    manager.add_connection("admin_conn", admin_ws)
    
    return {
        "manager": manager,
        "user_websocket": user_ws,
        "admin_websocket": admin_ws,
        "user_connection_id": "user_conn",
        "admin_connection_id": "admin_conn"
    }


# Export the main functions for use in tests
__all__ = [
    "MockWebSocket",
    "MockWebSocketManager",
    "create_mock_websocket",
    "create_authenticated_mock_websocket", 
    "create_unauthenticated_mock_websocket",
    "websocket_auth_test_scenario",
    "websocket_event_test_scenario"
]