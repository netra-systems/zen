"""
WebSocket Test Fixtures Module

This module provides SSOT WebSocket fixtures for integration tests.
Prevents import errors and provides consistent WebSocket test utilities.

Business Value:
- Prevents test collection failures due to missing fixtures
- Provides reusable WebSocket test components
- Ensures consistent WebSocket testing patterns
"""

import pytest
import asyncio
import websockets
from typing import Any, Dict, Optional, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.fixture
async def websocket_client_fixture() -> AsyncGenerator[Any, None]:
    """
    Fixture providing a mock WebSocket client for integration tests.
    
    Returns:
        Mock WebSocket client with send/receive capabilities
    """
    mock_client = AsyncMock()
    
    # Mock WebSocket client methods
    mock_client.send = AsyncMock()
    mock_client.recv = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.ping = AsyncMock()
    mock_client.pong = AsyncMock()
    
    # Mock connection properties
    mock_client.closed = False
    mock_client.state = websockets.ConnectionState.OPEN
    
    try:
        yield mock_client
    finally:
        # Cleanup
        mock_client.closed = True
        await mock_client.close()


@pytest.fixture
async def websocket_connection_fixture() -> AsyncGenerator[Any, None]:
    """
    Fixture providing a mock WebSocket connection for integration tests.
    
    Returns:
        Mock WebSocket connection with full lifecycle management
    """
    mock_connection = AsyncMock()
    
    # Connection lifecycle methods
    mock_connection.connect = AsyncMock()
    mock_connection.disconnect = AsyncMock()
    mock_connection.is_connected = MagicMock(return_value=True)
    
    # Message handling
    mock_connection.send_message = AsyncMock()
    mock_connection.receive_message = AsyncMock()
    mock_connection.send_json = AsyncMock()
    mock_connection.receive_json = AsyncMock()
    
    # Event handling
    mock_connection.add_event_listener = MagicMock()
    mock_connection.remove_event_listener = MagicMock()
    mock_connection.emit_event = AsyncMock()
    
    # Connection properties
    mock_connection.client_id = "test_websocket_client"
    mock_connection.user_id = "test_user"
    mock_connection.authenticated = True
    
    try:
        yield mock_connection
    finally:
        # Cleanup
        await mock_connection.disconnect()


@pytest.fixture
def websocket_manager_fixture() -> Any:
    """
    Fixture providing a mock WebSocket manager for integration tests.
    
    Returns:
        Mock WebSocket manager with connection management capabilities
    """
    mock_manager = MagicMock()
    
    # Connection management
    mock_manager.add_connection = AsyncMock()
    mock_manager.remove_connection = AsyncMock()
    mock_manager.get_connection = MagicMock()
    mock_manager.get_connection_by_client_id = MagicMock()
    mock_manager.get_connections_for_user = MagicMock(return_value=[])
    
    # Message broadcasting
    mock_manager.broadcast_to_user = AsyncMock()
    mock_manager.broadcast_to_all = AsyncMock()
    mock_manager.send_to_connection = AsyncMock()
    
    # Event management
    mock_manager.emit_agent_event = AsyncMock()
    mock_manager.emit_system_event = AsyncMock()
    
    # Manager properties
    mock_manager.connection_count = 0
    mock_manager.active_connections = {}
    
    return mock_manager


@pytest.fixture
async def authenticated_websocket_fixture() -> AsyncGenerator[Dict[str, Any], None]:
    """
    Fixture providing an authenticated WebSocket connection for integration tests.
    
    Returns:
        Dictionary with authenticated WebSocket client and context
    """
    # Mock authenticated user context
    user_context = {
        "user_id": "test_authenticated_user",
        "email": "test@netra-testing.ai",
        "authenticated": True,
        "jwt_token": "mock_jwt_token",
        "permissions": ["chat", "ai_analysis"]
    }
    
    # Mock authenticated WebSocket client
    mock_client = AsyncMock()
    mock_client.send = AsyncMock()
    mock_client.recv = AsyncMock()
    mock_client.close = AsyncMock()
    
    # Add authentication properties
    mock_client.user_context = user_context
    mock_client.authenticated = True
    mock_client.client_id = f"auth_ws_{user_context['user_id']}"
    
    websocket_data = {
        "client": mock_client,
        "user_context": user_context,
        "client_id": mock_client.client_id
    }
    
    try:
        yield websocket_data
    finally:
        # Cleanup
        await mock_client.close()


@pytest.fixture
def websocket_event_collector_fixture() -> Any:
    """
    Fixture providing an event collector for WebSocket events during tests.
    
    Returns:
        Event collector that captures WebSocket events for validation
    """
    class WebSocketEventCollector:
        def __init__(self):
            self.events = []
            self.event_counts = {}
        
        async def collect_event(self, event_type: str, event_data: Dict[str, Any]):
            """Collect a WebSocket event for later validation"""
            event = {
                "type": event_type,
                "data": event_data,
                "timestamp": asyncio.get_event_loop().time()
            }
            self.events.append(event)
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        def get_events_by_type(self, event_type: str):
            """Get all events of a specific type"""
            return [e for e in self.events if e["type"] == event_type]
        
        def get_event_count(self, event_type: str) -> int:
            """Get count of events by type"""
            return self.event_counts.get(event_type, 0)
        
        def clear_events(self):
            """Clear all collected events"""
            self.events.clear()
            self.event_counts.clear()
    
    return WebSocketEventCollector()