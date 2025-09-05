#!/usr/bin/env python3

import asyncio
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.routes.websocket import websocket_endpoint

async def test_websocket_behavior():
    # Set up the same mock as in the test
    mock_websocket = Mock()
    mock_app_state = Mock()
    mock_app_state.agent_supervisor = None
    mock_app_state.thread_service = None
    mock_app_state.startup_complete = True
    mock_websocket.app.state = mock_app_state
    mock_websocket.accept = MagicMock(return_value=None)
    mock_websocket.headers = {"sec-websocket-protocol": ""}

    print("Testing WebSocket endpoint behavior...")
    
    with patch('shared.isolated_environment.get_env') as mock_get_env:
        mock_get_env.return_value = {
            "ENVIRONMENT": "staging",
            "TESTING": "0"
        }
        
        with patch('netra_backend.app.routes.websocket.get_websocket_manager') as mock_ws_manager, \
             patch('netra_backend.app.routes.websocket.get_message_router') as mock_router, \
             patch('netra_backend.app.routes.websocket.get_connection_monitor') as mock_monitor, \
             patch('netra_backend.app.routes.websocket.safe_websocket_send') as mock_send, \
             patch('netra_backend.app.routes.websocket.safe_websocket_close') as mock_close:
            
            # Setup mocks
            mock_ws_manager.return_value = Mock()
            mock_message_router = Mock()
            mock_message_router.add_handler = Mock()
            mock_message_router.handlers = []
            mock_router.return_value = mock_message_router
            mock_monitor.return_value = Mock()
            
            try:
                print("Calling websocket_endpoint...")
                result = await websocket_endpoint(mock_websocket)
                print(f"Result: {result}")
                print("ERROR: Expected RuntimeError but got normal return!")
            except RuntimeError as e:
                print(f"SUCCESS: Got expected RuntimeError: {e}")
            except Exception as e:
                print(f"ERROR: Got unexpected exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_behavior())