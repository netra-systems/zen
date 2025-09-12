#!/usr/bin/env python3
"""
Simple test to isolate WebSocket serialization behavior.
"""

import asyncio
import time
import json


def create_complex_object():
    """Create a complex object for serialization testing."""
    obj = {"type": "complex", "data": {}}
    
    # Build nested structure (smaller than before to avoid import issues)
    current = obj["data"]
    for i in range(20):  # 20 levels
        current[f"level_{i}"] = {
            "items": [{"id": j, "content": "x" * 100} for j in range(10)],
            "text": "Some text data " * 50,
            "nested": {}
        }
        current = current[f"level_{i}"]["nested"]
    
    return obj


def sync_serialize(obj):
    """Simulate synchronous serialization like _serialize_message_safely."""
    # This is what happens in the synchronous path
    if isinstance(obj, dict):
        # Convert to JSON and back (what json.dumps test does)
        json_str = json.dumps(obj)
        # Additional processing that takes time
        result = json.loads(json_str)
        
        # Simulate additional work (like type conversion, validation, etc.)
        time.sleep(0.001)  # 1ms processing time per object
        return result
    
    return obj


async def async_serialize(obj):
    """Simulate async serialization like _serialize_message_safely_async."""
    loop = asyncio.get_event_loop()
    
    # Simulate running in thread pool
    def sync_work():
        return sync_serialize(obj)
    
    # This is what the thread pool executor does
    result = await loop.run_in_executor(None, sync_work)
    return result


async def test_blocking_behavior():
    """Test blocking behavior between sync and async serialization."""
    print("Testing serialization blocking behavior...")
    
    complex_obj = create_complex_object()
    print(f"Created object with ~{len(json.dumps(complex_obj))} characters")
    
    # Track event loop responsiveness
    blocks = []
    monitoring = True
    
    async def monitor_responsiveness():
        """Monitor event loop delays."""
        while monitoring:
            start = time.perf_counter()
            await asyncio.sleep(0.001)  # 1ms expected
            actual = time.perf_counter() - start
            
            if actual > 0.005:  # >5ms indicates blocking
                blocks.append(actual)
                print(f" WARNING: [U+FE0F]  Event loop delayed: {actual*1000:.2f}ms")
    
    monitor_task = asyncio.create_task(monitor_responsiveness())
    
    # Test 1: Multiple synchronous serializations
    print("\n1. Testing synchronous serialization (blocking)...")
    sync_start = time.perf_counter()
    
    for i in range(5):
        result = sync_serialize(complex_obj)
    
    sync_time = time.perf_counter() - sync_start
    print(f"   5 sync serializations: {sync_time*1000:.2f}ms")
    
    await asyncio.sleep(0.05)  # Let monitor catch up
    
    # Test 2: Multiple async serializations
    print("\n2. Testing async serialization (non-blocking)...")
    async_start = time.perf_counter()
    
    async_tasks = [async_serialize(complex_obj) for _ in range(5)]
    results = await asyncio.gather(*async_tasks)
    
    async_time = time.perf_counter() - async_start
    print(f"   5 async serializations: {async_time*1000:.2f}ms")
    
    await asyncio.sleep(0.05)  # Let monitor catch up
    
    # Stop monitoring
    monitoring = False
    monitor_task.cancel()
    
    # Analysis
    if blocks:
        print(f"\n CHART:  Event Loop Blocking Detected:")
        print(f"   Total blocks: {len(blocks)}")
        print(f"   Max block: {max(blocks)*1000:.2f}ms")
        print(f"   Total blocked time: {sum(blocks)*1000:.2f}ms")
        
        # Determine severity
        severe = [b for b in blocks if b > 0.050]
        moderate = [b for b in blocks if 0.010 <= b <= 0.050]
        minor = [b for b in blocks if b < 0.010]
        
        print(f"   Severe (>50ms): {len(severe)}")
        print(f"   Moderate (10-50ms): {len(moderate)}")
        print(f"   Minor (<10ms): {len(minor)}")
        
        return True
    else:
        print(f"\n PASS:  No significant blocking detected")
        return False


async def test_concurrent_vs_sequential():
    """Test concurrent vs sequential processing."""
    print("\n" + "="*50)
    print("Concurrent vs Sequential Processing Test")
    print("="*50)
    
    complex_obj = create_complex_object()
    
    # Sequential sync processing
    print("\n1. Sequential synchronous processing...")
    seq_start = time.perf_counter()
    
    for i in range(10):
        result = sync_serialize(complex_obj)
    
    seq_time = time.perf_counter() - seq_start
    print(f"   Sequential time: {seq_time*1000:.2f}ms")
    
    # Concurrent async processing
    print("\n2. Concurrent async processing...")
    conc_start = time.perf_counter()
    
    tasks = [async_serialize(complex_obj) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    conc_time = time.perf_counter() - conc_start
    print(f"   Concurrent time: {conc_time*1000:.2f}ms")
    
    # Compare
    improvement = ((seq_time - conc_time) / seq_time) * 100
    print(f"\n CHART:  Performance Comparison:")
    print(f"   Sequential: {seq_time*1000:.2f}ms")
    print(f"   Concurrent: {conc_time*1000:.2f}ms")
    print(f"   Improvement: {improvement:.1f}%")
    
    return conc_time < seq_time


async def simulate_websocket_load():
    """Simulate WebSocket load with mixed serialization paths."""
    print("\n" + "="*50)
    print("WebSocket Load Simulation")
    print("="*50)
    
    complex_obj = create_complex_object()
    
    # Simulate current implementation (mixed sync/async paths)
    print("\n1. Current mixed implementation...")
    
    blocks = []
    monitoring = True
    
    async def load_monitor():
        while monitoring:
            start = time.perf_counter()
            await asyncio.sleep(0.002)
            actual = time.perf_counter() - start
            if actual > 0.010:  # >10ms
                blocks.append(actual)
    
    monitor_task = asyncio.create_task(load_monitor())
    
    # Simulate mixed load
    load_start = time.perf_counter()
    
    # 5 send_to_thread (async) + 5 send_to_user (sync)  
    async_tasks = [async_serialize(complex_obj) for _ in range(5)]
    
    # Sync operations block the event loop
    sync_results = []
    for i in range(5):
        sync_results.append(sync_serialize(complex_obj))
    
    # Async operations
    async_results = await asyncio.gather(*async_tasks)
    
    load_time = time.perf_counter() - load_start
    
    monitoring = False
    monitor_task.cancel()
    
    print(f"   Mixed load time: {load_time*1000:.2f}ms")
    print(f"   Event loop blocks: {len(blocks)}")
    
    if blocks:
        print(f"   Max block: {max(blocks)*1000:.2f}ms")
        return True
    
    return False


async def main():
    """Main test function."""
    print("WebSocket Serialization Blocking Analysis")
    print("=" * 50)
    
    try:
        # Test basic blocking behavior
        blocking_detected = await test_blocking_behavior()
        
        # Test performance difference
        async_better = await test_concurrent_vs_sequential()
        
        # Test WebSocket load simulation
        load_blocking = await simulate_websocket_load()
        
        print("\n" + "="*50)
        print("CONCLUSIONS")
        print("="*50)
        
        if blocking_detected or load_blocking:
            print("[U+1F534] EVENT LOOP BLOCKING CONFIRMED")
            
            if blocking_detected:
                print("    FAIL:  Synchronous serialization blocks event loop")
            
            if load_blocking:
                print("    FAIL:  Mixed sync/async paths cause blocking under load")
            
            print("\n IDEA:  ROOT CAUSE:")
            print("   The issue is NOT with _serialize_message_safely_async")
            print("   The issue is that send_to_user, broadcast_to_room, etc.")
            print("   still use _serialize_message_safely (synchronous)")
            
            print("\n[U+1F527] SOLUTION:")
            print("   Update _send_to_connection to use async serialization")
            print("   This will fix send_to_user, broadcast_to_room, broadcast_to_all")
            
        else:
            print("[U+1F7E2] No blocking detected in test conditions")
            print("   Implementation may be adequate for current load patterns")
        
        if async_better:
            print(" PASS:  Async serialization shows performance benefits")
        else:
            print("[U+2139][U+FE0F]  Async serialization overhead may not be worth it for simple cases")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())