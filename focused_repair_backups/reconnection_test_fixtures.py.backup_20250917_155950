class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

        '''WebSocket Reconnection Test Fixtures

        Centralized test fixtures and utilities for reconnection testing scenarios.
        Supports state preservation, token management, and connection lifecycle testing.

        Business Value: Enables comprehensive reconnection testing for enterprise reliability
        '''

        import asyncio
        import time
        from datetime import UTC, datetime
        from typing import Any, Dict, List

        import pytest

    # Import required test utilities - no fallbacks
        from test_framework.helpers.auth_helpers import ( )
        get_test_token,
    
        from netra_backend.tests.helpers.websocket_test_helpers import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        MockWebSocket,
        create_mock_websocket,
    


class ReconnectionTestFixture:
        """Centralized fixture for reconnection testing scenarios."""

    def __init__(self):
    # Mock: Generic component isolation for controlled unit testing
        self.connection_manager = Magic        self.active_connections: List[MockWebSocket] = []
        self.reconnection_attempts: List[Dict[str, Any]] = []
        self.preserved_state: Dict[str, Any] = {}

    async def create_connection_with_state(self, user_id: str) -> MockWebSocket:
        """Create WebSocket connection with preserved state."""
        token = await get_test_token(user_id)
        websocket = create_mock_websocket().with_user_id(user_id).with_authentication(token).build()
        self.active_connections.append(websocket)
        return websocket

    def record_reconnection_attempt(self, connection_id: str, success: bool, reason: str) -> None:
        """Record reconnection attempt for analysis."""
        attempt = { )
        "connection_id": connection_id,
        "success": success,
        "reason": reason,
        "timestamp": datetime.now(UTC),
        "attempt_number": len(self.reconnection_attempts) + 1
    
        self.reconnection_attempts.append(attempt)


        @pytest.fixture
    def reconnection_fixture():
        """Create reconnection test fixture with cleanup."""
        fixture = ReconnectionTestFixture()
        return fixture
