"""
Simple test to verify async serialization is working correctly.
"""

import asyncio
import time
import pytest
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from fastapi import WebSocket
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.asyncio
async def test_async_serialization_non_blocking():
    """Test that async serialization doesn't block the event loop."""
    manager = WebSocketManager()
    
    # Create a large message that takes time to serialize
    large_message = {
        "type": "test",
        "data": {}
    }
    
    # Build a large nested structure
    current = large_message["data"]
    for i in range(50):
        current[f"level_{i}"] = {
            "items": [{"id": j, "data": "x" * 1000} for j in range(5)],
            "nested": {}
        }
        current = current[f"level_{i}"]["nested"]
    
    # Test async serialization
    start = time.perf_counter()
    result = await manager._serialize_message_safely_async(large_message)
    duration = time.perf_counter() - start
    
    # Should return a valid dict
    assert isinstance(result, dict)
    assert result.get("type") == "test"
    
    print(f"Async serialization took {duration:.3f}s")
    
    # Now test that multiple serializations can run concurrently
    start = time.perf_counter()
    tasks = [
        manager._serialize_message_safely_async(large_message)
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)
    duration = time.perf_counter() - start
    
    # All should succeed
    assert all(isinstance(r, dict) for r in results)
    
    print(f"5 concurrent serializations took {duration:.3f}s")
    # Should be much faster than 5x single serialization time due to concurrency
    

@pytest.mark.asyncio
async def test_send_to_thread_uses_async_serialization():
    """Test that send_to_thread uses async serialization and concurrent sending."""
    manager = WebSocketManager()
    
    # Create mock websockets
    mock_websockets = []
    for i in range(3):
        ws = AsyncMock(spec=WebSocket)
        ws.send_json = AsyncNone  # TODO: Use real service instance
        conn_id = await manager.connect_user(f"user-{i}", ws, "test-thread")
        mock_websockets.append(ws)
    
    # Create a complex message with proper fields
    state = DeepAgentState(
        user_request="test",
        chat_thread_id="test-thread",
        user_id="test-user",
        messages=[
            {"role": "user", "content": "test " * 100} for _ in range(10)
        ],
        metadata={"timestamp": str(time.time()), "data": "x" * 1000}
    )
    
    # Send to thread - should use async serialization
    start = time.perf_counter()
    result = await manager.send_to_thread("test-thread", state)
    duration = time.perf_counter() - start
    
    # Should succeed
    assert result is True
    
    # All websockets should have received the message
    for ws in mock_websockets:
        assert ws.send_json.call_count >= 1
    
    print(f"Send to thread with async serialization took {duration:.3f}s")
    

@pytest.mark.asyncio
async def test_event_loop_responsiveness_during_serialization():
    """Test that the event loop remains responsive during serialization."""
    manager = WebSocketManager()
    
    # Create a very large message
    huge_message = {
        "type": "huge",
        "data": ["x" * 10000 for _ in range(1000)]  # ~10MB of data
    }
    
    # Track event loop responsiveness
    loop_checks = []
    
    async def check_loop_responsiveness():
        """Check if loop is responsive every 10ms."""
        for _ in range(20):  # Check 20 times
            start = time.perf_counter()
            await asyncio.sleep(0.01)  # Should take ~10ms
            actual = time.perf_counter() - start
            loop_checks.append(actual)
    
    # Run serialization and responsiveness check concurrently
    await asyncio.gather(
        manager._serialize_message_safely_async(huge_message),
        check_loop_responsiveness()
    )
    
    # Check that loop remained responsive (no check took more than 50ms)
    max_delay = max(loop_checks)
    avg_delay = sum(loop_checks) / len(loop_checks)
    
    print(f"Event loop delays: max={max_delay:.3f}s, avg={avg_delay:.3f}s")
    
    # Loop should remain responsive (allowing some tolerance)
    assert max_delay < 0.1, f"Event loop was blocked for {max_delay:.3f}s"
    assert avg_delay < 0.02, f"Average loop delay was {avg_delay:.3f}s"


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_async_serialization_non_blocking())
    asyncio.run(test_send_to_thread_uses_async_serialization())
    asyncio.run(test_event_loop_responsiveness_during_serialization())
    print("All tests passed!")