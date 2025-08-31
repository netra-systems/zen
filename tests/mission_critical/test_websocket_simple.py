#!/usr/bin/env python
"""SIMPLE AND DIRECT WebSocket Test - Validates 5 Critical Events

This test focuses on the BASICS:
- User sends "Hello" message  
- Agent processes request
- ALL 5 critical WebSocket events are sent:
  1. agent_started: User must see agent began processing
  2. agent_thinking: Real-time reasoning visibility
  3. tool_executing: Tool usage transparency 
  4. tool_completed: Tool results display
  5. agent_completed: User must know when done

NO complex fixtures. NO environment variable dependencies.
DIRECT testing of the most critical WebSocket path.
"""

import asyncio
import os
import sys
import json
import time
from typing import Dict, List, Set

# Add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary modules BEFORE pytest
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.enhanced_tool_execution import EnhancedToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState

# Import pytest AFTER other imports to avoid fixture injection
import pytest

# Simple logger setup
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SimpleWebSocketEventValidator:
    """Simple validator for the 5 critical WebSocket events."""
    
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
        logger.info(f"Event recorded: {event_type}")
        
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


class MockWebSocket:
    """Simple mock WebSocket for testing."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connected = True
        self.validator = SimpleWebSocketEventValidator()
        self.application_state = 1  # Mock WebSocketState.CONNECTED
        
    async def send_text(self, data: str) -> bool:
        """Mock send_text method - returns success status."""
        if self.connected:
            try:
                message = json.loads(data) if isinstance(data, str) else data
                self.messages.append(message)
                self.validator.record_event(message)
                return True
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse WebSocket message: {data}")
                return False
        return False
            
    async def send_json(self, data: Dict, timeout: float = None) -> bool:
        """Mock send_json method - returns success status."""
        if self.connected:
            self.messages.append(data)
            self.validator.record_event(data)
            return True
        return False
        
    def client_state(self):
        """Mock client state method."""
        return 1 if self.connected else 0  # Connected state
        
    @property 
    def state(self):
        """Mock state property."""
        return 1 if self.connected else 0
            
    def disconnect(self):
        """Mock disconnect."""
        self.connected = False


class SimpleTestTool:
    """Simple test tool that triggers tool events."""
    
    def __init__(self):
        self.name = "simple_test_tool"
        self.description = "A simple tool for testing"
        
    async def __call__(self, *args, **kwargs) -> Dict:
        """Execute the tool."""
        await asyncio.sleep(0.05)  # Simulate tool execution
        return {"result": "Tool executed successfully", "status": "completed"}


# Simple and direct WebSocket test functions

@pytest.mark.asyncio
async def test_basic_websocket_events_flow():
    """Test that basic agent flow sends all 5 critical WebSocket events."""
    
    # Setup WebSocket components
    ws_manager = WebSocketManager()
    mock_websocket = MockWebSocket()
    
    # Create user connection
    user_id = "test-user"
    thread_id = "test-thread"
    
    # Connect user to WebSocket manager
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    # Create WebSocket notifier
    notifier = WebSocketNotifier(ws_manager)
    
    # Create execution context
    context = AgentExecutionContext(
        run_id="test-run-123",
        thread_id=thread_id,
        user_id=user_id,
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    )
    
    # SIMULATE COMPLETE AGENT FLOW
    
    # 1. Agent starts
    await notifier.send_agent_started(context)
    
    # 2. Agent thinks
    await notifier.send_agent_thinking(context, "Processing your message...")
    
    # 3. Agent executes tool
    await notifier.send_tool_executing(context, "simple_test_tool")
    
    # 4. Tool completes
    await notifier.send_tool_completed(context, "simple_test_tool", {"result": "success"})
    
    # 5. Agent completes
    await notifier.send_agent_completed(context, {"response": "Hello! I can help you."})
    
    # Allow async events to complete
    await asyncio.sleep(0.5)
    
    # VALIDATE ALL 5 EVENTS
    validator = mock_websocket.validator
    
    assert validator.has_all_required_events(), validator.get_summary()
    
    missing = validator.get_missing_events()
    assert len(missing) == 0, f"Missing critical events: {missing}"
    
    # Verify minimum event count
    assert len(validator.events) >= 5, f"Expected at least 5 events, got {len(validator.events)}"
    
    print(validator.get_summary())


@pytest.mark.asyncio
async def test_enhanced_tool_execution_events():
    """Test that enhanced tool execution sends proper WebSocket events."""
    
    ws_manager = WebSocketManager()
    mock_websocket = MockWebSocket()
    
    user_id = "tool-test-user"
    thread_id = "tool-test-thread"
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    # Create enhanced tool executor
    enhanced_executor = EnhancedToolExecutionEngine(ws_manager)
    
    # Create state for tool execution
    state = DeepAgentState(
        chat_thread_id=thread_id,
        user_id=user_id,
        run_id="tool-run-123"
    )
    
    # Create simple tool
    test_tool = SimpleTestTool()
    
    # Execute tool through enhanced executor
    result = await enhanced_executor.execute_with_state(
        test_tool, "simple_test_tool", {}, state, "tool-run-123"
    )
    
    # Allow events to propagate
    await asyncio.sleep(0.5)
    
    # Validate tool events
    validator = mock_websocket.validator
    
    # Should have at least tool_executing and tool_completed
    assert "tool_executing" in validator.event_types, "Missing tool_executing event"
    assert "tool_completed" in validator.event_types, "Missing tool_completed event"
    
    print(f"Tool execution events: {validator.event_types}")


@pytest.mark.asyncio 
async def test_user_hello_complete_flow():
    """Test the MOST CRITICAL path: user sends 'Hello' -> agent responds -> all events sent."""
    
    ws_manager = WebSocketManager()
    mock_websocket = MockWebSocket()
    
    user_id = "hello-user" 
    thread_id = "hello-thread"
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    # Create notifier
    notifier = WebSocketNotifier(ws_manager)
    
    # Create context for "Hello" processing
    context = AgentExecutionContext(
        run_id="hello-run",
        thread_id=thread_id,
        user_id=user_id,
        agent_name="greeting_agent",
        retry_count=0,
        max_retries=1
    )
    
    # SIMULATE COMPLETE "Hello" PROCESSING FLOW
    
    # User sends "Hello"
    user_message = "Hello"
    
    # 1. Agent starts processing
    await notifier.send_agent_started(context)
    
    # 2. Agent analyzes the greeting
    await notifier.send_agent_thinking(context, "Analyzing user greeting and preparing appropriate response...")
    
    # 3. Agent uses greeting tool
    await notifier.send_tool_executing(context, "greeting_tool", 
                                     tool_purpose="Generate appropriate greeting response")
    
    # 4. Greeting tool completes
    await notifier.send_tool_completed(context, "greeting_tool", 
                                     {"greeting": "Hello! How can I help you today?"})
    
    # 5. Agent completes with response
    await notifier.send_agent_completed(context, {
        "response": "Hello! How can I help you today?",
        "user_message": user_message,
        "processed": True
    })
    
    # Allow events to propagate
    await asyncio.sleep(0.5)
    
    # CRITICAL VALIDATION
    validator = mock_websocket.validator
    
    # MUST have all 5 critical events
    missing_events = validator.get_missing_events()
    
    assert len(missing_events) == 0, f"CRITICAL FAILURE: Missing events {missing_events} for basic Hello flow"
    assert validator.has_all_required_events(), f"CRITICAL: Not all required events received: {validator.get_summary()}"
    
    # Verify logical event order (first should be start, last should be completion)
    events = validator.events
    assert len(events) >= 5, f"Expected at least 5 events, got {len(events)}"
    
    first_event = events[0].get("type")
    last_event = events[-1].get("type") 
    
    assert first_event == "agent_started", f"First event should be agent_started, got {first_event}"
    assert last_event == "agent_completed", f"Last event should be agent_completed, got {last_event}"
    
    print("SUCCESS: CRITICAL PATH VALIDATED: User 'Hello' -> All 5 WebSocket events sent")
    print(validator.get_summary())


# Stand-alone test runner
if __name__ == "__main__":
    # Run the simple tests
    pytest.main([__file__, "-v", "--tb=short"])