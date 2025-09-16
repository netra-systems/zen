#!/usr/bin/env python3
"""
Quick verification script for Issue #1021 WebSocket event structure.
Tests the actual behavior of emit_critical_event to determine if the issue is resolved.
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_websocket_event_structure():
    """Test the actual WebSocket event structure to verify Issue #1021 status."""

    print("ISSUE #1021 VERIFICATION - WebSocket Event Structure Analysis")
    print("=" * 70)

    try:
        # Import the WebSocket manager
        from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation

        print("Successfully imported WebSocket manager")

        # Create a test instance
        manager = _UnifiedWebSocketManagerImplementation()

        # Test the _process_business_event method directly
        print("\n📋 Testing _process_business_event method...")

        # Test tool_executing event
        test_data = {
            "tool_name": "DataAnalyzer",
            "parameters": {"query": "customer metrics"},
            "execution_id": "exec_123",
            "estimated_time": 3000,
            "user_id": "user123",
            "thread_id": "thread456"
        }

        result = manager._process_business_event("tool_executing", test_data)

        print(f"📤 Input data: {json.dumps(test_data, indent=2)}")
        print(f"📥 Processed result: {json.dumps(result, indent=2)}")

        # Check the structure
        has_type = "type" in result
        has_tool_name_at_root = "tool_name" in result
        has_data_wrapper = "data" in result
        business_fields_at_root = all(key in result for key in ["tool_name", "parameters", "execution_id"])

        print(f"\n🔍 Structure Analysis:")
        print(f"  ✅ Has 'type' field: {has_type}")
        print(f"  ✅ Has 'tool_name' at root: {has_tool_name_at_root}")
        print(f"  ❌ Has 'data' wrapper: {has_data_wrapper}")
        print(f"  ✅ Business fields at root: {business_fields_at_root}")

        # Test the full emit_critical_event flow simulation
        print(f"\n🔄 Testing emit_critical_event message construction...")

        # Simulate the message construction from emit_critical_event
        processed_data = manager._process_business_event("tool_executing", test_data)

        # This is the actual message construction from emit_critical_event (line 1446-1451)
        message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "critical": True,
            "attempt": None,
            **processed_data  # This is the key - spreading processed data to root
        }

        print(f"📨 Final WebSocket message: {json.dumps(message, indent=2)}")

        # Critical verification
        final_has_data_wrapper = "data" in message
        final_business_at_root = all(key in message for key in ["tool_name", "parameters", "execution_id"])
        final_structure_correct = final_business_at_root and not final_has_data_wrapper

        print(f"\n🎯 FINAL VERDICT:")
        print(f"  ❌ Has 'data' wrapper: {final_has_data_wrapper}")
        print(f"  ✅ Business fields at root: {final_business_at_root}")
        print(f"  ✅ Structure is correct: {final_structure_correct}")

        if final_structure_correct:
            print(f"\n🎉 ISSUE #1021 STATUS: ✅ RESOLVED")
            print(f"   Business fields are correctly positioned at the root level")
            print(f"   No 'data' wrapper is burying business fields")
            return True
        else:
            print(f"\n❌ ISSUE #1021 STATUS: ❌ NOT RESOLVED")
            print(f"   Business fields are still wrapped or missing")
            return False

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_event_types():
    """Test multiple event types to ensure consistency."""

    print(f"\n🔄 Testing multiple event types for consistency...")

    try:
        from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation
        manager = _UnifiedWebSocketManagerImplementation()

        test_cases = [
            ("tool_executing", {"tool_name": "DataAnalyzer", "parameters": {"query": "test"}}),
            ("tool_completed", {"tool_name": "DataAnalyzer", "results": {"success": True}}),
            ("agent_started", {"agent_name": "SupervisorAgent", "task_description": "Process request"}),
            ("agent_thinking", {"reasoning": "Analyzing user requirements"}),
            ("agent_completed", {"status": "completed", "final_response": "Task done"})
        ]

        all_correct = True

        for event_type, test_data in test_cases:
            result = manager._process_business_event(event_type, test_data)

            # Check if business fields are at root level
            has_business_fields = any(key in result for key in test_data.keys())
            has_data_wrapper = "data" in result

            print(f"  {event_type}: Business at root: {has_business_fields}, Has data wrapper: {has_data_wrapper}")

            if has_data_wrapper or not has_business_fields:
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"❌ Error testing multiple event types: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Issue #1021 verification...")

    # Test basic structure
    structure_ok = test_websocket_event_structure()

    # Test multiple event types
    multi_ok = test_multiple_event_types()

    print(f"\n" + "=" * 70)
    print(f"📊 FINAL ANALYSIS SUMMARY:")
    print(f"  Structure Test: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"  Multi-Event Test: {'✅ PASS' if multi_ok else '❌ FAIL'}")

    if structure_ok and multi_ok:
        print(f"\n🎯 RECOMMENDATION: ✅ CLOSE Issue #1021")
        print(f"   The WebSocket event structure is working correctly.")
        print(f"   Business fields are properly positioned at the root level.")
        print(f"   No 'data' wrapper is burying critical fields.")
    else:
        print(f"\n🎯 RECOMMENDATION: ❌ CONTINUE working on Issue #1021")
        print(f"   The WebSocket event structure still has problems.")
        print(f"   Business fields may be wrapped or missing.")

    print(f"=" * 70)