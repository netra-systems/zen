"""
Shared fixtures and configuration for WebSocketManager comprehensive tests
"""

import pytest
import asyncio
import time
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from starlette.websockets import WebSocketState

from app.ws_manager import WebSocketManager, ConnectionInfo, manager, ws_manager


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
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def disconnected_websocket():
    """Create a disconnected mock WebSocket"""
    ws = MockWebSocket(WebSocketState.DISCONNECTED)
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws