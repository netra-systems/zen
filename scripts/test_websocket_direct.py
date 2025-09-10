#!/usr/bin/env python
"""DIRECT WebSocket Test - No pytest, no fixtures, no environment checks

This is the SIMPLEST and most DIRECT test possible:
- User sends "Hello" message
- Agent processes request  
- ALL 5 critical WebSocket events are sent:
  1. agent_started
  2. agent_thinking  
  3. tool_executing
  4. tool_completed
  5. agent_completed

Run with: python test_websocket_direct.py
"""

import asyncio
import json
import time
from typing import Dict, List, Set
from shared.isolated_environment import IsolatedEnvironment

# Imports
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState

class DirectWebSocketEventValidator:
    """Direct validator for the 5 critical WebSocket events."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_types: Set[str] = set()
        self.start_time = time.time()
        
    def record_event(self, event: Dict) -> None:
        """Record an event."""
        self.events.append(event)
        event_type = event.get("type", "unknown")
        self.event_types.add(event_type)
        print(f"  EVENT: {event_type}")
        
    def has_all_required_events(self) -> bool:
        """Check if all required events were received."""
        return self.REQUIRED_EVENTS.issubset(self.event_types)
        
    def get_missing_events(self) -> Set[str]:
        """Get list of missing required events."""
        return self.REQUIRED_EVENTS - self.event_types
        
    def get_summary(self) -> str:
        """Get validation summary."""
        duration = time.time() - self.start_time
        missing = self.get_missing_events()
        
        if not missing:
            return f"SUCCESS: ALL 5 CRITICAL EVENTS RECEIVED in {duration:.2f}s"
        else:
            return f"FAIL: MISSING EVENTS: {missing}. Got {len(self.events)} events in {duration:.2f}s"


class DirectMockWebSocket:
    """Direct mock WebSocket for testing."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connected = True
        self.validator = DirectWebSocketEventValidator()
        self.application_state = 1
        
    async def send_text(self, data: str) -> bool:
        """Mock send_text method."""
        if self.connected:
            try:
                message = json.loads(data) if isinstance(data, str) else data
                self.messages.append(message)
                self.validator.record_event(message)
                return True
            except json.JSONDecodeError:
                print(f"Failed to parse message: {data}")
                return False
        return False
            
    async def send_json(self, data: Dict, timeout: float = None) -> bool:
        """Mock send_json method."""
        if self.connected:
            self.messages.append(data)
            self.validator.record_event(data)
            return True
        return False
        
    def client_state(self):
        """Mock client state method."""
        return 1 if self.connected else 0
        
    @property 
    def state(self):
        """Mock state property."""
        return 1 if self.connected else 0


class DirectTestTool:
    """Direct test tool."""
    
    def __init__(self):
        self.name = "direct_test_tool"
        self.description = "A direct tool for testing"
        
    async def __call__(self, *args, **kwargs) -> Dict:
        """Execute the tool."""
        await asyncio.sleep(0.05)
        return {"result": "Direct tool executed successfully", "status": "completed"}


async def test_basic_5_events():
    """TEST 1: Basic 5 WebSocket events through notifier."""
    print("\n=== TEST 1: Basic 5 WebSocket Events ===")
    
    # Setup
    ws_manager = WebSocketManager()
    mock_websocket = DirectMockWebSocket()
    user_id = "test-user"
    thread_id = "test-thread"
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    notifier = AgentWebSocketBridge(ws_manager)
    
    context = AgentExecutionContext(
        run_id="test-run-123",
        thread_id=thread_id,
        user_id=user_id,
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    )
    
    print("Sending 5 critical WebSocket events...")
    
    # Send all 5 events
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "Processing your message...")
    await notifier.send_tool_executing(context, "direct_test_tool")
    await notifier.send_tool_completed(context, "direct_test_tool", {"result": "success"})
    await notifier.send_agent_completed(context, {"response": "Hello! I can help you."})
    
    await asyncio.sleep(0.5)
    
    # Validate
    validator = mock_websocket.validator
    success = validator.has_all_required_events()
    missing = validator.get_missing_events()
    
    print(f"\nRESULT: {validator.get_summary()}")
    
    if not success:
        print(f"FAILURE: Missing events: {missing}")
        return False
    
    if len(validator.events) < 5:
        print(f"FAILURE: Expected at least 5 events, got {len(validator.events)}")
        return False
    
    print("SUCCESS: All 5 critical events received!")
    return True


async def test_unified_tool_execution():
    """TEST 2: Enhanced tool execution events."""
    print("\n=== TEST 2: Enhanced Tool Execution Events ===")
    
    # Setup
    ws_manager = WebSocketManager()
    mock_websocket = DirectMockWebSocket()
    user_id = "tool-user"
    thread_id = "tool-thread"
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    enhanced_executor = UnifiedToolExecutionEngine(ws_manager)
    
    state = DeepAgentState(
        chat_thread_id=thread_id,
        user_id=user_id,
        run_id="tool-run-123"
    )
    
    test_tool = DirectTestTool()
    
    print("Executing tool through enhanced executor...")
    
    # Execute tool
    result = await enhanced_executor.execute_with_state(
        test_tool, "direct_test_tool", {}, state, "tool-run-123"
    )
    
    await asyncio.sleep(0.5)
    
    # Validate
    validator = mock_websocket.validator
    has_executing = "tool_executing" in validator.event_types
    has_completed = "tool_completed" in validator.event_types
    
    print(f"\nTool events received: {validator.event_types}")
    
    if not has_executing:
        print("FAILURE: Missing tool_executing event")
        return False
        
    if not has_completed:
        print("FAILURE: Missing tool_completed event")
        return False
    
    print("SUCCESS: Tool execution events working correctly!")
    return True


async def test_hello_complete_flow():
    """TEST 3: Complete 'Hello' user flow."""
    print("\n=== TEST 3: Complete 'Hello' User Flow ===")
    
    # Setup
    ws_manager = WebSocketManager()
    mock_websocket = DirectMockWebSocket()
    user_id = "hello-user"
    thread_id = "hello-thread"
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    notifier = AgentWebSocketBridge(ws_manager)
    
    context = AgentExecutionContext(
        run_id="hello-run",
        thread_id=thread_id,
        user_id=user_id,
        agent_name="greeting_agent",
        retry_count=0,
        max_retries=1
    )
    
    print("Simulating complete 'Hello' processing flow...")
    user_message = "Hello"
    
    # Complete flow simulation
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "Analyzing user greeting and preparing response...")
    await notifier.send_tool_executing(context, "greeting_tool", tool_purpose="Generate greeting response")
    await notifier.send_tool_completed(context, "greeting_tool", {"greeting": "Hello! How can I help you today?"})
    await notifier.send_agent_completed(context, {
        "response": "Hello! How can I help you today?",
        "user_message": user_message,
        "processed": True
    })
    
    await asyncio.sleep(0.5)
    
    # Validate
    validator = mock_websocket.validator
    success = validator.has_all_required_events()
    missing = validator.get_missing_events()
    events = validator.events
    
    print(f"\nRESULT: {validator.get_summary()}")
    
    if not success:
        print(f"FAILURE: Missing critical events: {missing}")
        return False
    
    if len(events) < 5:
        print(f"FAILURE: Expected at least 5 events, got {len(events)}")
        return False
    
    # Check event order
    first_event = events[0].get("type")
    last_event = events[-1].get("type")
    
    if first_event != "agent_started":
        print(f"FAILURE: First event should be agent_started, got {first_event}")
        return False
        
    if last_event != "agent_completed":
        print(f"FAILURE: Last event should be agent_completed, got {last_event}")
        return False
    
    print("SUCCESS: Complete 'Hello' flow with all 5 events in correct order!")
    return True


async def run_all_tests():
    """Run all direct tests."""
    print("STARTING DIRECT WEBSOCKET TESTS")
    print("=" * 50)
    
    tests = [
        test_basic_5_events,
        test_unified_tool_execution, 
        test_hello_complete_flow
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"TEST FAILED with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    
    passed = sum(results)
    total = len(results)
    
    for i, result in enumerate(results, 1):
        status = "PASS" if result else "FAIL"
        print(f"  Test {i}: {status}")
    
    print(f"\nOVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: ALL DIRECT WEBSOCKET TESTS PASSED!")
        return True
    else:
        print("FAILURE: Some tests failed!")
        return False


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)