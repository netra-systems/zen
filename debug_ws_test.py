#!/usr/bin/env python3
"""Debug script to test WebSocket manager behavior"""

import asyncio
from unittest.mock import AsyncMock
from starlette.websockets import WebSocketState

# Mock the dependencies to avoid import issues
import sys
sys.path.append('app')

try:
    from app.ws_manager import WebSocketManager
    from app.tests.ws_manager.test_base import MockWebSocket
    
    async def test_basic_flow():
        """Test the basic WebSocket flow"""
        print("Creating WebSocketManager...")
        
        # Reset singleton for testing
        WebSocketManager._instance = None
        WebSocketManager._initialized = False
        
        manager = WebSocketManager()
        print(f"Manager created: {manager}")
        print(f"Manager has connections_dict: {hasattr(manager, 'connections_dict')}")
        
        # Create a mock websocket
        mock_ws = MockWebSocket(WebSocketState.CONNECTED)
        print(f"MockWebSocket created: {mock_ws}")
        print(f"MockWebSocket state: {mock_ws.client_state}")
        
        # Test connect
        connection_id = "test-123"
        print(f"Attempting to connect with ID: {connection_id}")
        await manager.connect(mock_ws, connection_id)
        
        print(f"Connections after connect: {manager.connections}")
        print(f"Connection exists: {connection_id in manager.connections}")
        
        # Test send message
        message = {"type": "test", "data": "hello"}
        print(f"Attempting to send message: {message}")
        await manager.send_message(connection_id, message)
        
        # Check if send_json was called
        print(f"send_json called: {mock_ws.send_json.called}")
        print(f"send_json call count: {mock_ws.send_json.call_count}")
        if mock_ws.send_json.called:
            print(f"send_json call args: {mock_ws.send_json.call_args}")
        
        return mock_ws.send_json.called

    if __name__ == "__main__":
        result = asyncio.run(test_basic_flow())
        print(f"Test result: {result}")
        
except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()