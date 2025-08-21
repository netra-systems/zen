"""Fixtures Tests - Split from test_websocket_integration.py"""

import asyncio
import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
import websockets
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.websocket_cors import get_websocket_cors_handler
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.main import app
from netra_backend.app.routes.websocket_secure import (
    SECURE_WEBSOCKET_CONFIG,
    SecureWebSocketManager,
    get_secure_websocket_manager,
)
from test_framework.mock_utils import mock_justified


@pytest.fixture
def test_client():
    """Test client for FastAPI application."""
    return TestClient(app)


@pytest.fixture
def valid_jwt_token():
    """Valid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.signature"


@pytest.fixture
async def mock_async_db_session():
    """Mock async database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    return mock_session


@pytest.fixture
def mock_auth_client():
    """Mock authentication client."""
    with patch.object(auth_client, 'validate_token', new_callable=AsyncMock) as mock:
        mock.return_value = {"user_id": "test_user", "valid": True}
        yield mock


@pytest.fixture
def websocket_cors_handler():
    """WebSocket CORS handler for testing."""
    return get_websocket_cors_handler()


@pytest.fixture
def secure_websocket_manager():
    """Secure WebSocket manager for testing."""
    return get_secure_websocket_manager()