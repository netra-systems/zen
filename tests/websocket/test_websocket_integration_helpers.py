"""Utilities Tests - Split from test_websocket_integration.py"""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.websocket_cors import get_websocket_cors_handler
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.main import app
from netra_backend.app.routes.websocket_unified import (
    UNIFIED_WEBSOCKET_CONFIG,
)
# SECURITY FIX: Use factory pattern instead of singleton
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, Optional
import asyncio
import json
import pytest
import time
import websockets
from shared.isolated_environment import IsolatedEnvironment

# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

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
        
        # MockWebSocket class removed - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"