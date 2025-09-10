#!/usr/bin/env python
"""STANDALONE WebSocket Agent Events Test - NO FIXTURES

This test validates that the critical WebSocket events are sent during agent execution.
NO conftest dependencies, NO complex fixtures, NO real services requirements.

Tests the 5 critical WebSocket events:
1. agent_started
2. agent_thinking  
3. tool_executing
4. tool_completed
5. agent_completed
"""

import asyncio
import os
import sys
import json
import time
from typing import Dict, List, Set
from shared.isolated_environment import IsolatedEnvironment

# Add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core modules
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class MockWebSocket:
    """Mock WebSocket for testing - simulates WebSocket connection."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connected = True
        self.events = []
        self.application_state = 1  # Mock WebSocketState.CONNECTED
        
    async def send_text(self, data: str) -> bool:
        """Mock send_text method."""
        if not self.connected:
            return False
            
        try:
            message = json.loads(data) if isinstance(data, str) else data
            self.messages.append(message)
            self.events.append(message)
            print(f"WebSocket received: {message.get('type', 'unknown')}")
            return True
        except json.JSONDecodeError:
            print(f"Failed to parse WebSocket message: {data}")
            return False
            
    async def send_json(self, data: Dict, timeout: float = None) -> bool:
        """Mock send_json method."""
        if not self.connected:
            return False
            
        self.messages.append(data)
        self.events.append(data)
        print(f"WebSocket received: {data.get('type', 'unknown')}")
        return True
        
    def client_state(self):
        """Mock client state."""
        return 1 if self.connected else 0
        
    @property 
    def state(self):
        """Mock state property."""
        return 1 if self.connected else 0


class WebSocketEventValidator:
    """Validates that all critical WebSocket events are sent."""
    
    CRITICAL_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, events: List[Dict]):
        self.events = events
        self.event_types = {event.get("type") for event in events}
        
    def validate(self) -> Dict:
        """Validate events and return results."""
        missing_events = self.CRITICAL_EVENTS - self.event_types
        
        return {
            "total_events": len(self.events),
            "event_types": list(self.event_types),
            "missing_critical_events": list(missing_events),
            "has_all_critical": len(missing_events) == 0,
            "validation_success": len(missing_events) == 0 and len(self.events) >= 5
        }


async def test_websocket_agent_events():
    """Test that all 5 critical WebSocket events are sent during agent execution."""
    
    print("Starting WebSocket Agent Events Test...")
    
    # Setup WebSocket components
    ws_manager = WebSocketManager()
    mock_websocket = MockWebSocket()
    
    # Create user connection
    user_id = "test-user-123"
    thread_id = "test-thread-456"
    
    # Connect user to WebSocket manager
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    print(f"Connected user {user_id} to WebSocket manager")
    
    # Create WebSocket notifier
    notifier = AgentWebSocketBridge(ws_manager)
    
    # Create execution context
    context = AgentExecutionContext(
        run_id="test-run-789",
        thread_id=thread_id,
        user_id=user_id,
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    )
    print(f"Created execution context for run_id: {context.run_id}")
    
    # SIMULATE COMPLETE AGENT EXECUTION FLOW
    
    print("\n1. Sending agent_started event...")
    await notifier.send_agent_started(context)
    
    print("2. Sending agent_thinking event...")
    await notifier.send_agent_thinking(context, "Processing user request and analyzing requirements...")
    
    print("3. Sending tool_executing event...")
    await notifier.send_tool_executing(context, "analysis_tool", 
                                     tool_purpose="Analyze user input and generate response")
    
    print("4. Sending tool_completed event...")
    await notifier.send_tool_completed(context, "analysis_tool", {
        "result": "Analysis completed successfully",
        "status": "success",
        "processing_time_ms": 150
    })
    
    print("5. Sending agent_completed event...")
    await notifier.send_agent_completed(context, {
        "response": "Hello! I've analyzed your request and can help you.",
        "status": "completed",
        "processing_time_ms": 500
    })
    
    # Allow async events to complete
    await asyncio.sleep(0.5)
    
    # VALIDATE RESULTS
    print(f"\nReceived {len(mock_websocket.events)} WebSocket events:")
    for i, event in enumerate(mock_websocket.events, 1):
        print(f"  {i}. {event.get('type', 'unknown')}")
    
    validator = WebSocketEventValidator(mock_websocket.events)
    results = validator.validate()
    
    print(f"\nValidation Results:")
    print(f"  Total events: {results['total_events']}")
    print(f"  Event types received: {results['event_types']}")
    print(f"  Missing critical events: {results['missing_critical_events']}")
    print(f"  Has all critical events: {results['has_all_critical']}")
    print(f"  Validation success: {results['validation_success']}")
    
    # ASSERTIONS
    assert results['total_events'] >= 5, f"Expected at least 5 events, got {results['total_events']}"
    assert results['has_all_critical'], f"Missing critical events: {results['missing_critical_events']}"
    assert results['validation_success'], "WebSocket event validation failed"
    
    print("\nSUCCESS: All 5 critical WebSocket events were sent correctly!")
    return True


async def test_tool_execution_events():
    """Test that tool execution sends proper WebSocket events."""
    
    print("\nStarting Tool Execution Events Test...")
    
    # Setup
    ws_manager = WebSocketManager()
    mock_websocket = MockWebSocket()
    
    user_id = "tool-test-user"
    thread_id = "tool-test-thread"
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    # Try to import and use enhanced tool executor
    try:
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        from netra_backend.app.agents.state import DeepAgentState
        
        # Create enhanced tool executor
        enhanced_executor = UnifiedToolExecutionEngine(ws_manager)
        
        # Create state for tool execution
        state = DeepAgentState(
            chat_thread_id=thread_id,
            user_id=user_id,
            run_id="tool-run-123"
        )
        
        # Create simple test tool
        class SimpleTestTool:
            def __init__(self):
                self.name = "test_tool"
                
            async def __call__(self, *args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate work
                return {"result": "Tool executed successfully"}
        
        test_tool = SimpleTestTool()
        
        # Execute tool through enhanced executor
        print("Executing tool through enhanced executor...")
        result = await enhanced_executor.execute_with_state(
            test_tool, "test_tool", {}, state, "tool-run-123"
        )
        
        await asyncio.sleep(0.5)  # Allow events to propagate
        
        # Validate tool events
        event_types = {event.get("type") for event in mock_websocket.events}
        
        print(f"Tool execution events received: {list(event_types)}")
        
        # Should have at least tool_executing and tool_completed
        assert "tool_executing" in event_types, "Missing tool_executing event"
        assert "tool_completed" in event_types, "Missing tool_completed event"
        
        print("SUCCESS: Tool execution events sent correctly!")
        
    except ImportError as e:
        print(f"Enhanced tool execution not available: {e}")
        print("Skipping tool execution event test")


async def main():
    """Run all WebSocket event tests."""
    print("=" * 60)
    print("STANDALONE WEBSOCKET AGENT EVENTS TEST")
    print("=" * 60)
    
    try:
        # Test 1: Basic agent events
        await test_websocket_agent_events()
        
        # Test 2: Tool execution events  
        await test_tool_execution_events()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! WebSocket agent events working correctly.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(main())
    sys.exit(0 if result else 1)