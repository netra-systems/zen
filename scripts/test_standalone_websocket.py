#!/usr/bin/env python
"""Standalone test to verify WebSocket functionality without pytest fixtures"""

import asyncio
import json
import time
from typing import Dict, List, Set
from shared.isolated_environment import IsolatedEnvironment

# Imports
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

class MockWebSocket:
    """Simple mock WebSocket for testing."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connected = True
        self.application_state = 1  # Mock WebSocketState.CONNECTED
        
    async def send_text(self, data: str) -> bool:
        """Mock send_text method - returns success status."""
        if self.connected:
            try:
                message = json.loads(data) if isinstance(data, str) else data
                self.messages.append(message)
                print(f"WebSocket message: {message.get('type', 'unknown')}")
                return True
            except json.JSONDecodeError:
                print(f"Failed to parse WebSocket message: {data}")
                return False
        return False
            
    async def send_json(self, data: Dict, timeout: float = None) -> bool:
        """Mock send_json method - returns success status."""
        if self.connected:
            self.messages.append(data)
            print(f"WebSocket message: {data.get('type', 'unknown')}")
            return True
        return False
        
    def client_state(self):
        """Mock client state method."""
        return 1 if self.connected else 0  # Connected state
        
    @property 
    def state(self):
        """Mock state property."""
        return 1 if self.connected else 0


async def test_websocket_events():
    """Test the 5 critical WebSocket events."""
    print("Starting WebSocket event test...")
    
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
    
    print("Sending 5 critical WebSocket events...")
    
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
    
    # Validate events
    event_types = set(msg.get("type", "unknown") for msg in mock_websocket.messages)
    required_events = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
    
    print(f"\nResults:")
    print(f"Events received: {len(mock_websocket.messages)}")
    print(f"Event types: {event_types}")
    
    missing = required_events - event_types
    if not missing:
        print("SUCCESS: ALL 5 CRITICAL EVENTS RECEIVED!")
        return True
    else:
        print(f"FAIL: MISSING EVENTS: {missing}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_websocket_events())
    if result:
        print("\nWebSocket test PASSED!")
    else:
        print("\nWebSocket test FAILED!")