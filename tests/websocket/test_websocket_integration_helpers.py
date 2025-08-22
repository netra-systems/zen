"""Utilities Tests - Split from test_websocket_integration.py"""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.websocket_cors import get_websocket_cors_handler
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.main import app
from netra_backend.app.routes.websocket_secure import (
from netra_backend.app.websocket.connection_manager import ModernModernConnectionManager as WebSocketManager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch
import asyncio
import json
import pytest
import time
import websockets

    SECURE_WEBSOCKET_CONFIG,

    SecureWebSocketManager,

    get_secure_websocket_manager,

)
from test_framework.mock_utils import mock_justified


class WebSocketTestHelpers:

    """Helper utilities for WebSocket testing."""
    

    @staticmethod

    async def create_test_websocket_connection(

        url: str,

        headers: Optional[Dict[str, str]] = None,

        timeout: float = 5.0

    ):

        """Create a test WebSocket connection."""

        try:

            connection = await asyncio.wait_for(

                websockets.connect(url, extra_headers=headers or {}),

                timeout=timeout

            )

            return connection

        except asyncio.TimeoutError:

            raise TimeoutError(f"WebSocket connection to {url} timed out")
    

    @staticmethod

    async def send_and_receive(

        websocket,

        message: Dict[str, Any],

        timeout: float = 5.0

    ) -> Dict[str, Any]:

        """Send a message and receive response."""

        await websocket.send(json.dumps(message))

        response = await asyncio.wait_for(

            websocket.recv(),

            timeout=timeout

        )

        return json.loads(response)
    

    @staticmethod

    def create_mock_websocket(

        with_auth: bool = True,

        jwt_token: str = "test.jwt.token"

    ):

        """Create a mock WebSocket for testing."""

        class MockWebSocket:

            def __init__(self):

                if with_auth:

                    self.headers = {"authorization": f"Bearer {jwt_token}"}

                else:

                    self.headers = {}

                self.application_state = "CONNECTED"

                self.sent_messages = []

                self.closed = False

                self.close_code = None

                self.close_reason = None
            

            async def send(self, message):

                self.sent_messages.append(message)
            

            async def recv(self):

                if self.sent_messages:

                    return self.sent_messages.pop(0)

                raise websockets.exceptions.ConnectionClosed(1000, "Test closed")
            

            async def close(self, code=1000, reason=""):

                self.closed = True

                self.close_code = code

                self.close_reason = reason
        

        return MockWebSocket()
    

    @staticmethod

    def validate_websocket_message(message: Dict[str, Any], expected_type: str):

        """Validate WebSocket message structure."""

        assert "type" in message, "Message missing 'type' field"

        assert message["type"] == expected_type, f"Expected type '{expected_type}', got '{message['type']}'"

        assert "timestamp" in message, "Message missing 'timestamp' field"

        return True