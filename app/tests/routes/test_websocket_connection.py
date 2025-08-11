import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.asyncio
class TestWebSocketConnection:
    
    def test_websocket_connection_success(self):
        """Test successful WebSocket connection establishment"""
        client = TestClient(app)
        
        with patch('app.routes.websockets.websocket_manager') as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = AsyncMock()
            
            with client.websocket_connect("/ws/test-connection-id") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "connection_established"
                assert "connection_id" in data
    
    def test_websocket_message_handling(self):
        """Test WebSocket message handling and routing"""
        client = TestClient(app)
        
        with patch('app.routes.websockets.websocket_manager') as mock_manager:
            mock_manager.send_message = AsyncMock()
            
            with client.websocket_connect("/ws/test-connection-id") as websocket:
                websocket.receive_json()
                
                test_message = {
                    "type": "agent_message",
                    "content": "Test message",
                    "thread_id": "test-thread-123"
                }
                websocket.send_json(test_message)
                
                response = websocket.receive_json()
                assert response != None
    
    def test_websocket_disconnection_cleanup(self):
        """Test proper cleanup on WebSocket disconnection"""
        client = TestClient(app)
        
        with patch('app.routes.websockets.websocket_manager') as mock_manager:
            mock_manager.disconnect = AsyncMock()
            
            with client.websocket_connect("/ws/test-connection-id") as websocket:
                websocket.receive_json()
            
            mock_manager.disconnect.assert_called()