#!/usr/bin/env python3
"""
Standalone test to verify WebSocket API signatures match implementation.
This test focuses only on API signature validation without complex real services.
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add project to path
project_root = os.path.abspath('.')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager

class TestWebSocketManager:
    """Simple test WebSocket manager that doesn't require real connections."""
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Mock sending message to thread."""
        print(f"Would send to {thread_id}: {message.get('type', 'unknown')}")
        return True
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user connection."""
        print(f"Would connect user {user_id} to thread {thread_id}")
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user disconnection."""
        print(f"Would disconnect user {user_id} from thread {thread_id}")

async def test_websocket_api_signatures():
    """Test WebSocket API signatures against actual usage patterns."""
    print("=" * 80)
    print("WEBSOCKET API SIGNATURE VALIDATION")
    print("=" * 80)
    
    # Create test components
    ws_manager = TestWebSocketManager()
    notifier = WebSocketNotifier(ws_manager)
    
    # Create test context matching AgentExecutionContext constructor
    context = AgentExecutionContext(
        run_id="test-123",
        thread_id="thread-456", 
        user_id="user-789",
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    )
    
    print(f"Created context: {context}")
    
    # Test 1: Basic required methods
    print("\n1. Testing basic required methods...")
    
    methods_to_test = [
        ("send_agent_started", lambda: notifier.send_agent_started(context)),
        ("send_agent_thinking", lambda: notifier.send_agent_thinking(context, "Processing...")),
        ("send_partial_result", lambda: notifier.send_partial_result(context, "Partial result")),
        ("send_tool_executing", lambda: notifier.send_tool_executing(context, "search_tool")),
        ("send_tool_completed", lambda: notifier.send_tool_completed(context, "search_tool", {"status": "success"})),
        ("send_final_report", lambda: notifier.send_final_report(context, {"results": "complete"}, 1500.0)),
        ("send_agent_completed", lambda: notifier.send_agent_completed(context, {"success": True}, 2000.0))
    ]
    
    results = {}
    
    for method_name, method_call in methods_to_test:
        try:
            await method_call()
            results[method_name] = "✅ PASSED"
            print(f"  ✅ {method_name}: OK")
        except Exception as e:
            results[method_name] = f"❌ FAILED: {e}"
            print(f"  ❌ {method_name}: {e}")
    
    # Test 2: Enhanced method signatures
    print("\n2. Testing enhanced method signatures...")
    
    enhanced_tests = [
        ("send_agent_thinking with progress", 
         lambda: notifier.send_agent_thinking(
             context, "Analyzing data...", 
             step_number=2, 
             progress_percentage=50.0, 
             estimated_remaining_ms=3000,
             current_operation="data_analysis"
         )),
        ("send_tool_executing with extras", 
         lambda: notifier.send_tool_executing(
             context, "analyze_data", 
             tool_purpose="Process user data",
             estimated_duration_ms=2000,
             parameters_summary="dataset=user_input, mode=analyze"
         )),
        ("send_partial_result as complete", 
         lambda: notifier.send_partial_result(context, "Final output", is_complete=True)),
    ]
    
    for test_name, test_call in enhanced_tests:
        try:
            await test_call()
            results[test_name] = "✅ PASSED"
            print(f"  ✅ {test_name}: OK")
        except Exception as e:
            results[test_name] = f"❌ FAILED: {e}"
            print(f"  ❌ {test_name}: {e}")
    
    # Test 3: Error handling methods
    print("\n3. Testing error handling methods...")
    
    error_tests = [
        ("send_fallback_notification", 
         lambda: notifier.send_fallback_notification(context, "timeout_fallback")),
        ("send_agent_error", 
         lambda: notifier.send_agent_error(
             context, 
             "Processing failed", 
             error_type="timeout",
             error_details={"code": 408},
             recovery_suggestions=["Try again", "Check input"],
             is_recoverable=True,
             estimated_retry_delay_ms=5000
         )),
    ]
    
    for test_name, test_call in error_tests:
        try:
            await test_call()
            results[test_name] = "✅ PASSED"
            print(f"  ✅ {test_name}: OK")
        except Exception as e:
            results[test_name] = f"❌ FAILED: {e}"
            print(f"  ❌ {test_name}: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for result in results.values() if result.startswith("✅"))
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL API SIGNATURES ARE COMPATIBLE!")
        return True
    else:
        print("❌ API SIGNATURE MISMATCHES DETECTED")
        for method, result in results.items():
            if result.startswith("❌"):
                print(f"  - {method}: {result}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_api_signatures())
    sys.exit(0 if success else 1)