"""WebSocket test helpers for backend tests."""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
# class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, query_params=None, headers=None):
        self.query_params = query_params or {}
        self.headers = headers or {}
        # Mock: Generic component isolation for controlled unit testing
        self.state = MagicMock()
        # Mock: Generic component isolation for controlled unit testing
        self.app = MagicMock()
        # Mock: Generic component isolation for controlled unit testing
        self.accept = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.close = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.send_text = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.send_json = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.receive_text = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.receive_json = AsyncMock()

class MockAuthClient:
    """Mock auth client for testing."""
    
    def __init__(self, valid_response=True):
        self.valid_response = valid_response
        # Mock: Async component isolation for testing without real async operations
        self.validate_token_jwt = AsyncMock(return_value={
            "valid": valid_response,
            "user_id": "test-user-123" if valid_response else None,
            "email": "test@example.com" if valid_response else None,
            "permissions": [] if valid_response else None
        })

# COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
# class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.connections = {}
        # Mock: Generic component isolation for controlled unit testing
        self.connect = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.disconnect = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.send_message = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        self.broadcast = AsyncMock()
        # Mock: Service component isolation for predictable testing behavior
        self.get_connections = MagicMock(return_value=[])

def create_mock_websocket(token="valid-token", **kwargs):
    """Create a mock WebSocket with common settings."""
    query_params = {"token": token}
    query_params.update(kwargs.get("query_params", {}))
    
    return MockWebSocket(
        query_params=query_params,
        headers=kwargs.get("headers", {})
    )

def create_mock_auth_client(valid=True):
    """Create a mock auth client with standard responses."""
    return MockAuthClient(valid_response=valid)
