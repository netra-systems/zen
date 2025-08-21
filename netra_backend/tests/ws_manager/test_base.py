"""
Base fixtures and utilities for WebSocketManager tests
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from starlette.websockets import WebSocketState

from netra_backend.app.services.websocket.ws_manager import WebSocketManager, ConnectionInfo


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


class WebSocketTestBase:
    """Base class with common test utilities"""
    
    @staticmethod
    def create_connection_info(connection_id: str = "test-123") -> ConnectionInfo:
        """Create a test ConnectionInfo object"""
        return ConnectionInfo(
            connection_id=connection_id,
            connected_at=datetime.now(timezone.utc),
            user_id="user-456",
            role="user",
            metadata={"test": True}
        )
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout: float = 1.0, interval: float = 0.01):
        """Wait for a condition to become true"""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)
        return False
    
    @staticmethod
    def assert_message_sent(websocket: MockWebSocket, expected_type: str):
        """Assert that a message of the given type was sent"""
        assert websocket.send_json.called
        last_call = websocket.send_json.call_args_list[-1]
        message = last_call[0][0] if last_call[0] else last_call[1].get("data", {})
        assert message.get("type") == expected_type
        return message
    
    @staticmethod
    def assert_no_message_sent(websocket: MockWebSocket):
        """Assert that no message was sent"""
        assert not websocket.send_json.called
    
    @staticmethod
    def reset_manager_singleton():
        """Reset the WebSocketManager singleton for testing"""
        WebSocketManager._instance = None
        WebSocketManager._initialized = False