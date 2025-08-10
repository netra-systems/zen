import pytest
from unittest.mock import AsyncMock
from app.ws_manager import WebSocketManager

@pytest.mark.asyncio
async def test_connect():
    manager = WebSocketManager()
    websocket = AsyncMock()
    websocket.client_state = AsyncMock()
    conn_info = await manager.connect("user1", websocket)
    assert "user1" in manager.active_connections
    # Check that ConnectionInfo object is stored, not raw websocket
    assert any(conn.websocket == websocket for conn in manager.active_connections["user1"])
    assert conn_info.user_id == "user1"
    assert conn_info.websocket == websocket

@pytest.mark.asyncio
async def test_disconnect():
    manager = WebSocketManager()
    manager.active_connections.clear()
    websocket = AsyncMock()
    websocket.client_state = AsyncMock()
    await manager.connect("user1", websocket)
    await manager.disconnect("user1", websocket)
    assert "user1" not in manager.active_connections

@pytest.mark.asyncio
async def test_send_message():
    manager = WebSocketManager()
    websocket = AsyncMock()
    websocket.client_state = AsyncMock()
    websocket.send_json = AsyncMock(return_value=None)
    await manager.connect("user1", websocket)
    message = {"key": "value"}
    result = await manager.send_message("user1", message)
    assert result == True
    # Check that send_json was called with the message (with added timestamp)
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["key"] == "value"
    assert "timestamp" in call_args

@pytest.mark.asyncio
async def test_broadcast():
    manager = WebSocketManager()
    ws1 = AsyncMock()
    ws1.client_state = AsyncMock()
    ws1.send_json = AsyncMock(return_value=None)
    ws2 = AsyncMock()
    ws2.client_state = AsyncMock()
    ws2.send_json = AsyncMock(return_value=None)
    await manager.connect("user1", ws1)
    await manager.connect("user2", ws2)
    message = {"key": "value"}
    await manager.broadcast(message)
    # Check that both websockets received the message
    ws1.send_json.assert_called_once()
    ws2.send_json.assert_called_once()
    # Check message content
    call_args1 = ws1.send_json.call_args[0][0]
    call_args2 = ws2.send_json.call_args[0][0]
    assert call_args1["key"] == "value"
    assert call_args2["key"] == "value"
