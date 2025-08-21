"""Core_1 Tests - Split from test_websocket_integration.py"""

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


class TestWebSocketCORS:
    """Test WebSocket CORS functionality."""
    
    @pytest.fixture
    def mock_cors_check(self):
        with patch('app.core.websocket_cors.check_cors') as mock:
            yield mock
    
    @pytest.fixture
    def test_client(self):
        return TestClient(app)
    
    def test_cors_allowed_origin(self, mock_cors_check, test_client):
        """Test WebSocket connection with allowed origin."""
        mock_cors_check.return_value = True
        
        cors_handler = get_websocket_cors_handler()
        
        # Test with localhost (should be allowed in development)
        result = cors_handler.is_origin_allowed("http://localhost:3000")
        assert result is True

    def test_cors_blocked_origin(self, test_client):
        """Test WebSocket connection with blocked origin."""
        cors_handler = get_websocket_cors_handler()
        
        # Test with suspicious origin (should be blocked)
        result = cors_handler.is_origin_allowed("http://malicious-site.com")
        assert result is False

    def test_cors_security_violations_tracking(self, test_client):
        """Test CORS security violations are tracked."""
        cors_handler = get_websocket_cors_handler()
        
        # Make several blocked requests
        for _ in range(3):
            cors_handler.is_origin_allowed("http://blocked-site.com")
        
        stats = cors_handler.get_security_stats()
        assert stats["total_violations"] >= 3


class TestSecureWebSocketManager:
    """Test secure WebSocket manager functionality."""
    
    @pytest.fixture
    def valid_jwt_token(self):
        return "valid.jwt.token"
    
    @pytest.fixture  
    def mock_websocket_with_auth(self, valid_jwt_token):
        """Mock WebSocket with authentication headers."""
        class MockWebSocket:
            def __init__(self):
                self.headers = {"authorization": f"Bearer {valid_jwt_token}"}
                self.application_state = "CONNECTED"
                self.sent_messages = []
                self.closed = False
                self.close_code = None
                self.close_reason = None
            
            async def send(self, message):
                self.sent_messages.append(message)
            
            async def close(self, code=1000, reason=""):
                self.closed = True
                self.close_code = code
                self.close_reason = reason
        
        return MockWebSocket()
    
    @pytest.fixture
    def mock_websocket_with_protocol(self, valid_jwt_token):
        """Mock WebSocket with JWT protocol."""
        class MockWebSocket:
            def __init__(self):
                self.headers = {"sec-websocket-protocol": f"jwt.{valid_jwt_token}, chat"}
                self.application_state = "CONNECTED"
                self.sent_messages = []
                self.closed = False
                
            async def send(self, message):
                self.sent_messages.append(message)
                
            async def close(self, code=1000, reason=""):
                self.closed = True
                self.close_code = code
                self.close_reason = reason
        
        return MockWebSocket()
    
    @pytest.fixture
    def mock_websocket_no_auth(self):
        """Mock WebSocket without authentication."""
        class MockWebSocket:
            def __init__(self):
                self.headers = {}
                self.application_state = "CONNECTED"
                self.closed = False
                self.close_code = None
                self.close_reason = None
                
            async def close(self, code=1000, reason=""):
                self.closed = True
                self.close_code = code
                self.close_reason = reason
        
        return MockWebSocket()