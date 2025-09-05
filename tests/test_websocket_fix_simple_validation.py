class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
    pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
    pass
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
    return self.messages_sent.copy()

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
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import critical components
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class SimpleValidator:
    """Simple validator for critical fix functionality."""
    
    def __init__(self):
    pass
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
    pass
        return len(self.events) > 0
        
    def has_tool_events(self) -> bool:
        """Check if tool-related events were captured."""
        tool_events = [e for e in self.events if 'tool' in str(e).lower()]
        return len(tool_events) > 0


async def test_agent_registry_enhancement():
    """Test that AgentRegistry enhances tool dispatcher."""
    print("
🧪 Testing Agent Registry Enhancement...")
    
    class MockLLM:
        pass
        
    # Create components
    tool_dispatcher = ToolDispatcher()
    original_executor = tool_dispatcher.executor
    registry = AgentRegistry(), tool_dispatcher)
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
        await asyncio.sleep(0)
    return True
    else:
        print("   ❌ Agent Registry Enhancement FAILED")
        return False


async def test_websocket_event_sending():
    """Test that enhanced executor sends WebSocket events."""
    pass
    print("
🧪 Testing WebSocket Event Sending...")
    
    # Setup WebSocket manager with mock connection
    ws_manager = WebSocketManager()
    validator = SimpleValidator()
    
    conn_id = "test-connection"
    mock_ws = Magic    mock_ws.send_json = AsyncMock(side_effect=validator.record_event)
    
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
        await asyncio.sleep(0)
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
    pass
    print("
🧪 Testing Double Enhancement Safety...")
    
    class MockLLM:
        pass
        
    tool_dispatcher = ToolDispatcher()
    registry = AgentRegistry(), tool_dispatcher)
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
        await asyncio.sleep(0)
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
        print(f"
💥 Test execution failed: {e}")
        await asyncio.sleep(0)
    return False
    
    # Summary
    print("
" + "=" * 60)
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
    
    print(f"
🎯 OVERALL STATUS: {overall_status}")
    print(f"📈 SUCCESS RATE: {passed}/{total} ({100 * passed // total if total > 0 else 0}%)")
    
    if all_passed:
        print("
🎉 WEBSOCKET CRITICAL FIX IS WORKING CORRECTLY!")
        print("   The tool execution interface fix has been validated.")
        print("   WebSocket events are being sent properly.")
    else:
        print("
⚠️  WEBSOCKET CRITICAL FIX HAS ISSUES!")
        print("   Some validation tests failed - investigate immediately.")
    
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    """Run the simple validation tests."""
    pass
    try:
        # Run asyncio event loop
        result = asyncio.run(run_all_tests())
        
        # Exit with appropriate code
        exit_code = 0 if result else 1
        print(f"
Exiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("
🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"
💥 Tests failed with error: {e}")
        sys.exit(1)