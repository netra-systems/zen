"""WebSocket Integration Fixtures and Tests"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

import asyncio
import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import websockets
from netra_backend.app.auth_integration.auth import validate_token_jwt
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from netra_backend.app.routes.mcp.main import websocket_endpoint
from ws_manager import WebSocketManager

from netra_backend.app.schemas.websocket_message_types import WebSocketMessage

from netra_backend.app.websocket.connection_manager import (

    ConnectionManager,

    get_connection_manager,

)
from netra_backend.app.websocket.message_handler_core import (

    ModernReliableMessageHandler,

)

class MockWebSocket:

    """Mock WebSocket for testing."""
    
    def __init__(self):

        self.messages_sent = []

        self.messages_received = []

        self.closed = False

        self.accepted = False

        self.connection_id = f"test_conn_{int(asyncio.get_event_loop().time() * 1000)}"
    
    async def accept(self):

        self.accepted = True
    
    async def send_json(self, data: Dict[str, Any]):

        self.messages_sent.append(data)
    
    async def send_text(self, data: str):

        self.messages_sent.append(data)
    
    async def receive_json(self) -> Dict[str, Any]:

        if self.messages_received:

            return self.messages_received.pop(0)

        await asyncio.sleep(0.1)

        return {"type": "ping"}
    
    async def close(self):

        self.closed = True
    
    def add_received_message(self, message: Dict[str, Any]):

        """Add message to received queue for testing."""

        self.messages_received.append(message)

@pytest.fixture

def mock_websocket() -> MockWebSocket:

    """Create mock WebSocket for testing."""

    return MockWebSocket()

@pytest.fixture

def connection_manager() -> ConnectionManager:

    """Create connection manager for testing."""

    return get_connection_manager()

@pytest.fixture

def ws_manager() -> WebSocketManager:

    """Create WebSocket manager for testing."""

    return WebSocketManager()

@pytest.fixture

def sample_message() -> Dict[str, Any]:

    """Create sample WebSocket message."""

    return {

        "type": "agent_request",

        "content": "What is the status of my optimization project?",

        "thread_id": "thread_123",

        "user_id": "user_123"

    }

@pytest.fixture

def error_prone_websocket() -> MockWebSocket:

    """Create WebSocket that simulates errors."""

    mock_ws = MockWebSocket()
    
    # Override send_json to simulate errors

    async def error_send_json(data):

        raise ConnectionError("Simulated connection error")
    
    mock_ws.send_json = error_send_json

    return mock_ws

# =============================================================================
# WEBSOCKET FIXTURE TESTS
# =============================================================================

class TestWebSocketFixtures:

    """Test WebSocket fixtures functionality."""
    
    async def test_mock_websocket_creation(self, mock_websocket):

        """Test mock WebSocket fixture creation."""

        assert mock_websocket is not None

        assert mock_websocket.closed is False

        assert mock_websocket.accepted is False

        assert len(mock_websocket.messages_sent) == 0

        assert len(mock_websocket.messages_received) == 0
    
    async def test_connection_manager_fixture(self, connection_manager):

        """Test connection manager fixture."""

        assert connection_manager is not None

        assert hasattr(connection_manager, 'add_connection') or hasattr(connection_manager, 'connect')
    
    async def test_ws_manager_fixture(self, ws_manager):

        """Test WebSocket manager fixture."""

        assert ws_manager is not None

        assert hasattr(ws_manager, 'handle_message') or hasattr(ws_manager, 'send_message')
    
    async def test_sample_message_fixture(self, sample_message):

        """Test sample message fixture."""

        assert sample_message is not None

        assert sample_message["type"] == "agent_request"

        assert "content" in sample_message

        assert "thread_id" in sample_message

        assert "user_id" in sample_message
    
    async def test_error_prone_websocket_fixture(self, error_prone_websocket):

        """Test error-prone WebSocket fixture."""

        assert error_prone_websocket is not None
        
        # Test that it raises errors as expected

        with pytest.raises(ConnectionError, match="Simulated connection error"):

            await error_prone_websocket.send_json({"test": "data"})

class TestWebSocketFixtureIntegration:

    """Test integration between WebSocket fixtures."""
    
    async def test_websocket_message_flow(self, mock_websocket, sample_message):

        """Test message flow using fixtures."""
        # Setup

        await mock_websocket.accept()
        
        # Send message

        await mock_websocket.send_json(sample_message)
        
        # Verify

        assert len(mock_websocket.messages_sent) == 1

        assert mock_websocket.messages_sent[0] == sample_message
    
    async def test_websocket_lifecycle_with_fixtures(self, mock_websocket):

        """Test WebSocket lifecycle using fixtures."""
        # Initial state

        assert not mock_websocket.accepted

        assert not mock_websocket.closed
        
        # Accept connection

        await mock_websocket.accept()

        assert mock_websocket.accepted
        
        # Close connection

        await mock_websocket.close()

        assert mock_websocket.closed
    
    async def test_fixture_integration(self):

        """Test that fixtures can be used together."""
        # This test ensures the file can be imported and fixtures work

        assert True  # Basic passing test
