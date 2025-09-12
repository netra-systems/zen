#!/usr/bin/env python3
"""
Direct test of WebSocket async serialization to identify event loop blocking.
"""

import asyncio
import time
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to Python path
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


def create_large_message():
    """Create a complex message that requires heavy serialization."""
    message = {
        "type": "agent_update",
        "data": {}
    }
    
    # Build a large nested structure that will take time to serialize
    current = message["data"]
    for i in range(50):  # 50 levels deep
        current[f"level_{i}"] = {
            "items": [{"id": j, "data": "x" * 500} for j in range(5)],  # 2.5KB per level
            "nested": {}
        }
        current = current[f"level_{i}"]["nested"]
    
    return message


def create_large_agent_state():
    """Create a large DeepAgentState that requires complex serialization."""
    try:
        state = DeepAgentState(
            user_request="Test request with very long content " * 50,
            chat_thread_id="test-thread-123",
            user_id="test-user-456",
            step_count=100
        )
        
        # Add large amounts of data to trigger heavy serialization
        state.conversation_history = [
            {"role": "user", "content": "Large user message " * 200} for _ in range(20)
        ]
        state.tool_outputs = [
            {"tool": f"complex_tool_{i}", "output": "Tool output data " * 100} for i in range(10)
        ]
        
        return state
    except Exception as e:
        print(f"Error creating DeepAgentState: {e}")
        return {"fallback": "large_state", "data": "x" * 10000}


async def test_event_loop_blocking():
    """Test if serialization blocks the event loop."""
    print("Testing event loop blocking during serialization...")
    
    manager = WebSocketManager()
    large_message = create_large_message()
    
    # Track event loop responsiveness
    loop_blocked = False
    max_block_duration = 0
    
    async def monitor_loop():
        """Monitor if the event loop is responsive."""
        nonlocal loop_blocked, max_block_duration
        
        while True:
            start = time.perf_counter()
            await asyncio.sleep(0.01)  # Should complete in ~10ms
            duration = time.perf_counter() - start
            
            # If sleep took more than 50ms, loop was blocked
            if duration > 0.05:
                loop_blocked = True
                max_block_duration = max(max_block_duration, duration)
                print(f" WARNING: [U+FE0F]  Event loop blocked for {duration*1000:.1f}ms")
            
    # Start monitoring
    monitor_task = asyncio.create_task(monitor_loop())
    
    print("Testing synchronous serialization (current implementation)...")
    start_time = time.perf_counter()
    
    # Test synchronous serialization multiple times
    for i in range(3):
        print(f"  Sync serialization attempt {i+1}...")
        sync_start = time.perf_counter()
        result = manager._serialize_message_safely(large_message)
        sync_duration = time.perf_counter() - sync_start
        print(f"    Completed in {sync_duration*1000:.1f}ms")
    
    total_sync_time = time.perf_counter() - start_time
    
    # Test async serialization if available
    print("\nTesting async serialization...")
    start_time = time.perf_counter()
    
    if hasattr(manager, '_serialize_message_safely_async'):
        try:
            for i in range(3):
                print(f"  Async serialization attempt {i+1}...")
                async_start = time.perf_counter()
                result = await manager._serialize_message_safely_async(large_message)
                async_duration = time.perf_counter() - async_start
                print(f"    Completed in {async_duration*1000:.1f}ms")
        except Exception as e:
            print(f"    Error in async serialization: {e}")
    else:
        print("    Async serialization method not found!")
    
    total_async_time = time.perf_counter() - start_time
    
    # Stop monitoring
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    print(f"\nResults:")
    print(f"  Synchronous serialization total time: {total_sync_time*1000:.1f}ms")
    print(f"  Async serialization total time: {total_async_time*1000:.1f}ms")
    print(f"  Event loop blocked: {'Yes' if loop_blocked else 'No'}")
    if loop_blocked:
        print(f"  Maximum block duration: {max_block_duration*1000:.1f}ms")
    
    return loop_blocked, max_block_duration


async def test_async_serialization_performance():
    """Test async serialization performance specifically."""
    print("\n" + "="*60)
    print("Testing Async Serialization Performance")
    print("="*60)
    
    manager = WebSocketManager()
    
    # Test with different message types
    test_cases = [
        ("Simple Dict", {"type": "test", "message": "hello"}),
        ("Large Message", create_large_message()),
        ("Agent State", create_large_agent_state()),
    ]
    
    for test_name, message in test_cases:
        print(f"\n{test_name}:")
        
        # Test sync version
        print(f"  Synchronous:")
        sync_start = time.perf_counter()
        try:
            sync_result = manager._serialize_message_safely(message)
            sync_duration = time.perf_counter() - sync_start
            print(f"    Duration: {sync_duration*1000:.2f}ms")
            print(f"    Result size: ~{len(str(sync_result))} chars")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Test async version if available
        if hasattr(manager, '_serialize_message_safely_async'):
            print(f"  Asynchronous:")
            async_start = time.perf_counter()
            try:
                async_result = await manager._serialize_message_safely_async(message)
                async_duration = time.perf_counter() - async_start
                print(f"    Duration: {async_duration*1000:.2f}ms")
                print(f"    Result size: ~{len(str(async_result))} chars")
            except Exception as e:
                print(f"    Error: {e}")
        else:
            print(f"  Asynchronous: Not implemented")


async def test_concurrent_serialization():
    """Test concurrent serialization behavior."""
    print("\n" + "="*60)
    print("Testing Concurrent Serialization")
    print("="*60)
    
    manager = WebSocketManager()
    large_message = create_large_message()
    
    if hasattr(manager, '_serialize_message_safely_async'):
        print("Testing concurrent async serialization...")
        
        async def serialize_task(task_id):
            start = time.perf_counter()
            try:
                result = await manager._serialize_message_safely_async(large_message)
                duration = time.perf_counter() - start
                print(f"  Task {task_id}: {duration*1000:.1f}ms")
                return duration
            except Exception as e:
                print(f"  Task {task_id}: Error - {e}")
                return None
        
        # Run 5 serializations concurrently
        concurrent_start = time.perf_counter()
        tasks = [serialize_task(i) for i in range(5)]
        durations = await asyncio.gather(*tasks)
        concurrent_total = time.perf_counter() - concurrent_start
        
        print(f"  Concurrent execution total: {concurrent_total*1000:.1f}ms")
        print(f"  Average per task: {(concurrent_total/5)*1000:.1f}ms")
        
        # Compare with sequential
        print("\nTesting sequential async serialization...")
        sequential_start = time.perf_counter()
        for i in range(5):
            duration = await serialize_task(f"seq-{i}")
        sequential_total = time.perf_counter() - sequential_start
        
        print(f"  Sequential execution total: {sequential_total*1000:.1f}ms")
        
        improvement = ((sequential_total - concurrent_total) / sequential_total) * 100
        print(f"  Concurrency improvement: {improvement:.1f}%")
    else:
        print("Async serialization not available for concurrency testing")


async def main():
    """Main test function."""
    print("WebSocket Async Serialization Direct Test")
    print("=" * 60)
    
    try:
        # Test 1: Event loop blocking
        blocked, max_duration = await test_event_loop_blocking()
        
        # Test 2: Performance comparison
        await test_async_serialization_performance()
        
        # Test 3: Concurrent behavior
        await test_concurrent_serialization()
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        if blocked:
            print("[U+1F534] CRITICAL: Event loop blocking detected!")
            print(f"   Maximum blocking duration: {max_duration*1000:.1f}ms")
            print("   Recommendation: Complete async serialization implementation")
        else:
            print("[U+1F7E2] Event loop remains responsive during serialization")
        
        # Check if async implementation exists
        manager = WebSocketManager()
        if hasattr(manager, '_serialize_message_safely_async'):
            print("[U+1F7E2] Async serialization method exists")
            if hasattr(manager, '_serialization_executor'):
                print("[U+1F7E2] ThreadPoolExecutor is configured")
            else:
                print("[U+1F534] ThreadPoolExecutor missing")
        else:
            print("[U+1F534] Async serialization method missing")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())