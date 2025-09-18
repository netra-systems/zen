#!/usr/bin/env python3
"""
Issue #1021 Fix Validation Test

This script validates that the WebSocket payload wrapper fix is working correctly
by actually calling the WebSocket manager and checking the message structure.
"""

import asyncio
import json
import sys
import os

# Add the netra_backend to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


async def test_payload_wrapper_fix():
    """Test that the WebSocket manager now sends payload-wrapped events."""

    print("🔍 Testing Issue #1021 Fix: WebSocket Payload Wrapper")
    print("=" * 60)

    # Create a manager instance
    manager = UnifiedWebSocketManager()

    # Mock connection tracking (normally done during WebSocket connection)
    user_id = "test_user_123"
    mock_websocket = type('MockWebSocket', (), {
        'send': lambda self, data: print(f"📤 SENT: {data}"),
        'closed': False
    })()

    # Add the connection to the manager
    manager.connections[user_id] = mock_websocket

    # Capture sent messages
    sent_messages = []

    def capture_send(data):
        """Capture sent messages for analysis."""
        message = json.loads(data)
        sent_messages.append(message)
        print(f"📤 CAPTURED MESSAGE: {json.dumps(message, indent=2)}")

    # Override the send method to capture messages
    mock_websocket.send = capture_send

    # Test 1: tool_executing event
    print("\n🧪 Test 1: tool_executing event")
    print("-" * 40)

    test_data = {
        "tool_name": "aws_cost_analyzer",
        "metadata": {
            "parameters": {"region": "us-east-1"},
            "description": "Analyzing costs"
        },
        "status": "executing"
    }

    await manager.emit_critical_event(user_id, "tool_executing", test_data)

    # Analyze the sent message
    if sent_messages:
        message = sent_messages[-1]
        print(f"\n📊 ANALYSIS:")
        print(f"   Message Type: {message.get('type')}")
        print(f"   Has 'payload' field: {'payload' in message}")
        print(f"   Has 'data' field: {'data' in message}")

        if 'payload' in message:
            payload = message['payload']
            print(f"   ✅ PAYLOAD FOUND!")
            print(f"   Tool Name: {payload.get('tool_name')}")
            print(f"   Frontend can access: payload.tool_name = {payload.get('tool_name')}")

            # Test frontend-compatible access pattern
            try:
                frontend_tool_name = message['payload']['tool_name']
                print(f"   ✅ FRONTEND ACCESS SUCCESS: {frontend_tool_name}")
                print(f"   🎉 ISSUE #1021 FIX VALIDATED!")
                return True
            except KeyError as e:
                print(f"   ❌ FRONTEND ACCESS FAILED: {e}")
                return False
        else:
            print(f"   ❌ NO PAYLOAD FIELD - Fix not working")
            print(f"   Available fields: {list(message.keys())}")
            return False
    else:
        print("   ❌ NO MESSAGE SENT")
        return False


async def test_multiple_event_types():
    """Test that the fix works for different event types."""

    print("\n\n🧪 Test 2: Multiple Event Types")
    print("-" * 40)

    manager = UnifiedWebSocketManager()
    user_id = "test_user_456"

    sent_messages = []

    def capture_send(data):
        message = json.loads(data)
        sent_messages.append(message)

    mock_websocket = type('MockWebSocket', (), {
        'send': capture_send,
        'closed': False
    })()

    manager.connections[user_id] = mock_websocket

    # Test different event types
    test_events = [
        ("agent_started", {"agent_name": "supervisor", "task": "analysis"}),
        ("agent_thinking", {"thought": "analyzing data", "step": 1}),
        ("tool_completed", {"tool_name": "DataAnalyzer", "result": "success"}),
        ("agent_completed", {"agent_name": "supervisor", "final_response": "done"})
    ]

    all_passed = True

    for event_type, data in test_events:
        await manager.emit_critical_event(user_id, event_type, data)

        if sent_messages:
            message = sent_messages[-1]
            has_payload = 'payload' in message
            print(f"   {event_type}: {'✅ HAS PAYLOAD' if has_payload else '❌ NO PAYLOAD'}")

            if not has_payload:
                all_passed = False
        else:
            print(f"   {event_type}: ❌ NO MESSAGE SENT")
            all_passed = False

    return all_passed


async def main():
    """Run all validation tests."""

    print("🚀 Starting Issue #1021 Fix Validation")
    print("=" * 60)

    try:
        # Test 1: Basic payload wrapper functionality
        test1_passed = await test_payload_wrapper_fix()

        # Test 2: Multiple event types
        test2_passed = await test_multiple_event_types()

        print("\n" + "=" * 60)
        print("📋 FINAL RESULTS:")
        print(f"   Test 1 (Payload Wrapper): {'✅ PASS' if test1_passed else '❌ FAIL'}")
        print(f"   Test 2 (Multiple Events): {'✅ PASS' if test2_passed else '❌ FAIL'}")

        if test1_passed and test2_passed:
            print(f"\n🎉 ISSUE #1021 FIX VALIDATION: ✅ SUCCESS!")
            print(f"   Backend now sends payload-wrapped events")
            print(f"   Frontend can access business fields via payload.*")
            print(f"   WebSocket event structure mismatch RESOLVED")
            return True
        else:
            print(f"\n❌ ISSUE #1021 FIX VALIDATION: FAILED")
            print(f"   Fix needs additional work")
            return False

    except Exception as e:
        print(f"\n💥 VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)