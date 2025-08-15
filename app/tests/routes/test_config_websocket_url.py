"""Test WebSocket URL configuration endpoint regression test."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_config_includes_ws_url():
    """Test that /api/config endpoint returns ws_url field."""
    response = client.get("/api/config")
    assert response.status_code == 200
    
    config = response.json()
    assert "ws_url" in config, "ws_url field missing from /api/config response"
    assert config["ws_url"] is not None, "ws_url should not be None"
    assert isinstance(config["ws_url"], str), "ws_url should be a string"
    assert config["ws_url"].startswith(("ws://", "wss://")), \
        "ws_url should start with ws:// or wss://"
    assert "/ws" in config["ws_url"], "ws_url should contain /ws path"

def test_api_config_all_expected_fields():
    """Test that /api/config returns all expected fields."""
    response = client.get("/api/config")
    assert response.status_code == 200
    
    config = response.json()
    expected_fields = ["log_level", "max_retries", "timeout", "ws_url"]
    
    for field in expected_fields:
        assert field in config, f"{field} field missing from /api/config response"
    
    assert config["log_level"] == "INFO"
    assert config["max_retries"] == 3
    assert config["timeout"] == 30

def test_websocket_config_endpoint():
    """Test the dedicated /api/config/websocket endpoint."""
    response = client.get("/api/config/websocket")
    assert response.status_code == 200
    
    config = response.json()
    assert "ws_url" in config
    assert config["ws_url"] is not None
    assert isinstance(config["ws_url"], str)

def test_config_consistency():
    """Test that ws_url is consistent across different config endpoints."""
    api_config_response = client.get("/api/config")
    ws_config_response = client.get("/api/config/websocket")
    
    assert api_config_response.status_code == 200
    assert ws_config_response.status_code == 200
    
    api_ws_url = api_config_response.json().get("ws_url")
    ws_ws_url = ws_config_response.json().get("ws_url")
    
    assert api_ws_url == ws_ws_url, \
        "WebSocket URL should be consistent across config endpoints"