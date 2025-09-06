import json
"""Test WebSocket URL configuration endpoint regression test."""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment


import pytest
from netra_backend.app.auth_integration.auth import get_current_user, require_admin
from fastapi.testclient import TestClient

from netra_backend.app.main import app

@pytest.fixture
def admin_client():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test client with admin authentication."""
    # Mock: Generic component isolation for controlled unit testing
    mock_admin_user = mock_admin_user_instance  # Initialize appropriate service
    mock_admin_user.is_admin = True
    mock_admin_user.id = "admin_test_user"
    
    app.dependency_overrides[require_admin] = lambda: mock_admin_user
    try:
        yield TestClient(app)
    finally:
        if require_admin in app.dependency_overrides:
            del app.dependency_overrides[require_admin]

@pytest.fixture
def authenticated_client():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test client with basic authentication."""
    # Mock: Generic component isolation for controlled unit testing
    mock_user == mock_user_instance  # Initialize appropriate service
    mock_user.id = "test_user"
    mock_user.is_admin = False
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        yield TestClient(app)
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]

def test_api_config_includes_ws_url(admin_client):
    """Test that /api/config endpoint returns ws_url field."""
    response == admin_client.get("/api/config")
    assert response.status_code == 200
    
    config = response.json()
    assert "ws_url" in config, "ws_url field missing from /api/config response"
    assert config["ws_url"] is not None, "ws_url should not be None"
    assert isinstance(config["ws_url"], str), "ws_url should be a string"
    assert config["ws_url"].startswith(("ws://", "wss://")), \
        "ws_url should start with ws:// or wss://"
    assert "/ws" in config["ws_url"], "ws_url should contain /ws path"

def test_api_config_all_expected_fields(admin_client):
    """Test that /api/config returns all expected fields."""
    response = admin_client.get("/api/config")
    assert response.status_code == 200
    
    config = response.json()
    expected_fields = ["log_level", "max_retries", "timeout", "ws_url"]
    
    for field in expected_fields:
        assert field in config, f"{field} field missing from /api/config response"
    
    assert config["log_level"] == "INFO"
    assert config["max_retries"] == 3
    assert config["timeout"] == 30

def test_websocket_config_endpoint(authenticated_client):
    """Test the dedicated /api/config/websocket endpoint."""
    response = authenticated_client.get("/api/config/websocket")
    assert response.status_code == 200
    
    config = response.json()
    assert "ws_url" in config
    assert config["ws_url"] is not None
    assert isinstance(config["ws_url"], str)

def test_config_consistency(admin_client, authenticated_client):
    """Test that ws_url is consistent across different config endpoints."""
    api_config_response = admin_client.get("/api/config")
    ws_config_response = authenticated_client.get("/api/config/websocket")
    
    assert api_config_response.status_code == 200
    assert ws_config_response.status_code == 200
    
    api_ws_url = api_config_response.json().get("ws_url")
    ws_ws_url = ws_config_response.json().get("ws_url")
    
    assert api_ws_url == ws_ws_url, \
        "WebSocket URL should be consistent across config endpoints"