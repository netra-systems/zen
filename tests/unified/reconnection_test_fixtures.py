"""WebSocket Reconnection Test Fixtures

Centralized test fixtures and utilities for reconnection testing scenarios.
Supports state preservation, token management, and connection lifecycle testing.

Business Value: Enables comprehensive reconnection testing for enterprise reliability
"""

import asyncio
import time
from datetime import datetime, UTC
from typing import Dict, List, Any
from unittest.mock import MagicMock
import pytest

# Import test utilities with fallback mocks
try:
    from netra_backend.app.tests.test_utilities.auth_test_helpers import create_test_token
except ImportError:
    def create_test_token(user_id: str, exp_offset: int = 3600) -> str:
        return f"mock_token_{user_id}_{exp_offset}"

try:
    from netra_backend.app.tests.test_utilities.websocket_mocks import MockWebSocket, WebSocketBuilder
except ImportError:
    # Fallback mock implementations
    class MockWebSocket:
        def __init__(self, user_id: str = None):
            self.user_id = user_id or "test_user"
            self.connection_id = f"conn_{int(time.time() * 1000)}"
            self.state = "connected"
            self.sent_messages = []
            self.is_authenticated = True
            self.auth_token = f"token_{self.user_id}"
            
        async def accept(self): pass
        async def send_json(self, data: Dict[str, Any]): 
            self.sent_messages.append(data)
        async def close(self, code: int = 1000, reason: str = "Normal closure"): 
            self.state = "disconnected"
    
    class WebSocketBuilder:
        def __init__(self):
            self._websocket = MockWebSocket()
        def with_user_id(self, user_id: str): 
            self._websocket.user_id = user_id
            return self
        def with_authentication(self, token: str = None): 
            self._websocket.auth_token = token
            return self
        def build(self): 
            return self._websocket


class ReconnectionTestFixture:
    """Centralized fixture for reconnection testing scenarios."""
    
    def __init__(self):
        self.connection_manager = MagicMock()  # Mock connection manager
        self.active_connections: List[MockWebSocket] = []
        self.reconnection_attempts: List[Dict[str, Any]] = []
        self.preserved_state: Dict[str, Any] = {}
        
    def create_connection_with_state(self, user_id: str) -> MockWebSocket:
        """Create WebSocket connection with preserved state."""
        token = create_test_token(user_id)
        websocket = WebSocketBuilder().with_user_id(user_id).with_authentication(token).build()
        self.active_connections.append(websocket)
        return websocket
    
    def record_reconnection_attempt(self, connection_id: str, success: bool, reason: str) -> None:
        """Record reconnection attempt for analysis."""
        attempt = {
            "connection_id": connection_id,
            "success": success,
            "reason": reason,
            "timestamp": datetime.now(UTC),
            "attempt_number": len(self.reconnection_attempts) + 1
        }
        self.reconnection_attempts.append(attempt)


@pytest.fixture
def reconnection_fixture():
    """Create reconnection test fixture with cleanup."""
    fixture = ReconnectionTestFixture()
    return fixture