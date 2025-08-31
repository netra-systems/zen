"""Fixtures Tests - Split from test_websocket_integration.py"""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.websocket_cors import get_websocket_cors_handler
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.main import app
from netra_backend.app.routes.websocket_unified import (
    UNIFIED_WEBSOCKET_CONFIG,
)
from netra_backend.app.websocket_core import get_websocket_manager, WebSocketManager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict
from unittest.mock import AsyncMock, patch
import asyncio
import json
import pytest
import time
import websockets

# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

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

    # Mock: Database session isolation for transaction testing without real database dependency
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
    return get_websocket_manager()
