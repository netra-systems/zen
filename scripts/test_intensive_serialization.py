#!/usr/bin/env python3
"""
More intensive test to identify event loop blocking during complex serialization.
"""

import asyncio
import time
import sys
import json
import gc
from shared.isolated_environment import IsolatedEnvironment

sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from netra_backend.app.websocket_core.manager import WebSocketManager


def create_extremely_complex_object():
    """Create an object that causes heavy serialization blocking."""
    
    # Create a massive nested structure
    base_obj = {
        "type": "complex_agent_state",
        "metadata": {
            "timestamp": time.time(),
            "nested_levels": 200,
            "items_per_level": 20
        },
        "data": {}
    }
    
    current = base_obj["data"]
    
    # Create 200 levels of nesting with 20 items each
    for level in range(200):
        level_data = {
            "level_id": level,
            "items": [],
            "metadata": {
                "created": time.time(),
                "level_type": f"level_{level}",
                "data": "x" * 1000  # 1KB of data per level
            },
            "children": {}
        }
        
        # Add 20 items per level
        for item in range(20):
            level_data["items"].append({
                "item_id": item,
                "content": f"Item {item} content " * 100,  # ~2KB per item
                "tags": [f"tag_{i}" for i in range(50)],
                "properties": {
                    f"prop_{i}": f"value_{i} " * 20 for i in range(10)
                }
            })
        
        current[f"level_{level}"] = level_data
        current = level_data["children"]
    
    return base_obj


def create_serialization_nightmare():
    """Create an object that will cause major serialization delays."""
    
    # Simulated DeepAgentState-like structure
    nightmare = {
        "user_request": "Process this extremely complex request " * 100,
        "chat_thread_id": "thread-" + "x" * 100,
        "user_id": "user-" + "y" * 100,
        "step_count": 50000,
        "conversation_history": [],
        "tool_outputs": [],
        "intermediate_results": {},
        "context_data": {},
        "large_blob": "z" * 1000000  # 1MB of text data
    }
    
    # Add massive conversation history
    for i in range(500):
        nightmare["conversation_history"].append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i} " * 200,  # ~2KB per message
            "timestamp": time.time() - (500 - i) * 60,
            "metadata": {
                "tokens": 400,
                "model": "gpt-4",
                "processing_time": 2.5,
                "context": {f"key_{j}": f"value_{j}" for j in range(20)}
            }
        })
    
    # Add massive tool outputs
    for i in range(100):
        nightmare["tool_outputs"].append({
            "tool_name": f"complex_tool_{i}",
            "execution_time": time.time(),
            "output": {
                "result": "Success",
                "data": f"Tool output data " * 500,  # ~8KB per tool
                "logs": [f"Log entry {j}" for j in range(100)],
                "metrics": {f"metric_{j}": j * 1.5 for j in range(50)}
            },
            "error": None if i % 10 != 0 else f"Error in tool {i}"
        })
    
    # Add massive intermediate results
    for i in range(200):
        nightmare["intermediate_results"][f"result_{i}"] = {
            "data": f"Result data " * 300,  # ~3KB per result
            "computed_at": time.time(),
            "dependencies": [f"dep_{j}" for j in range(10)],
            "complexity": {f"complex_{j}": [k for k in range(20)] for j in range(5)}
        }
    
    # Add context data
    for i in range(50):
        nightmare["context_data"][f"context_{i}"] = {
            "type": "context",
            "data": "x" * 5000,  # 5KB per context
            "nested": {
                f"nested_{j}": {
                    "value": "nested_value" * 50,
                    "array": list(range(100))
                } for j in range(10)
            }
        }
    
    return nightmare


async def test_event_loop_blocking_intensive():
    """Test for event loop blocking with very complex objects."""
    print("Testing intensive event loop blocking...")
    
    manager = WebSocketManager()
    nightmare_obj = create_serialization_nightmare()
    
    print(f"Created nightmare object with ~{len(json.dumps(nightmare_obj)) / 1024 / 1024:.2f}MB of data")
    
    # Track event loop blocking more precisely
    blocks = []
    monitoring = True
    
    async def precise_monitor():
        """Precisely monitor event loop responsiveness."""
        while monitoring:
            start = time.perf_counter()
            await asyncio.sleep(0.001)  # 1ms sleep
            actual_duration = time.perf_counter() - start
            
            # Track any delay > 2ms as potential blocking
            if actual_duration > 0.002:
                blocks.append(actual_duration)
                print(f" WARNING: [U+FE0F]  Event loop delayed: {actual_duration*1000:.2f}ms")
    
    # Start precise monitoring
    monitor_task = asyncio.create_task(precise_monitor())
    
    print("\nTesting synchronous serialization with nightmare object...")
    sync_start = time.perf_counter()
    
    try:
        sync_result = manager._serialize_message_safely(nightmare_obj)
        sync_duration = time.perf_counter() - sync_start
        print(f"Sync serialization: {sync_duration*1000:.2f}ms")
    except Exception as e:
        sync_duration = time.perf_counter() - sync_start
        print(f"Sync serialization failed after {sync_duration*1000:.2f}ms: {e}")
    
    await asyncio.sleep(0.1)  # Let monitoring catch up
    
    print("\nTesting async serialization with nightmare object...")
    async_start = time.perf_counter()
    
    try:
        if hasattr(manager, '_serialize_message_safely_async'):
            async_result = await manager._serialize_message_safely_async(nightmare_obj)
            async_duration = time.perf_counter() - async_start
            print(f"Async serialization: {async_duration*1000:.2f}ms")
        else:
            print("Async serialization not available")
            async_duration = 0
    except Exception as e:
        async_duration = time.perf_counter() - async_start
        print(f"Async serialization failed after {async_duration*1000:.2f}ms: {e}")
    
    await asyncio.sleep(0.1)  # Let monitoring catch up
    
    # Stop monitoring
    monitoring = False
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Analyze blocking
    if blocks:
        print(f"\n CHART:  Event Loop Blocking Analysis:")
        print(f"   Total blocking events: {len(blocks)}")
        print(f"   Maximum block duration: {max(blocks)*1000:.2f}ms")
        print(f"   Average block duration: {(sum(blocks)/len(blocks))*1000:.2f}ms")
        print(f"   Total blocked time: {sum(blocks)*1000:.2f}ms")
        
        # Classify severity
        severe_blocks = [b for b in blocks if b > 0.050]  # > 50ms
        moderate_blocks = [b for b in blocks if 0.010 < b <= 0.050]  # 10-50ms
        minor_blocks = [b for b in blocks if 0.002 < b <= 0.010]  # 2-10ms
        
        print(f"\n[U+1F4C8] Block Severity:")
        print(f"   Severe (>50ms): {len(severe_blocks)}")
        print(f"   Moderate (10-50ms): {len(moderate_blocks)}")
        print(f"   Minor (2-10ms): {len(minor_blocks)}")
        
        if severe_blocks:
            print(f"[U+1F534] CRITICAL: Found {len(severe_blocks)} severe blocking events!")
            return True, max(blocks)
        elif moderate_blocks:
            print(f"[U+1F7E1] WARNING: Found {len(moderate_blocks)} moderate blocking events")
            return True, max(blocks)
        else:
            print(f"[U+1F7E2] Only minor blocking detected")
            return len(blocks) > 0, max(blocks) if blocks else 0
    else:
        print("[U+1F7E2] No significant event loop blocking detected")
        return False, 0


async def test_serialization_fallback_paths():
    """Test the fallback paths in serialization that might cause blocking."""
    print("\n" + "="*60)
    print("Testing Serialization Fallback Paths")
    print("="*60)
    
    manager = WebSocketManager()
    
    # Test cases that trigger different fallback paths
    test_cases = [
        ("Circular Reference", create_circular_reference()),
        ("Unserializable Object", create_unserializable_object()),
        ("Large Pydantic-like Object", create_fake_pydantic()),
        ("JSON Serialization Failure", create_json_failure_object()),
    ]
    
    for test_name, obj in test_cases:
        print(f"\n{test_name}:")
        
        # Test sync path
        sync_start = time.perf_counter()
        try:
            sync_result = manager._serialize_message_safely(obj)
            sync_duration = time.perf_counter() - sync_start
            print(f"  Sync: {sync_duration*1000:.2f}ms - Success")
        except Exception as e:
            sync_duration = time.perf_counter() - sync_start
            print(f"  Sync: {sync_duration*1000:.2f}ms - Error: {e}")
        
        # Test async path
        if hasattr(manager, '_serialize_message_safely_async'):
            async_start = time.perf_counter()
            try:
                async_result = await manager._serialize_message_safely_async(obj)
                async_duration = time.perf_counter() - async_start
                print(f"  Async: {async_duration*1000:.2f}ms - Success")
            except Exception as e:
                async_duration = time.perf_counter() - async_start
                print(f"  Async: {async_duration*1000:.2f}ms - Error: {e}")


def create_circular_reference():
    """Create an object with circular references."""
    obj = {"type": "circular"}
    obj["self"] = obj
    return obj


def create_unserializable_object():
    """Create an object that can't be serialized."""
    class UnserializableClass:
        def __init__(self):
            self.data = "test"
            self.func = lambda x: x  # Functions can't be serialized
    
    return UnserializableClass()


def create_fake_pydantic():
    """Create an object that looks like a Pydantic model."""
    class FakePydantic:
        def __init__(self):
            self.field1 = "test"
            self.field2 = list(range(10000))  # Large list
            
        def model_dump(self, **kwargs):
            # Simulate slow model_dump
            time.sleep(0.01)  # 10ms delay
            return {
                "field1": self.field1,
                "field2": self.field2,
                "mode": kwargs.get("mode", "python")
            }
    
    return FakePydantic()


def create_json_failure_object():
    """Create an object that causes json.dumps to fail."""
    import datetime
    
    return {
        "datetime": datetime.datetime.now(),  # Not JSON serializable
        "set": {1, 2, 3},  # Sets not JSON serializable
        "complex": 3 + 4j,  # Complex numbers not JSON serializable
    }


async def main():
    """Main test function."""
    print("Intensive WebSocket Async Serialization Test")
    print("=" * 60)
    
    try:
        # Force garbage collection to start clean
        gc.collect()
        
        # Test intensive blocking
        blocked, max_duration = await test_event_loop_blocking_intensive()
        
        # Test fallback paths
        await test_serialization_fallback_paths()
        
        print("\n" + "="*60)
        print("FINAL ANALYSIS")
        print("="*60)
        
        if blocked:
            print(f"[U+1F534] Event loop blocking detected!")
            print(f"   Maximum blocking: {max_duration*1000:.2f}ms")
            
            if max_duration > 0.100:  # > 100ms
                print(f" ALERT:  CRITICAL ISSUE: Blocking > 100ms detected")
                print(f"   This will cause noticeable UI freezing")
                print(f"   Async serialization implementation has issues")
            elif max_duration > 0.050:  # > 50ms
                print(f" WARNING: [U+FE0F]  MODERATE ISSUE: Blocking 50-100ms detected")
                print(f"   May cause minor UI stuttering")
            else:
                print(f"[U+2139][U+FE0F]  MINOR ISSUE: Only small blocking detected")
        else:
            print(f"[U+1F7E2] No significant event loop blocking")
        
        # Check implementation status
        manager = WebSocketManager()
        if hasattr(manager, '_serialize_message_safely_async'):
            print(f" PASS:  Async serialization method exists")
            if hasattr(manager, '_serialization_executor'):
                print(f" PASS:  ThreadPoolExecutor configured")
                print(f"   Max workers: {manager._serialization_executor._max_workers}")
            else:
                print(f" FAIL:  ThreadPoolExecutor missing")
        else:
            print(f" FAIL:  Async serialization method missing")
        
        print(f"\n IDEA:  Recommendations:")
        if max_duration > 0.050:
            print(f"   - Complex object serialization needs thread pool offloading")
            print(f"   - Consider implementing streaming serialization for large objects")
            print(f"   - Add caching for frequently serialized objects")
        else:
            print(f"   - Current implementation appears adequate for most use cases")
            print(f"   - Monitor production performance for edge cases")
            
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())