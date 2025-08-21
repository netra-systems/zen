"""Fixtures Tests - Split from test_websocket_integration.py"""

import asyncio
import json
import pytest
import websockets
import httpx
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.websocket.connection_manager import get_connection_manager, ModernConnectionManager
from app.websocket.message_handler_core import ModernReliableMessageHandler
from app.ws_manager import WebSocketManager
from app.auth_integration.auth import validate_token_jwt
from app.schemas.websocket_message_types import WebSocketMessage
from app.routes.mcp.main import websocket_endpoint
from app.tests.services.test_ws_connection_mocks import MockWebSocket


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def mock_websocket(self) -> MockWebSocket:
        """Create mock WebSocket for testing."""
        return MockWebSocket()

    def connection_manager(self) -> ModernConnectionManager:
        """Create connection manager for testing."""
        return get_connection_manager()

    def ws_manager(self) -> WebSocketManager:
        """Create WebSocket manager for testing."""
        return WebSocketManager()

    def sample_message(self) -> Dict[str, Any]:
        """Create sample WebSocket message."""
        return {
            "type": "agent_request",
            "content": "What is the status of my optimization project?",
            "thread_id": "thread_123",
            "user_id": "user_123"
        }

    def error_prone_websocket(self) -> MockWebSocket:
        """Create WebSocket that simulates errors."""
        mock_ws = MockWebSocket()
        
        # Override send_json to simulate errors
        async def error_send_json(data):
            raise ConnectionError("Simulated connection error")
        
        mock_ws.send_json = error_send_json
        return mock_ws
