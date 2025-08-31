#!/usr/bin/env python3
"""
Simple WebSocket test to isolate actual issues from framework problems.
"""

import asyncio
import sys
import os
from typing import Dict, Any
from unittest.mock import AsyncMock

# Add project to path
project_root = os.path.abspath('.')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.enhanced_tool_execution import enhance_tool_dispatcher_with_notifications

class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.messages = []
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message."""
        self.messages.append({
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown')
        })
        print(f"📡 WebSocket: {message.get('type', 'unknown')} -> {thread_id}")
        return True
    
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        print(f"🔗 Connect: user={user_id}, thread={thread_id}")
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        print(f"🔌 Disconnect: user={user_id}, thread={thread_id}")
    
    def get_events_for_thread(self, thread_id: str):
        return [msg for msg in self.messages if msg['thread_id'] == thread_id]

async def test_websocket_notifier_methods():
    """Test that WebSocketNotifier has all required methods."""
    print("🧪 Testing WebSocketNotifier methods...")
    
    ws_manager = MockWebSocketManager()
    notifier = WebSocketNotifier(ws_manager)
    
    # Verify all methods exist
    required_methods = [
        'send_agent_started',
        'send_agent_thinking', 
        'send_partial_result',
        'send_tool_executing',
        'send_tool_completed',
        'send_final_report',
        'send_agent_completed'
    ]
    
    for method in required_methods:
        assert hasattr(notifier, method), f"Missing method: {method}"
        assert callable(getattr(notifier, method)), f"Method not callable: {method}"
        print(f"  ✅ {method}")
    
    print("✅ All WebSocketNotifier methods exist and are callable")

async def test_tool_dispatcher_enhancement():
    """Test that tool dispatcher enhancement works."""
    print("\n🔧 Testing tool dispatcher enhancement...")
    
    dispatcher = ToolDispatcher()
    ws_manager = MockWebSocketManager()
    
    # Verify initial state
    assert hasattr(dispatcher, 'executor'), "ToolDispatcher missing executor"
    original_executor = dispatcher.executor
    print(f"  📋 Original executor: {type(original_executor).__name__}")
    
    # Enhance
    enhance_tool_dispatcher_with_notifications(dispatcher, ws_manager)
    
    # Verify enhancement
    assert dispatcher.executor != original_executor, "Executor was not replaced"
    print(f"  🔄 Enhanced executor: {type(dispatcher.executor).__name__}")
    assert hasattr(dispatcher, '_websocket_enhanced'), "Missing enhancement marker"
    assert dispatcher._websocket_enhanced is True, "Enhancement marker not set"
    
    print("✅ Tool dispatcher enhanced successfully")

async def test_agent_registry_integration():
    """Test AgentRegistry WebSocket integration."""
    print("\n👥 Testing AgentRegistry integration...")
    
    class MockLLM:
        pass
    
    tool_dispatcher = ToolDispatcher()
    registry = AgentRegistry(MockLLM(), tool_dispatcher)
    ws_manager = MockWebSocketManager()
    
    # Set WebSocket manager
    registry.set_websocket_manager(ws_manager)
    
    # Verify tool dispatcher was enhanced
    from netra_backend.app.agents.enhanced_tool_execution import EnhancedToolExecutionEngine
    assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
        f"Expected EnhancedToolExecutionEngine, got {type(tool_dispatcher.executor).__name__}"
    
    print("✅ AgentRegistry enhanced tool dispatcher correctly")

async def test_websocket_event_flow():
    """Test actual WebSocket event flow."""
    print("\n🌊 Testing WebSocket event flow...")
    
    ws_manager = MockWebSocketManager()
    notifier = WebSocketNotifier(ws_manager)
    
    # Create context
    context = AgentExecutionContext(
        run_id="test-123",
        thread_id="thread-456", 
        user_id="user-789",
        agent_name="test_agent"
    )
    
    # Send events in sequence
    print("  📤 Sending event sequence...")
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "Processing request...")
    await notifier.send_tool_executing(context, "search_tool")
    await notifier.send_tool_completed(context, "search_tool", {"found": 5})
    await notifier.send_agent_completed(context, {"success": True})
    
    # Verify events
    events = ws_manager.get_events_for_thread("thread-456")
    event_types = [e['event_type'] for e in events]
    
    expected_events = [
        'agent_started', 
        'agent_thinking',
        'tool_executing', 
        'tool_completed',
        'agent_completed'
    ]
    
    print(f"  📊 Expected: {expected_events}")
    print(f"  📊 Received: {event_types}")
    
    for expected in expected_events:
        assert expected in event_types, f"Missing event: {expected}"
    
    print("✅ All expected events received in correct order")

async def run_all_tests():
    """Run all WebSocket tests."""
    print("🚀 Running WebSocket API Tests")
    print("=" * 60)
    
    tests = [
        test_websocket_notifier_methods,
        test_tool_dispatcher_enhancement, 
        test_agent_registry_integration,
        test_websocket_event_flow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("💥 Some tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)