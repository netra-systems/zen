import pytest
from unittest.mock import AsyncMock
from app.ws_manager import WebSocketManager

@pytest.mark.asyncio
async def test_connect():
    manager = WebSocketManager()
    websocket = AsyncMock()
    await manager.connect("user1", websocket)
    assert "user1" in manager.active_connections
    assert websocket in manager.active_connections["user1"]

@pytest.mark.asyncio
async def test_disconnect():
    manager = WebSocketManager()
    manager.active_connections.clear()
    websocket = AsyncMock()
    await manager.connect("user1", websocket)
    manager.disconnect("user1", websocket)
    assert "user1" not in manager.active_connections

@pytest.mark.asyncio
async def test_send_message():
    manager = WebSocketManager()
    websocket = AsyncMock()
    await manager.connect("user1", websocket)
    message = {"key": "value"}
    await manager.send_message("user1", message)
    websocket.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_broadcast():
    manager = WebSocketManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect("user1", ws1)
    await manager.connect("user2", ws2)
    message = {"key": "value"}
    await manager.broadcast(message)
    ws1.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)
