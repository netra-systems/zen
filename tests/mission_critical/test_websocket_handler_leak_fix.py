"""
Test to verify WebSocket handler accumulation fix

This test ensures that handlers don't accumulate when multiple WebSocket
connections are created and closed.
"""

import asyncio
import json
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.routes.websocket import websocket_endpoint
from netra_backend.app.websocket_core import get_message_router


@pytest.mark.asyncio
async def test_no_handler_accumulation():
    """Test that handlers don't accumulate when connections are made."""
    
    # Get the message router instance
    message_router = get_message_router()
    
    # Record initial handler count
    initial_count = len(message_router.handlers)
    print(f"Initial handler count: {initial_count}")
    
    # Simulate multiple WebSocket connections
    for i in range(5):
        # Create a mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer mock_token",
            "sec-websocket-protocol": "jwt-auth"
        }
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
        mock_websocket.client_state = MagicMock()
        mock_websocket.client_state.value = 1  # CONNECTED
        mock_websocket.application_state = MagicMock()
        mock_websocket.application_state.value = 1  # CONNECTED
        
        # Mock authentication
        with patch('netra_backend.app.routes.websocket.verify_auth_header') as mock_auth:
            mock_auth.return_value = {"user_id": f"test_user_{i}", "email": f"test{i}@example.com"}
            
            # Mock other dependencies
            with patch('netra_backend.app.routes.websocket.get_agent_supervisor') as mock_supervisor:
                mock_supervisor.return_value = Mock()
                
                with patch('netra_backend.app.routes.websocket.get_thread_service') as mock_thread_service:
                    mock_thread_service.return_value = Mock()
                    
                    # Try to handle the WebSocket (it will fail quickly but should register handlers)
                    try:
                        await websocket_endpoint(mock_websocket)
                    except:
                        pass  # Expected to fail, we just want to trigger handler registration
        
        # Check handler count after each connection
        current_count = len(message_router.handlers)
        print(f"Handler count after connection {i+1}: {current_count}")
    
    # Final handler count should not have grown significantly
    final_count = len(message_router.handlers)
    
    # The count should increase by at most 1 (for the shared AgentMessageHandler)
    # not by 5 (one per connection)
    assert final_count - initial_count <= 1, \
        f"Handler leak detected! Initial: {initial_count}, Final: {final_count}, Expected increase: <=1"
    
    print(f"✓ Test passed! Handler count only increased by {final_count - initial_count}")


@pytest.mark.asyncio
async def test_handler_reuse():
    """Test that existing handlers are reused instead of creating new ones."""
    
    # Get the message router instance  
    message_router = get_message_router()
    
    # Find any existing AgentMessageHandler
    initial_agent_handler = None
    for handler in message_router.handlers:
        if handler.__class__.__name__ == 'AgentMessageHandler':
            initial_agent_handler = handler
            break
    
    # Create first mock WebSocket connection
    mock_ws1 = AsyncMock(spec=WebSocket)
    mock_ws1.headers = {"authorization": "Bearer mock_token"}
    mock_ws1.accept = AsyncMock()
    mock_ws1.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
    mock_ws1.client_state = MagicMock()
    mock_ws1.client_state.value = 1
    mock_ws1.application_state = MagicMock()
    mock_ws1.application_state.value = 1
    
    with patch('netra_backend.app.routes.websocket.verify_auth_header') as mock_auth:
        mock_auth.return_value = {"user_id": "user1", "email": "user1@example.com"}
        
        with patch('netra_backend.app.routes.websocket.get_agent_supervisor') as mock_supervisor:
            mock_supervisor.return_value = Mock()
            
            with patch('netra_backend.app.routes.websocket.get_thread_service') as mock_thread_service:
                mock_thread_service.return_value = Mock()
                
                try:
                    await websocket_endpoint(mock_ws1)
                except:
                    pass
    
    # Find AgentMessageHandler after first connection
    first_agent_handler = None
    for handler in message_router.handlers:
        if handler.__class__.__name__ == 'AgentMessageHandler':
            first_agent_handler = handler
            break
    
    # Create second mock WebSocket connection
    mock_ws2 = AsyncMock(spec=WebSocket)
    mock_ws2.headers = {"authorization": "Bearer mock_token"}
    mock_ws2.accept = AsyncMock()
    mock_ws2.receive_text = AsyncMock(side_effect=Exception("Connection closed"))
    mock_ws2.client_state = MagicMock()
    mock_ws2.client_state.value = 1
    mock_ws2.application_state = MagicMock()
    mock_ws2.application_state.value = 1
    
    with patch('netra_backend.app.routes.websocket.verify_auth_header') as mock_auth:
        mock_auth.return_value = {"user_id": "user2", "email": "user2@example.com"}
        
        with patch('netra_backend.app.routes.websocket.get_agent_supervisor') as mock_supervisor:
            mock_supervisor.return_value = Mock()
            
            with patch('netra_backend.app.routes.websocket.get_thread_service') as mock_thread_service:
                mock_thread_service.return_value = Mock()
                
                try:
                    await websocket_endpoint(mock_ws2)
                except:
                    pass
    
    # Find AgentMessageHandler after second connection
    second_agent_handler = None
    agent_handler_count = 0
    for handler in message_router.handlers:
        if handler.__class__.__name__ == 'AgentMessageHandler':
            second_agent_handler = handler
            agent_handler_count += 1
    
    # There should only be ONE AgentMessageHandler
    assert agent_handler_count <= 1, \
        f"Multiple AgentMessageHandlers found! Count: {agent_handler_count}"
    
    # If we had an initial handler, it should be the same object (reused)
    if initial_agent_handler and first_agent_handler:
        assert first_agent_handler is initial_agent_handler, \
            "AgentMessageHandler was replaced instead of reused"
    
    # The handler from first and second connections should be the same
    if first_agent_handler and second_agent_handler:
        assert first_agent_handler is second_agent_handler, \
            "New AgentMessageHandler created instead of reusing existing"
    
    print("✓ Handler reuse test passed!")


if __name__ == "__main__":
    asyncio.run(test_no_handler_accumulation())
    asyncio.run(test_handler_reuse())
    print("\n✓ All WebSocket handler leak tests passed!")