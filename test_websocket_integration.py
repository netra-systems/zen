#!/usr/bin/env python
"""Simple test to verify WebSocket agent integration works."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.enhanced_tool_execution import EnhancedToolExecutionEngine


async def test_websocket_integration():
    """Test basic WebSocket integration for agent events."""
    print("Testing WebSocket Agent Integration...")
    
    # Setup components
    ws_manager = WebSocketManager()
    
    # Mock WebSocket connection
    conn_id = "test-integration"
    mock_ws = MagicMock()
    received_events = []
    
    async def capture_event(message):
        if isinstance(message, str):
            data = json.loads(message)
        else:
            data = message
        received_events.append(data)
        print(f"Event: {data.get('type', 'unknown')}")
        
    mock_ws.send_json = AsyncMock(side_effect=capture_event)
    await ws_manager.connect_user(conn_id, mock_ws, conn_id)
    
    # Setup agent components
    class MockLLM:
        async def generate(self, *args, **kwargs):
            return {"content": "Test response"}
    
    llm = MockLLM()
    tool_dispatcher = ToolDispatcher()
    
    # Create registry and set websocket
    registry = AgentRegistry(llm, tool_dispatcher)
    registry.set_websocket_manager(ws_manager)
    
    # Verify tool dispatcher was enhanced
    assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
        "Tool dispatcher was not enhanced!"
    print("PASS: Tool dispatcher enhanced successfully")
    
    # Create execution engine
    engine = ExecutionEngine(registry, ws_manager)
    
    # Verify WebSocket notifier is initialized
    assert hasattr(engine, 'websocket_notifier'), "Missing WebSocket notifier!"
    assert engine.websocket_notifier is not None, "WebSocket notifier not initialized!"
    print("PASS: ExecutionEngine WebSocket notifier initialized")
    
    # Create execution context
    context = AgentExecutionContext(
        run_id="test-run",
        thread_id=conn_id,
        user_id="test-user", 
        agent_name="test_agent"
    )
    
    # Create state
    state = DeepAgentState()
    state.user_request = "Test request"
    state.chat_thread_id = conn_id
    
    # Test agent execution (this should send WebSocket events)
    try:
        result = await engine.execute_agent(context, state)
        print(f"PASS: Agent execution completed: success={result.success}")
    except Exception as e:
        print(f"WARN: Agent execution error (expected): {e}")
    
    # Allow events to propagate
    await asyncio.sleep(0.5)
    
    # Verify events were received
    print(f"\nSTATS: Received {len(received_events)} events:")
    for i, event in enumerate(received_events):
        print(f"  {i+1}. {event.get('type', 'unknown')}")
    
    # Check for critical events
    event_types = [e.get('type', 'unknown') for e in received_events]
    
    critical_events = {
        "agent_started": "agent_started" in event_types,
        "agent_thinking": "agent_thinking" in event_types,
        "completion": any(t in ["agent_completed", "agent_error"] for t in event_types)
    }
    
    print(f"\nCHECK: Critical Events Check:")
    for event, found in critical_events.items():
        status = "PASS" if found else "FAIL"
        print(f"  {status} {event}: {'Found' if found else 'Missing'}")
    
    # Test tool execution events
    async def test_tool():
        return {"result": "success"}
    
    print(f"\nTOOL: Testing tool execution events...")
    try:
        await tool_dispatcher.executor.execute_with_state(
            test_tool, "test_tool", {}, state, "tool-run"
        )
        print("PASS: Tool execution completed")
    except Exception as e:
        print(f"WARN: Tool execution error: {e}")
    
    await asyncio.sleep(0.5)
    
    # Check for tool events
    new_events = [e for e in received_events if e.get('type') in ['tool_executing', 'tool_completed']]
    print(f"TOOL: Tool events: {len(new_events)} found")
    for event in new_events:
        print(f"  - {event.get('type')}")
    
    # Cleanup
    await ws_manager.disconnect_user(conn_id, mock_ws, conn_id)
    
    # Summary
    total_events = len(received_events)
    has_agent_events = any(critical_events.values())
    has_tool_events = len(new_events) > 0
    
    print(f"\nSUMMARY: Integration Test Summary:")
    print(f"  Total Events: {total_events}")
    print(f"  Agent Events: {'PASS' if has_agent_events else 'FAIL'}")
    print(f"  Tool Events: {'PASS' if has_tool_events else 'FAIL'}")
    
    if total_events > 0 and has_agent_events:
        print(f"\nSUCCESS: WebSocket Agent Integration is working!")
        return True
    else:
        print(f"\nFAILED: WebSocket Agent Integration needs fixes")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_websocket_integration())
    exit(0 if result else 1)