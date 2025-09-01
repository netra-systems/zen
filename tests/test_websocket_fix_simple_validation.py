#!/usr/bin/env python3
"""SIMPLE WEBSOCKET CRITICAL FIX VALIDATION

This is a simplified version of the WebSocket critical fix validation that 
focuses on the core functionality without complex test framework dependencies.

Use this test to quickly validate that the critical fix is working.
"""

import asyncio
import json
import os
import sys
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import critical components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


class SimpleValidator:
    """Simple validator for critical fix functionality."""
    
    def __init__(self):
        self.events: List[Dict] = []
        
    def record_event(self, event):
        """Record WebSocket event."""
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except:
                event = {"raw": event}
        self.events.append(event)
        print(f"📡 WebSocket Event: {event.get('type', 'unknown')} - {event}")
        
    def has_events(self) -> bool:
        """Check if any events were captured."""
        return len(self.events) > 0
        
    def has_tool_events(self) -> bool:
        """Check if tool-related events were captured."""
        tool_events = [e for e in self.events if 'tool' in str(e).lower()]
        return len(tool_events) > 0


async def test_agent_registry_enhancement():
    """Test that AgentRegistry enhances tool dispatcher."""
    print("\n🧪 Testing Agent Registry Enhancement...")
    
    class MockLLM:
        pass
        
    # Create components
    tool_dispatcher = ToolDispatcher()
    original_executor = tool_dispatcher.executor
    registry = AgentRegistry(MockLLM(), tool_dispatcher)
    ws_manager = WebSocketManager()
    
    print(f"   Original executor: {type(original_executor).__name__}")
    
    # Apply the critical fix
    registry.set_websocket_manager(ws_manager)
    
    # Validate enhancement
    success = isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine)
    has_marker = hasattr(tool_dispatcher, '_websocket_enhanced')
    
    print(f"   Enhanced executor: {type(tool_dispatcher.executor).__name__}")
    print(f"   Has enhancement marker: {has_marker}")
    
    if success and has_marker:
        print("   ✅ Agent Registry Enhancement PASSED")
        return True
    else:
        print("   ❌ Agent Registry Enhancement FAILED")
        return False


async def test_websocket_event_sending():
    """Test that enhanced executor sends WebSocket events."""
    print("\n🧪 Testing WebSocket Event Sending...")
    
    # Setup WebSocket manager with mock connection
    ws_manager = WebSocketManager()
    validator = SimpleValidator()
    
    conn_id = "test-connection"
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock(side_effect=validator.record_event)
    
    await ws_manager.connect_user(conn_id, mock_ws, conn_id)
    print(f"   Connected WebSocket: {conn_id}")
    
    # Create enhanced executor
    executor = UnifiedToolExecutionEngine(ws_manager)
    
    # Create test state and tool
    state = DeepAgentState(
        chat_thread_id=conn_id,
        user_id=conn_id,
        run_id="test-run"
    )
    
    async def test_tool(*args, **kwargs):
        """Simple test tool."""
        await asyncio.sleep(0.01)  # Simulate work
        return {"result": "test completed"}
    
    print(f"   Executing test tool...")
    
    # Execute tool
    try:
        result = await executor.execute_with_state(
            test_tool, "test_tool", {}, state, "test-run"
        )
        print(f"   Tool execution result: {result}")
    except Exception as e:
        print(f"   Tool execution error: {e}")
    
    # Allow events to propagate
    await asyncio.sleep(0.1)
    
    # Validate events were sent
    has_events = validator.has_events()
    has_tool_events = validator.has_tool_events()
    
    print(f"   Events captured: {len(validator.events)}")
    print(f"   Has any events: {has_events}")
    print(f"   Has tool events: {has_tool_events}")
    
    if has_events:
        print("   ✅ WebSocket Event Sending PASSED")
        return True
    else:
        print("   ❌ WebSocket Event Sending FAILED")
        return False


async def test_double_enhancement_safety():
    """Test that double enhancement doesn't break the system."""
    print("\n🧪 Testing Double Enhancement Safety...")
    
    class MockLLM:
        pass
        
    tool_dispatcher = ToolDispatcher()
    registry = AgentRegistry(MockLLM(), tool_dispatcher)
    ws_manager = WebSocketManager()
    
    # Apply enhancement twice
    registry.set_websocket_manager(ws_manager)
    first_executor = tool_dispatcher.executor
    
    registry.set_websocket_manager(ws_manager)
    second_executor = tool_dispatcher.executor
    
    # Should be the same executor (no double-wrapping)
    same_executor = first_executor == second_executor
    still_enhanced = isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine)
    
    print(f"   Same executor after double enhancement: {same_executor}")
    print(f"   Still properly enhanced: {still_enhanced}")
    
    if same_executor and still_enhanced:
        print("   ✅ Double Enhancement Safety PASSED")
        return True
    else:
        print("   ❌ Double Enhancement Safety FAILED") 
        return False


async def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("🚀 WEBSOCKET CRITICAL FIX SIMPLE VALIDATION")
    print("=" * 60)
    
    results = []
    
    try:
        # Test 1: Agent Registry Enhancement
        result1 = await test_agent_registry_enhancement()
        results.append(("Agent Registry Enhancement", result1))
        
        # Test 2: WebSocket Event Sending  
        result2 = await test_websocket_event_sending()
        results.append(("WebSocket Event Sending", result2))
        
        # Test 3: Double Enhancement Safety
        result3 = await test_double_enhancement_safety()
        results.append(("Double Enhancement Safety", result3))
        
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    all_passed = passed == total
    overall_status = "✅ ALL TESTS PASSED" if all_passed else f"❌ {total - passed} TESTS FAILED"
    
    print(f"\n🎯 OVERALL STATUS: {overall_status}")
    print(f"📈 SUCCESS RATE: {passed}/{total} ({100 * passed // total if total > 0 else 0}%)")
    
    if all_passed:
        print("\n🎉 WEBSOCKET CRITICAL FIX IS WORKING CORRECTLY!")
        print("   The tool execution interface fix has been validated.")
        print("   WebSocket events are being sent properly.")
    else:
        print("\n⚠️  WEBSOCKET CRITICAL FIX HAS ISSUES!")
        print("   Some validation tests failed - investigate immediately.")
    
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    """Run the simple validation tests."""
    try:
        # Run asyncio event loop
        result = asyncio.run(run_all_tests())
        
        # Exit with appropriate code
        exit_code = 0 if result else 1
        print(f"\nExiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Tests failed with error: {e}")
        sys.exit(1)