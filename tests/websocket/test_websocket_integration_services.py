"""Services Tests - Split from test_websocket_integration.py"""

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


class TestWebSocketServices:
    """Test WebSocket service endpoints."""
    
    @pytest.fixture
    def test_client(self):
        """Test client for FastAPI application."""
        return TestClient(app)
    
    def test_secure_websocket_config_endpoint(self, test_client):
        """Test secure WebSocket configuration endpoint."""
        response = test_client.get("/ws/secure/config")
        
        assert response.status_code == 200
        config = response.json()
        assert "max_connections" in config
        assert "timeout" in config
        assert "cors_enabled" in config
    
    def test_websocket_health_check(self, test_client):
        """Test WebSocket service health check."""
        response = test_client.get("/ws/health")
        
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"
        assert "active_connections" in health
    
    @pytest.mark.asyncio
    async def test_websocket_manager_instance(self):
        """Test WebSocket manager singleton instance."""
        manager1 = get_secure_websocket_manager()
        manager2 = get_secure_websocket_manager()
        
        assert manager1 is manager2  # Should be the same instance
    
    def test_cors_handler_instance(self):
        """Test CORS handler singleton instance."""
        handler1 = get_websocket_cors_handler()
        handler2 = get_websocket_cors_handler()
        
        assert handler1 is handler2  # Should be the same instance