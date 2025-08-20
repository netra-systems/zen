"""Simple WebSocket tests that work with the actual demo endpoint."""
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app


def test_websocket_connection():
    """Test basic WebSocket connection to demo endpoint."""
    client = TestClient(app)
    
    # The demo WebSocket endpoint accepts connections immediately
    with client.websocket_connect("/api/demo/ws") as websocket:
        # Should receive connection established message
        data = websocket.receive_json()
        assert data["type"] == "connection_established"
        assert "session_id" in data
        
        # Send a ping message
        websocket.send_json({"type": "ping"})
        
        # Should receive pong response
        response = websocket.receive_json()
        assert response["type"] == "pong"


def test_websocket_invalid_message_type():
    """Test WebSocket handles invalid message types gracefully."""
    client = TestClient(app)
    
    with client.websocket_connect("/api/demo/ws") as websocket:
        # Receive connection established
        data = websocket.receive_json()
        assert data["type"] == "connection_established"
        
        # Send invalid message type (should be ignored)
        websocket.send_json({"type": "invalid_type", "data": "test"})
        
        # Send valid ping to ensure connection still works
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"