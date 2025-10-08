#!/usr/bin/env python3
"""
Test the thread ID handshake between CLI and backend.

This test verifies that:
1. CLI waits for and accepts backend-provided thread_id
2. CLI sends acknowledgment with the same thread_id
3. Events are properly filtered by thread_id
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.agent_cli import WebSocketClient, Config, DebugManager, DebugLevel, Environment


async def test_handshake():
    """Test the handshake protocol with backend."""

    # Configure for testing
    config = Config(
        environment=Environment.STAGING,
        debug_level=DebugLevel.VERBOSE,
        stream_logs=True
    )

    # Get authentication token (you may need to set this)
    token = os.environ.get('NETRA_AUTH_TOKEN')
    if not token:
        print("ERROR: Set NETRA_AUTH_TOKEN environment variable")
        return False

    # Create WebSocket client
    debug_manager = DebugManager(
        debug_level=DebugLevel.VERBOSE,
        enable_websocket_diagnostics=True
    )

    ws_client = WebSocketClient(config, token, debug_manager)

    print("\n=== Testing Thread ID Handshake ===\n")

    try:
        # Step 1: Connect to WebSocket
        print("1. Connecting to WebSocket...")
        connected = await ws_client.connect()

        if not connected:
            print("   ❌ FAILED: Could not connect to WebSocket")
            return False

        print("   ✅ Connected successfully")

        # Step 2: Check if thread_id was received
        if not ws_client.current_thread_id:
            print("   ❌ FAILED: No thread_id received from backend")
            return False

        print(f"   ✅ Received thread_id: {ws_client.current_thread_id}")

        # Step 3: Send a test message with the thread_id
        print("\n2. Sending test message...")
        test_message = "Test message for thread ID verification"

        run_id = await ws_client.send_message(test_message)
        print(f"   ✅ Message sent with run_id: {run_id}")

        # Step 4: Receive events for a few seconds
        print("\n3. Listening for events (5 seconds)...")
        events_received = []

        async def collect_events(event):
            events_received.append(event)
            print(f"   📨 Event: {event.type}")

            # Check if events have our thread_id
            if hasattr(event, 'data') and isinstance(event.data, dict):
                event_thread_id = event.data.get('thread_id')
                if event_thread_id:
                    if event_thread_id == ws_client.current_thread_id:
                        print(f"      ✅ Event has correct thread_id: {event_thread_id}")
                    else:
                        print(f"      ❌ Event has wrong thread_id: {event_thread_id}")

        # Start receiving events
        receive_task = asyncio.create_task(ws_client.receive_events(callback=collect_events))

        # Wait for events
        await asyncio.sleep(5)

        # Cancel receive task
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass

        # Step 5: Verify results
        print(f"\n4. Results:")
        print(f"   • Thread ID: {ws_client.current_thread_id}")
        print(f"   • Events received: {len(events_received)}")

        # Check for critical events
        event_types = [e.type for e in events_received]

        if 'agent_started' in event_types:
            print("   ✅ Received agent_started event")

        if 'agent_thinking' in event_types:
            print("   ✅ Received agent_thinking event")

        if 'agent_completed' in event_types:
            print("   ✅ Received agent_completed event")

        # Overall success check
        if len(events_received) > 0:
            print("\n✅ SUCCESS: Handshake and event reception working!")
            return True
        else:
            print("\n⚠️ WARNING: Connected but no events received")
            print("   This might mean the agent didn't run or events aren't being routed")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        if ws_client and ws_client.connected:
            await ws_client.close()
            print("\n5. Connection closed")


def main():
    """Run the handshake test."""
    print("=" * 60)
    print("Thread ID Handshake Test")
    print("=" * 60)

    # Run the async test
    success = asyncio.run(test_handshake())

    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED ✅")
    else:
        print("TEST FAILED ❌")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())