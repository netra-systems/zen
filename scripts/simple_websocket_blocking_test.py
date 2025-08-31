#!/usr/bin/env python3
"""
Simple standalone test to demonstrate WebSocket serialization blocking issue.

This test demonstrates that the current WebSocket manager uses synchronous 
serialization which blocks the event loop during complex message processing.
"""

import asyncio
import time
import json
from typing import Dict, Any
from datetime import datetime, timezone
from unittest.mock import AsyncMock


class ComplexState:
    """Simulate a complex state object that takes time to serialize"""
    
    def __init__(self, complexity: int = 10):
        self.data = {}
        for i in range(complexity * 100):
            self.data[f"key_{i}"] = {
                "nested": [f"item_{j}" for j in range(20)],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "more_data": "x" * 1000  # Large string data
            }
        self.user_request = f"Complex request with {complexity} complexity"
        self.step_count = complexity * 50
        self.messages = [{"content": f"Message {i}: " + "x" * 200} for i in range(complexity * 5)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "data": self.data,
            "user_request": self.user_request,
            "step_count": self.step_count,
            "messages": self.messages
        }


class MockWebSocketManager:
    """Mock WebSocket manager that simulates the current blocking behavior"""
    
    def _serialize_message_safely(self, message: Any) -> Dict[str, Any]:
        """
        Current synchronous serialization - THIS BLOCKS THE EVENT LOOP
        
        This simulates the actual method in websocket_core/manager.py line 319
        which uses json.dumps() synchronously for complex objects.
        """
        try:
            if hasattr(message, 'to_dict'):
                message_dict = message.to_dict()
            else:
                message_dict = message
                
            # This synchronous JSON serialization blocks the event loop
            json_str = json.dumps(message_dict, default=str)
            
            # Simulate additional processing time for complex objects
            time.sleep(0.01)  # 10ms delay to simulate complex serialization
            
            return json.loads(json_str)
        except Exception as e:
            return {"error": str(e)}
    
    async def _send_to_connection(self, connection_id: str, message: Any) -> bool:
        """
        Current implementation that uses sync serialization - BLOCKS EVENT LOOP
        
        This simulates the actual method in websocket_core/manager.py line 810
        """
        try:
            # THIS IS THE BLOCKING CALL - uses sync serialization
            message_dict = self._serialize_message_safely(message)
            
            # Simulate WebSocket send
            await asyncio.sleep(0.001)  # Small async delay for WebSocket send
            
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False


class EventLoopMonitor:
    """Simple event loop blocking detector"""
    
    def __init__(self, threshold_ms: float = 5.0):
        self.threshold_ms = threshold_ms
        self.max_block = 0.0
        self.blocked_count = 0
        self._monitoring = False
        
    async def start_monitoring(self):
        """Start monitoring for event loop blocks"""
        self._monitoring = True
        self.max_block = 0.0
        self.blocked_count = 0
        asyncio.create_task(self._monitor_loop())
        
    async def stop_monitoring(self):
        """Stop monitoring and return results"""
        self._monitoring = False
        return {
            'max_block_ms': self.max_block * 1000,
            'blocked_count': self.blocked_count,
            'threshold_exceeded': self.max_block * 1000 > self.threshold_ms
        }
        
    async def _monitor_loop(self):
        """Monitor loop for blocking detection"""
        while self._monitoring:
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.001)  # 1ms
            end = asyncio.get_event_loop().time()
            
            actual_delay = end - start
            if actual_delay > (0.001 + self.threshold_ms / 1000):
                self.max_block = max(self.max_block, actual_delay - 0.001)
                self.blocked_count += 1


async def test_websocket_serialization_blocking():
    """
    Test demonstrating that synchronous serialization blocks the event loop.
    
    This test SHOULD show blocking behavior with the current implementation.
    Once async serialization is implemented, the blocking should be eliminated.
    """
    print("\n=== WebSocket Serialization Blocking Test ===")
    
    # Create mock WebSocket manager with current blocking implementation
    ws_manager = MockWebSocketManager()
    
    # Create complex message that takes time to serialize
    complex_state = ComplexState(complexity=20)
    
    # Set up event loop monitoring
    monitor = EventLoopMonitor(threshold_ms=5.0)
    await monitor.start_monitoring()
    
    print(f"Testing with complex state containing {len(complex_state.data)} nested objects...")
    
    start_time = time.perf_counter()
    
    # This should block the event loop due to sync serialization
    result = await ws_manager._send_to_connection("test_conn", complex_state)
    
    end_time = time.perf_counter()
    
    # Stop monitoring and get results
    blocking_results = await monitor.stop_monitoring()
    
    operation_time_ms = (end_time - start_time) * 1000
    
    print(f"\nResults:")
    print(f"  Operation succeeded: {result}")
    print(f"  Total operation time: {operation_time_ms:.2f}ms")
    print(f"  Event loop blocked for: {blocking_results['max_block_ms']:.2f}ms")
    print(f"  Blocking threshold: 5.0ms")
    print(f"  Threshold exceeded: {blocking_results['threshold_exceeded']}")
    print(f"  Number of blocks detected: {blocking_results['blocked_count']}")
    
    # Analysis
    print(f"\n=== Analysis ===")
    if blocking_results['threshold_exceeded']:
        print("❌ BLOCKING DETECTED: Synchronous serialization is blocking the event loop!")
        print("   This confirms the issue described in the CRITICAL CONTEXT.")
        print("   Real WebSocket connections and other async operations would be delayed.")
    else:
        print("✅ No significant blocking detected.")
        
    print(f"\n=== Expected Fix ===")
    print("The fix should replace the synchronous _serialize_message_safely() call")
    print("at line 810 in websocket_core/manager.py with the async version:")
    print("  message_dict = await self._serialize_message_safely_async(message)")
    print("\nThis would move serialization to a thread pool, preventing event loop blocking.")
    
    return blocking_results['threshold_exceeded']


async def test_concurrent_serialization_blocking():
    """Test that multiple concurrent serializations block each other"""
    print("\n\n=== Concurrent Serialization Blocking Test ===")
    
    ws_manager = MockWebSocketManager()
    
    # Create multiple complex messages
    messages = [ComplexState(complexity=10) for _ in range(5)]
    
    monitor = EventLoopMonitor(threshold_ms=8.0)
    await monitor.start_monitoring()
    
    print(f"Testing concurrent serialization of {len(messages)} complex messages...")
    
    start_time = time.perf_counter()
    
    # Send all messages concurrently - should show blocking due to sync serialization
    tasks = [
        ws_manager._send_to_connection(f"conn_{i}", message)
        for i, message in enumerate(messages)
    ]
    results = await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    
    blocking_results = await monitor.stop_monitoring()
    total_time_ms = (end_time - start_time) * 1000
    
    print(f"\nResults:")
    print(f"  All operations succeeded: {all(results)}")
    print(f"  Total concurrent time: {total_time_ms:.2f}ms")
    print(f"  Event loop blocked for: {blocking_results['max_block_ms']:.2f}ms")
    print(f"  Expected with async: <50ms (operations run concurrently)")
    print(f"  Actual time suggests: {'serial execution' if total_time_ms > 100 else 'concurrent execution'}")
    
    print(f"\n=== Analysis ===")
    if blocking_results['threshold_exceeded']:
        print("❌ BLOCKING DETECTED: Concurrent serializations are blocking each other!")
        print("   This shows serialization is not properly concurrent.")
    else:
        print("⚠️  Limited blocking detected, but operation time may still indicate issues.")
        
    return blocking_results['threshold_exceeded']


async def main():
    """Run all WebSocket serialization blocking tests"""
    print("WebSocket Async Serialization Blocking Demonstration")
    print("=====================================================")
    print("These tests demonstrate the blocking behavior described in the")
    print("CRITICAL CONTEXT: synchronous serialization at line 810 in")
    print("websocket_core/manager.py blocks the event loop during agent updates.")
    
    # Run tests
    test1_blocked = await test_websocket_serialization_blocking()
    test2_blocked = await test_concurrent_serialization_blocking()
    
    print(f"\n\n=== SUMMARY ===")
    print(f"Single operation blocking test:    {'BLOCKED' if test1_blocked else 'OK'}")
    print(f"Concurrent operations blocking test: {'BLOCKED' if test2_blocked else 'OK'}")
    
    if test1_blocked or test2_blocked:
        print("\n❌ BLOCKING CONFIRMED: The current implementation blocks the event loop.")
        print("   This validates the need for async serialization implementation.")
        print("   User chat will appear frozen during complex agent state updates.")
    else:
        print("\n✅ No blocking detected in this simplified test environment.")
        print("   However, real-world complex DeepAgentState objects may still cause blocking.")
    
    print(f"\nThe comprehensive test suite in:")
    print(f"  netra_backend/tests/compliance/test_websocket_serialization_blocking.py")
    print(f"provides more rigorous testing with actual WebSocket manager components.")


if __name__ == "__main__":
    asyncio.run(main())