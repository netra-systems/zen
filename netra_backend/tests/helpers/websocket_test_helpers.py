"""WebSocket test helpers for backend tests."""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, query_params=None, headers=None):
        self.query_params = query_params or {}
        self.headers = headers or {}
        self.state = MagicMock()
        self.app = MagicMock()
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.send_text = AsyncMock()
        self.send_json = AsyncMock()
        self.receive_text = AsyncMock()
        self.receive_json = AsyncMock()

class MockAuthClient:
    """Mock auth client for testing."""
    
    def __init__(self, valid_response=True):
        self.valid_response = valid_response
        self.validate_token_jwt = AsyncMock(return_value={
            "valid": valid_response,
            "user_id": "test-user-123" if valid_response else None,
            "email": "test@example.com" if valid_response else None,
            "permissions": [] if valid_response else None
        })

class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.connections = {}
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.send_message = AsyncMock()
        self.broadcast = AsyncMock()
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
