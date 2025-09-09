"""
Validate MockWebSocketManager Interface Fixes
"""
import asyncio
import json
import pytest

from test_framework.fixtures.websocket_manager_mock import (
    MockWebSocketManager, 
    MockWebSocketConnection
)

@pytest.mark.asyncio
async def test_mock_websocket_manager_recv_send_interface():
    """Test that MockWebSocketManager has working recv/send methods."""
    manager = MockWebSocketManager()
    
    # Test recv method exists and works
    assert hasattr(manager, 'recv')
    recv_result = await manager.recv()
    assert isinstance(recv_result, str)
    
    # Should be valid JSON
    parsed = json.loads(recv_result)
    assert 'type' in parsed
    
    # Test send method exists and works
    assert hasattr(manager, 'send')
    test_message = json.dumps({"type": "test", "data": "hello"})
    await manager.send(test_message)
    
    # Should be recorded in messages_sent
    assert len(manager.messages_sent) == 1

@pytest.mark.asyncio
async def test_mock_websocket_connection_recv_interface():
    """Test that MockWebSocketConnection has working recv method."""
    conn = MockWebSocketConnection("test_conn", "test_user")
    
    # Test recv method exists and works
    assert hasattr(conn, 'recv')
    
    # Add a message to receive
    conn.add_received_message({"type": "response", "data": "test response"})
    
    # Test recv returns JSON string
    recv_result = await conn.recv()
    assert isinstance(recv_result, str)
    
    # Should be valid JSON
    parsed = json.loads(recv_result)
    assert parsed['type'] == 'response'
    assert parsed['data'] == 'test response'

@pytest.mark.asyncio
async def test_mock_websocket_connection_send_compatibility():
    """Test that MockWebSocketConnection send works with both string and dict."""
    conn = MockWebSocketConnection("test_conn", "test_user")
    
    # Test send with JSON string (real WebSocket pattern)
    json_message = json.dumps({"type": "user_message", "text": "hello"})
    await conn.send(json_message)
    assert len(conn.messages_sent) == 1
    
    # Test send with dict (backward compatibility)
    dict_message = {"type": "dict_message", "text": "hello dict"}
    await conn.send(dict_message)
    assert len(conn.messages_sent) == 2
    
    # Both should be stored as parsed dicts
    assert conn.messages_sent[0]['message']['type'] == 'user_message'
    assert conn.messages_sent[1]['message']['type'] == 'dict_message'

@pytest.mark.asyncio
async def test_websocket_interface_timeout_support():
    """Test that recv methods support timeout parameter."""
    conn = MockWebSocketConnection("test_conn", "test_user")
    manager = MockWebSocketManager()
    
    # These should not crash with timeout parameter
    await manager.recv(timeout=5.0)
    await conn.recv(timeout=5.0)

if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_mock_websocket_manager_recv_send_interface())
    asyncio.run(test_mock_websocket_connection_recv_interface())
    asyncio.run(test_mock_websocket_connection_send_compatibility())
    asyncio.run(test_websocket_interface_timeout_support())
    print("All validation tests passed!")