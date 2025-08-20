"""Fixtures Tests - Split from test_websocket_integration.py"""

import asyncio
import json
import pytest
import websockets
import time
from typing import Dict, Any
from unittest.mock import patch, AsyncMock
from test_framework.mock_utils import mock_justified
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db.postgres import get_async_db
from app.clients.auth_client import auth_client
from app.core.websocket_cors import get_websocket_cors_handler
from app.routes.websocket_secure import (
    SecureWebSocketManager,
    SECURE_WEBSOCKET_CONFIG,
    get_secure_websocket_manager
)
from fastapi import HTTPException


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