import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ws_manager import WebSocketManager

@pytest.fixture
def mock_redis_manager():
    redis_manager = MagicMock()
    redis_manager.publish = AsyncMock()
    redis_manager.pubsub = MagicMock()
    redis_manager.pubsub.return_value.subscribe = AsyncMock()
    redis_manager.pubsub.return_value.unsubscribe = AsyncMock()
    redis_manager.pubsub.return_value.get_message = AsyncMock()
    return redis_manager

@pytest.mark.asyncio
async def test_connect(mock_redis_manager):
    manager = WebSocketManager(mock_redis_manager)
    websocket = AsyncMock()
    await manager.connect(websocket, "user1")
    assert "user1" in manager.connections
    assert websocket in manager.connections["user1"]
    mock_redis_manager.pubsub.return_value.subscribe.assert_called_with("user:user1")

@pytest.mark.asyncio
async def test_disconnect(mock_redis_manager):
    manager = WebSocketManager(mock_redis_manager)
    websocket = AsyncMock()
    await manager.connect(websocket, "user1")
    manager.disconnect("user1", websocket)
    assert "user1" not in manager.connections
    mock_redis_manager.pubsub.return_value.unsubscribe.assert_called_with("user:user1")

@pytest.mark.asyncio
async def test_send_to_client(mock_redis_manager):
    manager = WebSocketManager(mock_redis_manager)
    message = MagicMock()
    message.model_dump_json.return_value = '{"type": "test", "payload": {}}'
    await manager.send_to_client("user1", message)
    mock_redis_manager.publish.assert_called_with("user:user1", '{"type": "test", "payload": {}}')

@pytest.mark.asyncio
async def test_broadcast(mock_redis_manager):
    manager = WebSocketManager(mock_redis_manager)
    message = MagicMock()
    message.model_dump_json.return_value = '{"type": "test", "payload": {}}'
    await manager.broadcast(message)
    mock_redis_manager.publish.assert_called_with("broadcast", '{"type": "test", "payload": {}}')
