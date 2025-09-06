"""
Test WebSocket timing fix for startup race conditions.
Tests the enhanced UnifiedWebSocketManager that handles startup timing gracefully.
"""

import asyncio
import pytest
import uuid
import time
from typing import Dict, Any, List

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent: List[Dict[str, Any]] = []
        self.is_closed = False
    
    async def send_json(self, message: Dict[str, Any]):
        """Mock sending JSON message."""
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
    
    async def close(self):
        """Mock closing WebSocket."""
        self.is_closed = True


@pytest.mark.asyncio
async def test_startup_message_without_connection():
    """Test that startup messages don't trigger critical errors when no connection exists."""
    manager = UnifiedWebSocketManager()
    
    # Generate startup test user ID
    startup_user_id = f"startup_test_{uuid.uuid4()}"
    
    # Send a startup test message - should not log critical error
    startup_message = {
        "type": "startup_test",
        "timestamp": time.time(),
        "validation": "timing_test"
    }
    
    # This should NOT log a critical error for startup_test users
    await manager.send_to_user(startup_user_id, startup_message)
    
    # Verify message was stored for recovery
    assert startup_user_id in manager._message_recovery_queue
    queued_messages = manager._message_recovery_queue[startup_user_id]
    assert len(queued_messages) > 0
    assert queued_messages[0]["type"] == "startup_test"


@pytest.mark.asyncio
async def test_regular_message_still_logs_critical():
    """Test that non-startup messages still log critical errors when no connection exists."""
    manager = UnifiedWebSocketManager()
    
    # Regular user ID (not startup test)
    regular_user_id = f"user_{uuid.uuid4()}"
    
    # Send a regular message - should still log critical error
    regular_message = {
        "type": "agent_started",
        "data": {"agent": "test_agent"}
    }
    
    # This SHOULD log a critical error for regular users
    await manager.send_to_user(regular_user_id, regular_message)
    
    # Verify message was stored for recovery
    assert regular_user_id in manager._message_recovery_queue


@pytest.mark.asyncio
async def test_wait_for_connection_timeout():
    """Test wait_for_connection times out correctly when no connection is established."""
    manager = UnifiedWebSocketManager()
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Should timeout after 0.5 seconds
    start_time = asyncio.get_event_loop().time()
    result = await manager.wait_for_connection(user_id, timeout=0.5)
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert result is False
    assert 0.4 < elapsed < 0.6  # Allow some timing variance


@pytest.mark.asyncio
async def test_wait_for_connection_success():
    """Test wait_for_connection succeeds when connection is established."""
    manager = UnifiedWebSocketManager()
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Create a task that adds a connection after a short delay
    async def add_connection_delayed():
        await asyncio.sleep(0.2)
        mock_ws = MockWebSocket()
        connection = WebSocketConnection(
            connection_id=f"conn_{uuid.uuid4()}",
            user_id=user_id,
            websocket=mock_ws,
            connected_at=asyncio.get_event_loop().time()
        )
        await manager.add_connection(connection)
    
    # Start the delayed connection task
    asyncio.create_task(add_connection_delayed())
    
    # Wait for connection - should succeed after ~0.2 seconds
    start_time = asyncio.get_event_loop().time()
    result = await manager.wait_for_connection(user_id, timeout=1.0)
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert result is True
    assert 0.1 < elapsed < 0.4  # Connection should be established around 0.2s


@pytest.mark.asyncio
async def test_send_to_user_with_wait():
    """Test send_to_user_with_wait method properly waits for connections."""
    manager = UnifiedWebSocketManager()
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Message to send
    test_message = {
        "type": "test_event",
        "data": {"test": "data"}
    }
    
    # Create a task that adds a connection after a short delay
    mock_ws = MockWebSocket()
    
    async def add_connection_delayed():
        await asyncio.sleep(0.3)
        connection = WebSocketConnection(
            connection_id=f"conn_{uuid.uuid4()}",
            user_id=user_id,
            websocket=mock_ws,
            connected_at=asyncio.get_event_loop().time()
        )
        await manager.add_connection(connection)
    
    # Start the delayed connection task
    asyncio.create_task(add_connection_delayed())
    
    # Send message with wait - should succeed after connection is established
    result = await manager.send_to_user_with_wait(user_id, test_message, wait_timeout=1.0)
    
    assert result is True
    # Verify message was sent to the mock WebSocket
    assert len(mock_ws.messages_sent) == 1
    assert mock_ws.messages_sent[0]["type"] == "test_event"


@pytest.mark.asyncio
async def test_send_to_user_with_wait_timeout():
    """Test send_to_user_with_wait returns False on timeout."""
    manager = UnifiedWebSocketManager()
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Message to send
    test_message = {
        "type": "test_event",
        "data": {"test": "data"}
    }
    
    # Send message with short wait timeout - should fail
    result = await manager.send_to_user_with_wait(user_id, test_message, wait_timeout=0.2)
    
    assert result is False
    # Verify message was stored for recovery
    assert user_id in manager._message_recovery_queue


@pytest.mark.asyncio
async def test_recovery_queue_processing():
    """Test that queued messages are delivered when connection is established."""
    manager = UnifiedWebSocketManager()
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Send messages before connection exists
    messages = [
        {"type": "message_1", "data": {"seq": 1}},
        {"type": "message_2", "data": {"seq": 2}},
        {"type": "message_3", "data": {"seq": 3}}
    ]
    
    for msg in messages:
        await manager.send_to_user(user_id, msg)
    
    # Verify messages are queued
    assert user_id in manager._message_recovery_queue
    assert len(manager._message_recovery_queue[user_id]) == 3
    
    # Now establish connection
    mock_ws = MockWebSocket()
    connection = WebSocketConnection(
        connection_id=f"conn_{uuid.uuid4()}",
        user_id=user_id,
        websocket=mock_ws,
        connected_at=asyncio.get_event_loop().time()
    )
    await manager.add_connection(connection)
    
    # Wait a bit for recovery queue processing
    await asyncio.sleep(0.2)
    
    # Check that messages were delivered
    assert len(mock_ws.messages_sent) >= 3
    delivered_types = [msg["type"] for msg in mock_ws.messages_sent]
    assert "message_1" in delivered_types
    assert "message_2" in delivered_types
    assert "message_3" in delivered_types
    
    # Recovery queue should be cleared
    assert user_id not in manager._message_recovery_queue or len(manager._message_recovery_queue[user_id]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])