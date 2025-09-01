#!/usr/bin/env python
"""Standalone WebSocket Agent Test - bypasses database dependencies.

This test focuses solely on WebSocket agent event integration without
requiring Docker services to be running.
"""

import asyncio
import sys
import os
import time
from typing import Dict, List, Any
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core imports
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine, enhance_tool_dispatcher_with_notifications
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager


class MockWebSocketManager:
    """Mock WebSocket manager that captures events for validation."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connections: Dict[str, Any] = {}
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message and simulate successful delivery."""
        self.messages.append({
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        })
        return True
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user connection."""
        self.connections[thread_id] = {'user_id': user_id, 'connected': True}
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user disconnection."""
        if thread_id in self.connections:
            self.connections[thread_id]['connected'] = False
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get all events for a specific thread."""
        return [msg for msg in self.messages if msg['thread_id'] == thread_id]
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for a thread in order."""
        return [msg['event_type'] for msg in self.messages if msg['thread_id'] == thread_id]
    
    def clear_messages(self):
        """Clear all recorded messages."""
        self.messages.clear()


class WebSocketEventValidator:
    """Validates that required WebSocket events are sent."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
    
    def record_event(self, event: Dict) -> None:
        """Record an event for validation."""
        event_type = event.get("type", "unknown")
        self.events.append(event)
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def validate_required_events(self) -> tuple[bool, List[str]]:
        """Validate that all required events are present."""
        failures = []
        
        # Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"Missing required events: {missing}")
        
        # Check event order (agent_started should be first)
        if self.events and self.events[0].get("type") != "agent_started":
            failures.append(f"First event was {self.events[0].get('type')}, not agent_started")
        
        # Check that tool events are paired
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        if tool_starts != tool_ends:
            failures.append(f"Unpaired tool events: {tool_starts} starts, {tool_ends} completions")
        
        return len(failures) == 0, failures
    
    def generate_report(self) -> str:
        """Generate validation report."""
        is_valid, failures = self.validate_required_events()
        
        report = [
            "\n" + "=" * 60,
            "WEBSOCKET EVENT VALIDATION REPORT",
            "=" * 60,
            f"Status: {'PASSED' if is_valid else 'FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Event Types: {len(self.event_counts)}",
            "",
            "Event Coverage:"
        ]
        
        for event in self.REQUIRED_EVENTS:
            count = self.event_counts.get(event, 0)
            status = "[OK]" if count > 0 else "[MISSING]"
            report.append(f"  {status} {event}: {count}")
        
        if failures:
            report.extend(["", "FAILURES:"] + [f"  - {f}" for f in failures])
        
        report.append("=" * 60)
        return "\n".join(report)


async def test_websocket_notifier_basic():
    """Test basic WebSocket notifier functionality."""
    print("\n[TEST] Testing WebSocket notifier basic functionality...")
    
    mock_ws = MockWebSocketManager()
    notifier = WebSocketNotifier(mock_ws)
    validator = WebSocketEventValidator()
    
    # Create test context
    context = AgentExecutionContext(
        run_id="test-123",
        thread_id="test-conn",
        user_id="test-user",
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    )
    
    # Test that notifier has required methods
    required_methods = [
        'send_agent_started',
        'send_agent_thinking',
        'send_tool_executing',
        'send_tool_completed',
        'send_agent_completed'
    ]
    
    for method in required_methods:
        if not hasattr(notifier, method):
            print(f"[FAIL] Missing method: {method}")
            return False
        if not callable(getattr(notifier, method)):
            print(f"[FAIL] Method not callable: {method}")
            return False
    
    # Test sending all required events
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "Processing request...")
    await notifier.send_tool_executing(context, "search_tool")
    await notifier.send_tool_completed(context, "search_tool", {"result": "success"})
    await notifier.send_agent_completed(context, {"success": True})
    
    # Validate events were captured
    events = mock_ws.get_events_for_thread("test-conn")
    for event in events:
        validator.record_event(event['message'])
    
    is_valid, failures = validator.validate_required_events()
    
    if is_valid:
        print("[PASS] WebSocket notifier basic test PASSED")
        print(f"   Captured {len(events)} events: {validator.event_counts}")
        return True
    else:
        print("[FAIL] WebSocket notifier basic test FAILED")
        for failure in failures:
            print(f"   - {failure}")
        return False


async def test_tool_dispatcher_enhancement():
    """Test that tool dispatcher gets enhanced with WebSocket notifications."""
    print("\n[TEST] Testing tool dispatcher enhancement...")
    
    mock_ws = MockWebSocketManager()
    dispatcher = ToolDispatcher()
    
    # Check initial state
    original_executor = dispatcher.executor
    
    # Enhance with WebSocket notifications
    enhance_tool_dispatcher_with_notifications(dispatcher, mock_ws)
    
    # Verify enhancement
    if dispatcher.executor == original_executor:
        print("[FAIL] Tool dispatcher executor was not replaced")
        return False
    
    # Import both types since they're both valid (UnifiedToolExecutionEngine is the new SSOT)
    from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
    
    if not isinstance(dispatcher.executor, (UnifiedToolExecutionEngine, UnifiedToolExecutionEngine)):
        print(f"[FAIL] Wrong executor type: {type(dispatcher.executor)}")
        return False
    
    if not hasattr(dispatcher, '_websocket_enhanced'):
        print("[FAIL] Missing enhancement marker")
        return False
    
    if not dispatcher._websocket_enhanced:
        print("[FAIL] Enhancement marker not set")
        return False
    
    print("[PASS] Tool dispatcher enhancement test PASSED")
    return True


async def test_agent_registry_websocket_integration():
    """Test that AgentRegistry properly integrates WebSocket manager."""
    print("\n[TEST] Testing AgentRegistry WebSocket integration...")
    
    class MockLLM:
        pass
    
    mock_ws = MockWebSocketManager()
    dispatcher = ToolDispatcher()
    registry = AgentRegistry(MockLLM(), dispatcher)
    
    # Set WebSocket manager - this should enhance the tool dispatcher
    registry.set_websocket_manager(mock_ws)
    
    # Import both types since they're both valid (UnifiedToolExecutionEngine is the new SSOT)
    from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
    
    # Verify tool dispatcher was enhanced
    if not isinstance(dispatcher.executor, (UnifiedToolExecutionEngine, UnifiedToolExecutionEngine)):
        print(f"[FAIL] Tool dispatcher not enhanced by AgentRegistry: {type(dispatcher.executor)}")
        return False
    
    print("[PASS] AgentRegistry WebSocket integration test PASSED")
    return True


async def test_execution_engine_initialization():
    """Test ExecutionEngine WebSocket initialization."""
    print("\n[TEST] Testing ExecutionEngine WebSocket initialization...")
    
    class MockLLM:
        pass
    
    mock_ws = MockWebSocketManager()
    registry = AgentRegistry(MockLLM(), ToolDispatcher())
    
    # Create ExecutionEngine with WebSocket manager
    engine = ExecutionEngine(registry, mock_ws)
    
    # Verify WebSocket components
    if not hasattr(engine, 'websocket_notifier'):
        print("[FAIL] Missing websocket_notifier attribute")
        return False
    
    if not isinstance(engine.websocket_notifier, WebSocketNotifier):
        print(f"[FAIL] Wrong websocket_notifier type: {type(engine.websocket_notifier)}")
        return False
    
    # Check for WebSocket methods on engine
    websocket_methods = ['send_agent_thinking', 'send_partial_result']
    for method in websocket_methods:
        if not hasattr(engine, method):
            print(f"[FAIL] Missing WebSocket method on engine: {method}")
            return False
    
    print("[PASS] ExecutionEngine WebSocket initialization test PASSED")
    return True


async def test_unified_tool_execution_events():
    """Test that enhanced tool execution sends WebSocket events."""
    print("\n[TEST] Testing enhanced tool execution WebSocket events...")
    
    mock_ws = MockWebSocketManager()
    validator = WebSocketEventValidator()
    
    # Create enhanced executor
    executor = UnifiedToolExecutionEngine(mock_ws)
    
    if not executor.websocket_notifier:
        print("[FAIL] Enhanced executor should have WebSocket notifier")
        return False
    
    # Create context for testing
    context = AgentExecutionContext(
        run_id="test-enhanced-123",
        thread_id="test-enhanced-conn",
        user_id="test-enhanced-user",
        agent_name="enhanced_agent",
        retry_count=0,
        max_retries=1
    )
    
    # Test direct notification capability
    await executor.websocket_notifier.send_tool_executing(context, "enhanced_tool")
    await executor.websocket_notifier.send_tool_completed(context, "enhanced_tool", {"result": "success"})
    
    # Verify events were sent
    events = mock_ws.get_events_for_thread("test-enhanced-conn")
    for event in events:
        validator.record_event(event['message'])
    
    if validator.event_counts.get("tool_executing", 0) == 0:
        print("[FAIL] No tool_executing event sent")
        return False
    
    if validator.event_counts.get("tool_completed", 0) == 0:
        print("[FAIL] No tool_completed event sent")
        return False
    
    print("[PASS] Enhanced tool execution WebSocket events test PASSED")
    print(f"   Sent events: {validator.event_counts}")
    return True


async def test_complete_agent_flow():
    """Test complete agent execution flow with WebSocket events."""
    print("\n[TEST] Testing complete agent execution flow...")
    
    mock_ws = MockWebSocketManager()
    validator = WebSocketEventValidator()
    
    # Create notifier for complete flow simulation
    notifier = WebSocketNotifier(mock_ws)
    
    # Create context
    context = AgentExecutionContext(
        run_id="flow-test-123",
        thread_id="flow-test-conn",
        user_id="flow-test-user",
        agent_name="supervisor_agent",
        retry_count=0,
        max_retries=1
    )
    
    # Simulate complete agent flow with multiple tools
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "Analyzing request...")
    
    # First tool
    await notifier.send_tool_executing(context, "search_knowledge")
    await notifier.send_tool_completed(context, "search_knowledge", {"results": "Found data"})
    
    # Second tool
    await notifier.send_tool_executing(context, "analyze_data")
    await notifier.send_tool_completed(context, "analyze_data", {"analysis": "Complete"})
    
    await notifier.send_agent_completed(context, {"success": True})
    
    # Validate complete flow
    events = mock_ws.get_events_for_thread("flow-test-conn")
    for event in events:
        validator.record_event(event['message'])
    
    is_valid, failures = validator.validate_required_events()
    
    if not is_valid:
        print("[FAIL] Complete agent flow test FAILED")
        for failure in failures:
            print(f"   - {failure}")
        print(validator.generate_report())
        return False
    
    # Additional validation for multiple tools
    if validator.event_counts.get("tool_executing", 0) < 2:
        print("[FAIL] Expected at least 2 tool executions")
        return False
    
    print("[PASS] Complete agent execution flow test PASSED")
    print(f"   Total events: {len(events)}, Types: {validator.event_counts}")
    return True


async def main():
    """Run all WebSocket agent integration tests."""
    print("[START] Starting WebSocket Agent Integration Tests")
    print("=" * 60)
    
    test_functions = [
        test_websocket_notifier_basic,
        test_tool_dispatcher_enhancement,
        test_agent_registry_websocket_integration,
        test_execution_engine_initialization,
        test_unified_tool_execution_events,
        test_complete_agent_flow
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[FAIL] Test {test_func.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"[TOTAL] Total: {passed + failed}")
    
    if failed == 0:
        print("\n[SUCCESS] ALL WEBSOCKET AGENT TESTS PASSED!")
        print("WebSocket agent event integration is working correctly.")
        return True
    else:
        print(f"\n[WARNING]  {failed} test(s) failed - WebSocket integration needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)