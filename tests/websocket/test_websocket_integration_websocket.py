"""Websocket Tests - Split from test_websocket_integration.py"""

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
from netra_backend.app.main import app
from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.core.websocket_cors import get_websocket_cors_handler
from netra_backend.app.routes.websocket_secure import SecureWebSocketManager
from fastapi import HTTPException
from netra_backend.app.routes.websocket_secure import SecureWebSocketManager, SECURE_WEBSOCKET_CONFIG
from netra_backend.app.routes.websocket_secure import get_secure_websocket_manager

def test_client():
    """Test client for FastAPI application."""
    return TestClient(app)

def test_client():
    """Test client for FastAPI application."""
    return TestClient(app)

    def test_secure_websocket_config_endpoint(self, test_client):
        """Test secure WebSocket configuration endpoint."""
        response = test_client.get("/ws/secure/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "websocket_config" in data
        config = data["websocket_config"]
        
        assert config["version"] == "2.0"
        assert config["security_level"] == "enterprise"
        assert config["features"]["secure_auth"] is True
        assert config["features"]["header_based_jwt"] is True
        assert config["features"]["cors_validation"] is True
        assert "limits" in config

    def test_secure_websocket_health_endpoint(self, test_client):
        """Test secure WebSocket health check endpoint."""
        response = test_client.get("/ws/secure/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "secure_websocket"
        assert data["version"] == "2.0"
        assert data["security_level"] == "enterprise"
        assert "timestamp" in data
        assert "cors_stats" in data
