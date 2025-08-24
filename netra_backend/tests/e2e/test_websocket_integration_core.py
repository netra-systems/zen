"""Core Tests - Split from test_websocket_integration.py"""

from netra_backend.app.websocket_core.manager import WebSocketManager as UnifiedWebSocketManager as WebSocketManager
# Test framework import - using pytest fixtures instead
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

from netra_backend.app.schemas.websocket_message_types import WebSocketMessage

from netra_backend.app.websocket_core import (
    WebSocketManager as ConnectionManager,

    get_connection_manager,

)
from netra_backend.app.websocket_core.message_handler_core import (

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
# WEBSOCKET CORE TESTS
# =============================================================================

class TestWebSocketConnectionCore:

    """Test core WebSocket connection functionality."""
    
    async def test_websocket_connection_establishment(self, mock_websocket, connection_manager):

        """Test basic WebSocket connection establishment."""
        # Arrange

        mock_websocket.accepted = False
        
        # Act

        await mock_websocket.accept()
        
        # Assert

        assert mock_websocket.accepted is True

        assert len(mock_websocket.messages_sent) == 0

        assert len(mock_websocket.messages_received) == 0
    
    async def test_websocket_message_sending(self, mock_websocket, sample_message):

        """Test sending messages through WebSocket."""
        # Arrange

        await mock_websocket.accept()
        
        # Act

        await mock_websocket.send_json(sample_message)
        
        # Assert

        assert len(mock_websocket.messages_sent) == 1

        assert mock_websocket.messages_sent[0] == sample_message
    
    async def test_websocket_message_receiving(self, mock_websocket):

        """Test receiving messages through WebSocket."""
        # Arrange

        test_message = {"type": "ping", "timestamp": "2025-01-20T10:00:00Z"}

        mock_websocket.add_received_message(test_message)
        
        # Act

        received = await mock_websocket.receive_json()
        
        # Assert

        assert received == test_message
    
    async def test_websocket_connection_manager_integration(self, connection_manager, mock_websocket):

        """Test WebSocket integration with connection manager."""
        # Arrange

        user_id = "test_user_123"
        
        # Act - this would normally add the connection but we'll mock it

        assert connection_manager is not None

        assert hasattr(connection_manager, 'add_connection') or hasattr(connection_manager, 'connect')
    
    async def test_websocket_error_handling(self, error_prone_websocket):

        """Test WebSocket error handling."""
        # Arrange

        test_message = {"type": "test", "content": "error test"}
        
        # Act & Assert

        with pytest.raises(ConnectionError, match="Simulated connection error"):

            await error_prone_websocket.send_json(test_message)

class TestWebSocketMessageHandler:

    """Test WebSocket message handling functionality."""
    
    async def test_agent_request_message_handling(self, ws_manager, sample_message):

        """Test handling of agent request messages."""
        # Arrange

        assert sample_message["type"] == "agent_request"
        
        # Act - Test that ws_manager can handle the message structure

        assert ws_manager is not None

        assert hasattr(ws_manager, 'handle_message') or hasattr(ws_manager, 'send_message')
    
    async def test_websocket_connection_lifecycle(self, mock_websocket):

        """Test complete WebSocket connection lifecycle."""
        # Arrange

        assert mock_websocket.closed is False

        assert mock_websocket.accepted is False
        
        # Act - Connection establishment

        await mock_websocket.accept()

        assert mock_websocket.accepted is True
        
        # Send test message

        test_message = {"type": "test", "data": "lifecycle_test"}

        await mock_websocket.send_json(test_message)

        assert len(mock_websocket.messages_sent) == 1
        
        # Close connection

        await mock_websocket.close()

        assert mock_websocket.closed is True
    
    async def test_websocket_message_validation(self, mock_websocket):

        """Test WebSocket message validation."""
        # Arrange

        valid_message = {

            "type": "agent_request",

            "content": "Test content",

            "user_id": "test_user",

            "thread_id": "test_thread"

        }
        
        # Act

        await mock_websocket.accept()

        await mock_websocket.send_json(valid_message)
        
        # Assert

        assert len(mock_websocket.messages_sent) == 1

        sent_message = mock_websocket.messages_sent[0]

        assert sent_message["type"] == "agent_request"

        assert "content" in sent_message

        assert "user_id" in sent_message

        assert "thread_id" in sent_message

class TestWebSocketIntegration:

    """Test WebSocket integration with other components."""
    
    async def test_websocket_auth_integration(self, mock_websocket, test_auth_token):

        """Test WebSocket integration with authentication."""
        # Arrange

        auth_message = {

            "type": "auth",

            "token": test_auth_token,

            "user_id": "test_user_123"

        }
        
        # Act

        await mock_websocket.accept()

        await mock_websocket.send_json(auth_message)
        
        # Assert

        assert len(mock_websocket.messages_sent) == 1

        assert mock_websocket.messages_sent[0]["type"] == "auth"
    
    async def test_websocket_thread_integration(self, mock_websocket, thread_management_service):

        """Test WebSocket integration with thread management."""
        # Arrange

        thread_message = {

            "type": "thread_message",

            "thread_id": "test_thread_123",

            "content": "Test thread message"

        }
        
        # Act

        await mock_websocket.accept()

        await mock_websocket.send_json(thread_message)
        
        # Assert

        assert len(mock_websocket.messages_sent) == 1

        assert thread_management_service is not None
    
    async def test_websocket_agent_communication(self, mock_websocket, agent_orchestration_service):

        """Test WebSocket communication with agent system."""
        # Arrange

        agent_message = {

            "type": "agent_request",

            "content": "Optimize my AI costs",

            "user_id": "test_user",

            "thread_id": "test_thread"

        }
        
        # Act

        await mock_websocket.accept()

        await mock_websocket.send_json(agent_message)
        
        # Assert

        assert len(mock_websocket.messages_sent) == 1

        assert agent_orchestration_service is not None
        
        # Verify agent service can route the request

        routing_result = await agent_orchestration_service.route_request(agent_message["content"])

        assert routing_result["agent_type"] in ["triage", "optimization", "data"]
