#!/usr/bin/env python3
"""
Targeted test to identify the exact source of event loop blocking.
"""

import asyncio
import time
import sys
from shared.isolated_environment import IsolatedEnvironment

sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from fastapi import WebSocket


def create_blocking_object():
    """Create an object that will cause significant serialization delays."""
    
    # Create a complex nested structure with circular patterns
    obj = {
        "type": "blocking_nightmare",
        "metadata": {
            "timestamp": time.time(),
            "processing_stage": "intensive_serialization"
        },
        "data": {}
    }
    
    # Create deeply nested structure that will stress serialization
    current = obj["data"]
    for level in range(100):  # 100 levels deep
        level_data = {
            "level_id": level,
            "complex_data": {
                # Multiple large arrays and nested objects
                f"array_{i}": list(range(100)) for i in range(10)
            },
            "text_blob": "This is a large text blob that repeats. " * 100,  # ~4KB
            "nested_objects": {},
            "children": {}
        }
        
        # Add nested objects at each level
        for i in range(5):
            level_data["nested_objects"][f"obj_{i}"] = {
                "properties": {f"prop_{j}": f"value_{j}" * 20 for j in range(20)},
                "arrays": [list(range(50)) for _ in range(10)],
                "metadata": {"created": time.time(), "level": level, "obj": i}
            }
        
        current[f"level_{level}"] = level_data
        current = level_data["children"]
    
    return obj


async def test_synchronous_serialization_blocking():
    """Test synchronous serialization path for blocking."""
    print("Testing synchronous serialization blocking...")
    
    manager = WebSocketManager()
    blocking_obj = create_blocking_object()
    
    # Monitor event loop blocking precisely
    blocks = []
    monitoring = True
    
    async def event_loop_monitor():
        """Monitor event loop delays."""
        while monitoring:
            start = time.perf_counter()
            await asyncio.sleep(0.001)  # 1ms sleep
            actual_time = time.perf_counter() - start
            
            # Any delay > 5ms indicates potential blocking
            if actual_time > 0.005:
                blocks.append(actual_time)
                print(f" WARNING: [U+FE0F]  Event loop delayed: {actual_time*1000:.2f}ms")
    
    # Start monitoring
    monitor_task = asyncio.create_task(event_loop_monitor())
    
    print("\n1. Testing _serialize_message_safely (sync path)...")
    sync_start = time.perf_counter()
    
    try:
        sync_result = manager._serialize_message_safely(blocking_obj)
        sync_time = time.perf_counter() - sync_start
        print(f"   Sync serialization completed: {sync_time*1000:.2f}ms")
    except Exception as e:
        sync_time = time.perf_counter() - sync_start
        print(f"   Sync serialization failed: {sync_time*1000:.2f}ms - {e}")
    
    await asyncio.sleep(0.05)  # Give monitor time to detect
    
    print("\n2. Testing _serialize_message_safely_async (async path)...")
    async_start = time.perf_counter()
    
    try:
        async_result = await manager._serialize_message_safely_async(blocking_obj)
        async_time = time.perf_counter() - async_start
        print(f"   Async serialization completed: {async_time*1000:.2f}ms")
    except Exception as e:
        async_time = time.perf_counter() - async_start
        print(f"   Async serialization failed: {async_time*1000:.2f}ms - {e}")
    
    await asyncio.sleep(0.05)  # Give monitor time to detect
    
    # Stop monitoring
    monitoring = False
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Analyze results
    if blocks:
        max_block = max(blocks)
        total_blocks = len(blocks)
        total_blocked_time = sum(blocks)
        
        print(f"\n CHART:  Blocking Analysis:")
        print(f"   Total blocking events: {total_blocks}")
        print(f"   Maximum block: {max_block*1000:.2f}ms")
        print(f"   Total blocked time: {total_blocked_time*1000:.2f}ms")
        
        return max_block > 0.010  # Consider >10ms as significant blocking
    else:
        print(f"\n PASS:  No significant blocking detected")
        return False


async def test_send_to_user_vs_send_to_thread():
    """Compare blocking between send_to_user and send_to_thread."""
    print("\n" + "="*60)
    print("Comparing send_to_user vs send_to_thread blocking")
    print("="*60)
    
    manager = WebSocketManager()
    blocking_obj = create_blocking_object()
    
    # Create mock websocket connections
    mock_websocket1 = AsyncMock(spec=WebSocket)
    mock_websocket1.send_json = AsyncMock()
    
    mock_websocket2 = AsyncMock(spec=WebSocket)
    mock_websocket2.send_json = AsyncMock()
    
    # Connect mock users
    conn_id1 = await manager.connect_user("user1", mock_websocket1, "thread1")
    conn_id2 = await manager.connect_user("user2", mock_websocket2, "thread2")
    
    print(f"Connected test users: {conn_id1}, {conn_id2}")
    
    # Test send_to_user (uses synchronous serialization)
    print("\n1. Testing send_to_user (synchronous serialization path)...")
    blocks_sync = []
    monitoring_sync = True
    
    async def monitor_sync():
        while monitoring_sync:
            start = time.perf_counter()
            await asyncio.sleep(0.001)
            duration = time.perf_counter() - start
            if duration > 0.005:
                blocks_sync.append(duration)
    
    monitor_sync_task = asyncio.create_task(monitor_sync())
    
    send_user_start = time.perf_counter()
    result1 = await manager.send_to_user("user1", blocking_obj)
    send_user_time = time.perf_counter() - send_user_start
    
    await asyncio.sleep(0.05)
    monitoring_sync = False
    monitor_sync_task.cancel()
    
    print(f"   send_to_user result: {result1}")
    print(f"   send_to_user time: {send_user_time*1000:.2f}ms")
    print(f"   Event loop blocks during send_to_user: {len(blocks_sync)}")
    
    # Test send_to_thread (uses async serialization)
    print("\n2. Testing send_to_thread (async serialization path)...")
    blocks_async = []
    monitoring_async = True
    
    async def monitor_async():
        while monitoring_async:
            start = time.perf_counter()
            await asyncio.sleep(0.001)
            duration = time.perf_counter() - start
            if duration > 0.005:
                blocks_async.append(duration)
    
    monitor_async_task = asyncio.create_task(monitor_async())
    
    send_thread_start = time.perf_counter()
    result2 = await manager.send_to_thread("thread2", blocking_obj)
    send_thread_time = time.perf_counter() - send_thread_start
    
    await asyncio.sleep(0.05)
    monitoring_async = False
    monitor_async_task.cancel()
    
    print(f"   send_to_thread result: {result2}")
    print(f"   send_to_thread time: {send_thread_time*1000:.2f}ms")
    print(f"   Event loop blocks during send_to_thread: {len(blocks_async)}")
    
    # Compare results
    print(f"\n CHART:  Comparison Results:")
    print(f"   send_to_user blocks: {len(blocks_sync)}")
    print(f"   send_to_thread blocks: {len(blocks_async)}")
    
    if len(blocks_sync) > len(blocks_async):
        print(f"[U+1F534] send_to_user causes more blocking than send_to_thread")
        print(f"   This confirms that synchronous serialization is the issue")
        return True
    else:
        print(f"[U+1F7E2] Both paths have similar blocking behavior")
        return False


async def test_concurrent_serialization_stress():
    """Stress test concurrent serialization with complex objects."""
    print("\n" + "="*60)
    print("Concurrent Serialization Stress Test")
    print("="*60)
    
    manager = WebSocketManager()
    
    # Create multiple complex objects
    complex_objects = [create_blocking_object() for _ in range(10)]
    
    print(f"Created {len(complex_objects)} complex objects for stress testing")
    
    # Monitor event loop during concurrent operations
    blocks = []
    monitoring = True
    
    async def stress_monitor():
        while monitoring:
            start = time.perf_counter()
            await asyncio.sleep(0.002)  # 2ms sleep
            duration = time.perf_counter() - start
            if duration > 0.010:  # >10ms indicates blocking
                blocks.append(duration)
                print(f" WARNING: [U+FE0F]  Stress test blocking: {duration*1000:.2f}ms")
    
    monitor_task = asyncio.create_task(stress_monitor())
    
    # Test concurrent async serialization
    print("\n1. Concurrent async serialization...")
    async_start = time.perf_counter()
    
    async_tasks = [
        manager._serialize_message_safely_async(obj) 
        for obj in complex_objects
    ]
    
    async_results = await asyncio.gather(*async_tasks, return_exceptions=True)
    async_total_time = time.perf_counter() - async_start
    
    successful_async = sum(1 for r in async_results if not isinstance(r, Exception))
    print(f"   Async results: {successful_async}/{len(complex_objects)} successful")
    print(f"   Total time: {async_total_time*1000:.2f}ms")
    print(f"   Average per object: {(async_total_time/len(complex_objects))*1000:.2f}ms")
    
    await asyncio.sleep(0.1)
    
    # Test concurrent sync serialization
    print("\n2. Concurrent sync serialization (for comparison)...")
    sync_start = time.perf_counter()
    
    # Run sync operations in async context (they should block)
    sync_tasks = []
    for obj in complex_objects:
        async def sync_wrapper(o):
            return manager._serialize_message_safely(o)
        sync_tasks.append(sync_wrapper(obj))
    
    sync_results = await asyncio.gather(*sync_tasks, return_exceptions=True)
    sync_total_time = time.perf_counter() - sync_start
    
    successful_sync = sum(1 for r in sync_results if not isinstance(r, Exception))
    print(f"   Sync results: {successful_sync}/{len(complex_objects)} successful")
    print(f"   Total time: {sync_total_time*1000:.2f}ms")
    print(f"   Average per object: {(sync_total_time/len(complex_objects))*1000:.2f}ms")
    
    # Stop monitoring
    monitoring = False
    monitor_task.cancel()
    
    # Analysis
    severe_blocks = [b for b in blocks if b > 0.050]  # >50ms
    moderate_blocks = [b for b in blocks if 0.020 <= b <= 0.050]  # 20-50ms
    
    print(f"\n CHART:  Stress Test Analysis:")
    print(f"   Total blocking events: {len(blocks)}")
    print(f"   Severe blocks (>50ms): {len(severe_blocks)}")
    print(f"   Moderate blocks (20-50ms): {len(moderate_blocks)}")
    
    if severe_blocks:
        print(f"[U+1F534] CRITICAL: Severe blocking detected during stress test")
        return True
    elif moderate_blocks:
        print(f"[U+1F7E1] WARNING: Moderate blocking detected")
        return True
    else:
        print(f"[U+1F7E2] Stress test completed without significant blocking")
        return False


async def main():
    """Main test function."""
    print("WebSocket Async Serialization Blocking Analysis")
    print("=" * 60)
    
    results = {
        "sync_blocking": False,
        "path_comparison_blocking": False,
        "stress_blocking": False
    }
    
    try:
        # Test 1: Direct serialization blocking
        results["sync_blocking"] = await test_synchronous_serialization_blocking()
        
        # Test 2: Path comparison (send_to_user vs send_to_thread)
        results["path_comparison_blocking"] = await test_send_to_user_vs_send_to_thread()
        
        # Test 3: Stress test
        results["stress_blocking"] = await test_concurrent_serialization_stress()
        
        print("\n" + "="*60)
        print("FINAL ANALYSIS")
        print("="*60)
        
        blocking_detected = any(results.values())
        
        if blocking_detected:
            print("[U+1F534] EVENT LOOP BLOCKING CONFIRMED")
            print("\nRoot Cause Analysis:")
            
            if results["sync_blocking"]:
                print("    FAIL:  Synchronous serialization blocks event loop")
            
            if results["path_comparison_blocking"]:
                print("    FAIL:  send_to_user (sync path) blocks more than send_to_thread (async path)")
                print("    IDEA:  This confirms the fix should apply async serialization to send_to_user")
            
            if results["stress_blocking"]:
                print("    FAIL:  System cannot handle concurrent complex serialization")
            
            print("\n[U+1F527] SOLUTION REQUIRED:")
            print("   1. Update send_to_user to use _serialize_message_safely_async")
            print("   2. Update broadcast_to_room to use _serialize_message_safely_async")
            print("   3. Update broadcast_to_all to use _serialize_message_safely_async")
            print("   4. Replace synchronous serialization calls in _send_to_connection")
            
        else:
            print("[U+1F7E2] NO SIGNIFICANT BLOCKING DETECTED")
            print("Current async serialization implementation appears sufficient")
        
        print(f"\n CHART:  Test Summary:")
        for test, blocked in results.items():
            status = "BLOCKED" if blocked else "OK"
            print(f"   {test}: {status}")
            
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())