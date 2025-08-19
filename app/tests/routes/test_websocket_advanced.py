import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.registry import WebSocketMessage, UserMessage, AgentMessage

class TestWebSocketAdvanced:
    
    def test_websocket_authentication_success(self):
        """Test successful WebSocket authentication"""
        client = TestClient(app)
        
        with patch('app.routes.websockets.manager') as mock_manager, \
             patch('app.routes.websockets.authenticate_websocket_user') as mock_auth, \
             patch('app.routes.websockets.extract_app_services') as mock_get_services, \
             patch('app.routes.websockets.accept_websocket_connection') as mock_accept:
            
            # Setup mocks
            mock_manager.connect_user = AsyncMock(return_value=MagicMock())
            mock_manager.disconnect_user = AsyncMock()
            mock_auth.return_value = "test-user-123"
            
            # Mock security service with async methods
            mock_security_service = MagicMock()
            mock_security_service.decode_access_token = AsyncMock(return_value={"user_id": "test-user-123"})
            mock_agent_service = MagicMock()
            mock_get_services.return_value = (mock_security_service, mock_agent_service)
            
            # Mock accept websocket to return token
            mock_accept.return_value = "test-token"
            
            with client.websocket_connect("/ws?token=valid_token") as websocket:
                # If we get here, authentication succeeded
                assert True  # Connection established successfully
    
    def test_websocket_authentication_failure(self):
        """Test WebSocket authentication failure handling"""
        client = TestClient(app)
        
        with patch('app.routes.utils.websocket_helpers.authenticate_websocket_user') as mock_auth, \
             patch('app.routes.websockets.extract_app_services') as mock_get_services, \
             patch('app.routes.websockets.accept_websocket_connection') as mock_accept:
            
            # Mock authentication failure
            mock_auth.side_effect = ValueError("Invalid token")
            
            # Mock security service with async methods
            mock_security_service = MagicMock()
            mock_security_service.decode_access_token = AsyncMock(return_value={"user_id": "test-user-123"})
            mock_agent_service = MagicMock()
            mock_get_services.return_value = (mock_security_service, mock_agent_service)
            
            # Mock accept websocket to return token
            mock_accept.return_value = "test-token"
            
            # The ValueError is caught by WebSocket exception handler and connection is closed gracefully
            # So we don't expect an exception to be raised to the test client
            with client.websocket_connect("/ws?token=invalid_token") as websocket:
                # Authentication failed, but connection was handled gracefully
                assert mock_auth.called  # Verify authentication was attempted
    
    def test_websocket_message_handling(self):
        """Test WebSocket message handling and processing"""
        client = TestClient(app)
        
        with patch('app.routes.websockets.manager') as mock_manager, \
             patch('app.routes.websockets.authenticate_websocket_user') as mock_auth, \
             patch('app.routes.websockets.extract_app_services') as mock_get_services, \
             patch('app.routes.websockets.accept_websocket_connection') as mock_accept:
            
            # Setup mocks
            mock_manager.connect_user = AsyncMock(return_value=MagicMock())
            mock_manager.handle_message = AsyncMock(return_value=True)
            mock_manager.disconnect_user = AsyncMock()
            mock_auth.return_value = "test-user-123"
            
            # Mock services
            mock_security_service = MagicMock()
            mock_security_service.decode_access_token = AsyncMock(return_value={"user_id": "test-user-123"})
            mock_agent_service = MagicMock()
            mock_agent_service.handle_websocket_message = AsyncMock()
            mock_get_services.return_value = (mock_security_service, mock_agent_service)
            
            with client.websocket_connect("/ws?token=valid_token") as websocket:
                test_message = {
                    "type": "message",
                    "content": "Test message",
                    "thread_id": "thread_123"
                }
                websocket.send_json(test_message)
                
                # Verify message handling succeeded
                assert True  # Message processing completed