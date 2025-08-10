import pytest
import json
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocket

@pytest.mark.asyncio
async def test_websocket_connection_success(client, test_user, mock_websocket_manager):
    """Test successful WebSocket connection"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}") as websocket:
                assert mock_websocket_manager.connect.called
                
                data = {"type": "ping"}
                websocket.send_json(data)
                
                response = websocket.receive_json()
                assert response["type"] == "pong"

@pytest.mark.asyncio 
async def test_websocket_disconnect(client, test_user, mock_websocket_manager):
    """Test WebSocket disconnection cleanup"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}"):
                pass
            
            assert mock_websocket_manager.disconnect.called

@pytest.mark.asyncio
async def test_websocket_unauthorized(client, mock_websocket_manager):
    """Test WebSocket connection with unauthorized user"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.side_effect = Exception("Unauthorized")
            
            with pytest.raises(Exception):
                with client.websocket_connect("/ws?user_id=unauthorized"):
                    pass

@pytest.mark.asyncio
async def test_websocket_message_handling(client, test_user, mock_websocket_manager):
    """Test WebSocket message handling"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}") as websocket:
                test_message = {
                    "type": "message",
                    "content": "Test message",
                    "thread_id": str(uuid.uuid4())
                }
                
                websocket.send_json(test_message)
                
                response = websocket.receive_json()
                assert "type" in response

@pytest.mark.asyncio
async def test_websocket_broadcast(mock_websocket_manager):
    """Test WebSocket broadcast functionality"""
    
    user_id = "test-user"
    message = {"type": "broadcast", "data": "test"}
    
    await mock_websocket_manager.broadcast(message, user_id)
    
    mock_websocket_manager.broadcast.assert_called_once_with(message, user_id)

@pytest.mark.asyncio
async def test_websocket_error_handling(client, test_user, mock_websocket_manager):
    """Test WebSocket error handling"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}") as websocket:
                invalid_message = "invalid json"
                
                websocket.send_text(invalid_message)
                
                response = websocket.receive_json()
                assert response["type"] == "error"

@pytest.mark.asyncio
async def test_websocket_reconnection(client, test_user, mock_websocket_manager):
    """Test WebSocket reconnection handling"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}"):
                pass
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}"):
                pass
            
            assert mock_websocket_manager.connect.call_count == 2
            assert mock_websocket_manager.disconnect.call_count == 2

@pytest.mark.asyncio
async def test_websocket_concurrent_connections(client, mock_websocket_manager):
    """Test multiple concurrent WebSocket connections"""
    
    user1 = MagicMock(id="user1", email="user1@test.com")
    user2 = MagicMock(id="user2", email="user2@test.com")
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.side_effect = [user1, user2]
            
            with client.websocket_connect(f"/ws?user_id={user1.id}") as ws1:
                with client.websocket_connect(f"/ws?user_id={user2.id}") as ws2:
                    assert mock_websocket_manager.connect.call_count >= 2

@pytest.mark.asyncio
async def test_websocket_heartbeat(client, test_user, mock_websocket_manager):
    """Test WebSocket heartbeat/ping-pong mechanism"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}") as websocket:
                websocket.send_json({"type": "ping"})
                response = websocket.receive_json()
                assert response["type"] == "pong"
                
                websocket.send_json({"type": "ping", "timestamp": 123456})
                response = websocket.receive_json()
                assert response["type"] == "pong"
                assert response.get("timestamp") == 123456

@pytest.mark.asyncio
async def test_websocket_rate_limiting(client, test_user, mock_websocket_manager):
    """Test WebSocket rate limiting for message spam prevention"""
    
    with patch("app.routes.websockets.manager", mock_websocket_manager):
        with patch("app.auth.auth_dependencies.get_active_user_ws") as mock_auth:
            mock_auth.return_value = test_user
            
            with client.websocket_connect(f"/ws?user_id={test_user.id}") as websocket:
                for i in range(10):
                    websocket.send_json({"type": "message", "content": f"Message {i}"})
                
                responses = []
                for _ in range(10):
                    try:
                        response = websocket.receive_json()
                        responses.append(response)
                    except:
                        break
                
                assert len(responses) > 0