"""
Pytest fixtures for WebSocketManager tests
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from starlette.websockets import WebSocketState

from app.ws_manager import WebSocketManager, ConnectionInfo


class MockWebSocket:
    """Enhanced mock WebSocket for comprehensive testing"""
    def __init__(self, state=WebSocketState.CONNECTED):
        self.client_state = state
        self.send_json = AsyncMock()
        self.close = AsyncMock()
        self.send_calls = []
        self.close_calls = []
    
    async def mock_send_json(self, data):
        self.send_calls.append(data)
    
    async def mock_close(self, code=1000, reason=""):
        self.close_calls.append({"code": code, "reason": reason})
        self.client_state = WebSocketState.DISCONNECTED


@pytest.fixture
def fresh_manager():
    """Create a fresh WebSocketManager instance for each test"""
    # Reset singleton
    WebSocketManager._instance = None
    WebSocketManager._initialized = False
    
    manager = WebSocketManager()
    yield manager
    
    # Clean up
    WebSocketManager._instance = None


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket"""
    return MockWebSocket()


@pytest.fixture
def connected_websocket():
    """Create a connected mock WebSocket"""
    ws = MockWebSocket(WebSocketState.CONNECTED)
    ws.client_state = WebSocketState.CONNECTED
    return ws


@pytest.fixture
def disconnected_websocket():
    """Create a disconnected mock WebSocket"""
    ws = MockWebSocket(WebSocketState.DISCONNECTED)
    ws.client_state = WebSocketState.DISCONNECTED
    return ws