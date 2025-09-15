#!/usr/bin/env python3
"""
Quick test to validate the WebSocket event routing fix.
"""

import asyncio
import json
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.types import get_frontend_message_type

async def test_agent_event_preservation():
    """Test that agent events are preserved correctly."""

    # Test the get_frontend_message_type function directly
    agent_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]

    print("Testing get_frontend_message_type preservation:")
    for event in agent_events:
        result = get_frontend_message_type(event)
        print(f"  {event} -> {result} (preserved: {result == event})")

    # Test message router preparation
    router = MessageRouter()

    print("\nTesting message preparation with agent events:")
    for event_type in agent_events:
        raw_message = {
            "type": event_type,
            "user_id": "test_user",
            "thread_id": "test_thread",
            "timestamp": 1234567890
        }

        prepared_message = await router._prepare_message(raw_message)
        print(f"  Raw: {event_type}")
        print(f"  Prepared type: {prepared_message.type}")
        print(f"  Original preserved in payload: {'original_agent_event_type' in raw_message}")
        if 'original_agent_event_type' in raw_message:
            print(f"  Preserved value: {raw_message['original_agent_event_type']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_agent_event_preservation())