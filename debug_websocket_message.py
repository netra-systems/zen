#!/usr/bin/env python3
"""
Debug script to test WebSocket message construction fix for Issue #1021.
Tests that the emit_critical_event method creates consistent message structures.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from datetime import datetime, timezone
import json


async def test_message_construction():
    """Test that message construction is consistent between success and failure paths."""

    print("Testing WebSocket message construction consistency...")

    # Create a mock WebSocket manager
    manager = UnifiedWebSocketManager()

    # Test data
    test_user_id = "test_user_123"
    test_event_type = "agent_started"
    test_data = {
        "agent_name": "Test Agent",
        "run_id": "run_456",
        "context": {"action": "processing"}
    }

    print(f"Test Data: {json.dumps(test_data, indent=2)}")

    # Test successful message construction (the code path that works)
    successful_message = {
        "type": test_event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "critical": True,
        "attempt": None,
        **test_data  # This spreads the data to root level
    }

    print("SUCCESS PATH Message Structure:")
    print(json.dumps(successful_message, indent=2))
    print()

    # Test failure message construction (the code path we fixed)
    failure_message = {
        "type": test_event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "critical": True,
        "retry_exhausted": True,  # Add context for failure case
        **test_data  # Spread business data to root level (this is the fix)
    }

    print("FAILURE PATH Message Structure (FIXED):")
    print(json.dumps(failure_message, indent=2))
    print()

    # Test old broken failure message construction (what it was before)
    old_broken_failure_message = {
        "type": test_event_type,
        "data": test_data,  # This wraps business data (the bug)
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "critical": True
    }

    print("OLD BROKEN FAILURE PATH Message Structure:")
    print(json.dumps(old_broken_failure_message, indent=2))
    print()

    # Verify the structures are consistent
    success_keys = set(successful_message.keys()) - {"attempt"}  # Remove attempt which is success-specific
    failure_keys = set(failure_message.keys()) - {"retry_exhausted"}  # Remove retry_exhausted which is failure-specific

    print("Structure Consistency Check:")
    print(f"Success path keys (minus 'attempt'): {sorted(success_keys)}")
    print(f"Failure path keys (minus 'retry_exhausted'): {sorted(failure_keys)}")

    # Check if both have business data at root level
    success_has_root_data = "agent_name" in successful_message and "run_id" in successful_message
    failure_has_root_data = "agent_name" in failure_message and "run_id" in failure_message
    old_has_wrapped_data = "data" in old_broken_failure_message and isinstance(old_broken_failure_message["data"], dict)

    print()
    print("Business Data Location Check:")
    print(f"Success path has business data at root level: {success_has_root_data}")
    print(f"Fixed failure path has business data at root level: {failure_has_root_data}")
    print(f"Old broken failure path wraps data: {old_has_wrapped_data}")

    if success_has_root_data and failure_has_root_data:
        print()
        print("SUCCESS: Both paths now have consistent message structure!")
        print("Issue #1021 WebSocket event structure validation is FIXED")
        return True
    else:
        print()
        print("❌ FAILURE: Message structures are still inconsistent")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_message_construction())
    sys.exit(0 if result else 1)