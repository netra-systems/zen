#!/usr/bin/env python3
"""
Test to reproduce the event batching regression where events wait until all
items complete before rendering/receiving, rather than streaming immediately.

This test simulates the issue where async callbacks might be causing events
to queue up rather than being displayed immediately as they arrive.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock

# Mock WebSocket event structure
class MockWebSocketEvent:
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now()

class EventBatchingTest:
    """Test harness to reproduce the batching issue"""

    def __init__(self):
        self.received_events: List[MockWebSocketEvent] = []
        self.display_times: List[float] = []
        self.event_received_times: List[float] = []

    async def simulate_websocket_stream(self, events: List[Dict[str, Any]], delay_between_events: float = 0.5):
        """Simulate WebSocket events arriving with delays between them"""
        print(f"\n🔬 Simulating {len(events)} events with {delay_between_events}s delay between each")

        for i, event_data in enumerate(events):
            event = MockWebSocketEvent(event_data['type'], event_data)
            self.event_received_times.append(time.time())

            # Simulate the callback being called (as in agent_cli.py)
            await self.event_callback(event)

            # Simulate delay between events from server
            if i < len(events) - 1:
                await asyncio.sleep(delay_between_events)

    async def event_callback(self, event: MockWebSocketEvent):
        """
        Callback that simulates what happens in agent_cli.py
        This is where the potential batching issue occurs
        """
        self.received_events.append(event)

        # Simulate display/rendering logic
        await self.display_event(event)

    async def display_event(self, event: MockWebSocketEvent):
        """Simulate event display with potential blocking"""
        display_time = time.time()
        self.display_times.append(display_time)

        # Simulate some async processing that might cause batching
        # This represents the display logic in _receive_events callbacks
        if event.type == "agent_thinking":
            # Simulate starting a spinner or other UI element
            await asyncio.sleep(0.1)  # Small async delay

        print(f"  [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Event displayed: {event.type}")

    def analyze_results(self):
        """Analyze if events were batched or streamed immediately"""
        print("\n📊 Analysis Results:")
        print("=" * 60)

        if len(self.display_times) < 2:
            print("❌ Not enough events to analyze")
            return False

        # Calculate time differences between displays
        display_gaps = []
        for i in range(1, len(self.display_times)):
            gap = self.display_times[i] - self.display_times[i-1]
            display_gaps.append(gap)

        avg_gap = sum(display_gaps) / len(display_gaps)
        max_gap = max(display_gaps)
        min_gap = min(display_gaps)

        print(f"Events received: {len(self.received_events)}")
        print(f"Average gap between displays: {avg_gap:.3f}s")
        print(f"Max gap: {max_gap:.3f}s")
        print(f"Min gap: {min_gap:.3f}s")

        # Check if events were batched (very small gaps between most events)
        batched_threshold = 0.05  # Less than 50ms suggests batching
        small_gaps = [g for g in display_gaps if g < batched_threshold]
        batch_ratio = len(small_gaps) / len(display_gaps) if display_gaps else 0

        print(f"Small gap ratio: {batch_ratio:.2%} (gaps < {batched_threshold}s)")

        is_batched = batch_ratio > 0.7  # If >70% of gaps are tiny, likely batched

        if is_batched:
            print("\n❌ ISSUE DETECTED: Events appear to be batched!")
            print("   Events are being displayed all at once rather than streaming.")
        else:
            print("\n✅ PASS: Events are being displayed as they arrive (streaming)")

        return not is_batched

async def test_immediate_display():
    """Test that events are displayed immediately as they arrive"""
    print("\n" + "="*70)
    print("TEST 1: Immediate Display (Expected Behavior)")
    print("="*70)

    test = EventBatchingTest()

    # Simulate multiple events arriving over time
    events = [
        {"type": "connection_established", "data": {"user_id": "test-user"}},
        {"type": "agent_started", "data": {"agent": "TestAgent"}},
        {"type": "agent_thinking", "data": {"thought": "Processing request..."}},
        {"type": "tool_executing", "data": {"tool": "WebSearch"}},
        {"type": "tool_completed", "data": {"tool": "WebSearch", "status": "success"}},
        {"type": "agent_completed", "data": {"status": "success"}}
    ]

    await test.simulate_websocket_stream(events, delay_between_events=0.5)

    success = test.analyze_results()
    return success

async def test_with_async_processing():
    """Test with async processing in callbacks that might cause batching"""
    print("\n" + "="*70)
    print("TEST 2: With Async Processing (Potential Batching Issue)")
    print("="*70)

    class BatchingEventTest(EventBatchingTest):
        async def display_event(self, event: MockWebSocketEvent):
            """Simulate problematic async processing that causes batching"""
            display_time = time.time()
            self.display_times.append(display_time)

            # Simulate heavier async processing that might block
            # This could represent complex UI updates, spinner management, etc.
            if event.type in ["agent_thinking", "tool_executing"]:
                # Longer async operations that might cause queuing
                await asyncio.sleep(0.3)
            else:
                await asyncio.sleep(0.05)

            print(f"  [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Event displayed: {event.type}")

    test = BatchingEventTest()

    events = [
        {"type": "connection_established", "data": {"user_id": "test-user"}},
        {"type": "agent_started", "data": {"agent": "TestAgent"}},
        {"type": "agent_thinking", "data": {"thought": "Processing request..."}},
        {"type": "tool_executing", "data": {"tool": "WebSearch"}},
        {"type": "tool_completed", "data": {"tool": "WebSearch", "status": "success"}},
        {"type": "agent_completed", "data": {"status": "success"}}
    ]

    await test.simulate_websocket_stream(events, delay_between_events=0.2)

    success = test.analyze_results()
    return success

async def test_concurrent_display():
    """Test fix: Using asyncio.create_task for non-blocking display"""
    print("\n" + "="*70)
    print("TEST 3: Concurrent Display (Proposed Fix)")
    print("="*70)

    class ConcurrentEventTest(EventBatchingTest):
        async def event_callback(self, event: MockWebSocketEvent):
            """Fixed callback that doesn't block on display"""
            self.received_events.append(event)

            # Create task for display instead of awaiting it
            # This allows the next event to be processed immediately
            asyncio.create_task(self.display_event(event))

            # Small yield to allow task scheduling
            await asyncio.sleep(0)

    test = ConcurrentEventTest()

    events = [
        {"type": "connection_established", "data": {"user_id": "test-user"}},
        {"type": "agent_started", "data": {"agent": "TestAgent"}},
        {"type": "agent_thinking", "data": {"thought": "Processing request..."}},
        {"type": "tool_executing", "data": {"tool": "WebSearch"}},
        {"type": "tool_completed", "data": {"tool": "WebSearch", "status": "success"}},
        {"type": "agent_completed", "data": {"status": "success"}}
    ]

    await test.simulate_websocket_stream(events, delay_between_events=0.5)

    # Give tasks time to complete
    await asyncio.sleep(1)

    success = test.analyze_results()
    return success

async def main():
    """Run all tests"""
    print("\n" + "🚀 " + "="*68)
    print("  EVENT BATCHING REGRESSION TEST SUITE")
    print("  Testing client-side event display streaming vs batching")
    print("="*70)

    results = []

    # Test 1: Expected immediate display behavior
    result1 = await test_immediate_display()
    results.append(("Immediate Display", result1))

    # Test 2: Problematic async processing
    result2 = await test_with_async_processing()
    results.append(("With Async Processing", result2))

    # Test 3: Proposed fix with concurrent display
    result3 = await test_concurrent_display()
    results.append(("Concurrent Display (Fix)", result3))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(r[1] for r in results)

    print("\n" + "="*70)
    if all_passed:
        print("✅ All tests passed - No batching issues detected")
    else:
        print("❌ Some tests failed - Batching issue confirmed")
        print("\nRECOMMENDATION:")
        print("  The issue is likely in the await callback(event) call in receive_events.")
        print("  Consider using asyncio.create_task() for the callback to avoid blocking")
        print("  the event loop while processing display logic.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())