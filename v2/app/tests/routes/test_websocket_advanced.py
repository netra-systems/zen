import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.WebSocket import MessageRequest, MessageResponse, ConnectionStatus

@pytest.mark.asyncio
async def test_websocket_authentication_success():
    with TestClient(app) as client:
        with patch('app.routes.websockets.verify_token', return_value={'user_id': 'test_user'}):
            with client.websocket_connect("/ws?token=valid_token") as websocket:
                data = websocket.receive_json()
                assert data['type'] == 'connection'
                assert data['status'] == 'connected'

@pytest.mark.asyncio  
async def test_websocket_authentication_failure():
    with TestClient(app) as client:
        with patch('app.routes.websockets.verify_token', return_value=None):
            with pytest.raises(Exception):
                with client.websocket_connect("/ws?token=invalid_token") as websocket:
                    pass

@pytest.mark.asyncio
async def test_websocket_message_handling():
    with TestClient(app) as client:
        with patch('app.routes.websockets.verify_token', return_value={'user_id': 'test_user'}):
            with patch('app.routes.websockets.handle_message', new_callable=AsyncMock) as mock_handler:
                mock_handler.return_value = MessageResponse(
                    type='response',
                    content='Test response',
                    thread_id='thread_123'
                )
                
                with client.websocket_connect("/ws?token=valid_token") as websocket:
                    websocket.send_json({
                        'type': 'message',
                        'content': 'Test message',
                        'thread_id': 'thread_123'
                    })
                    
                    response = websocket.receive_json()
                    assert response['type'] == 'response'
                    assert response['content'] == 'Test response'