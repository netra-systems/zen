#!/usr/bin/env python
"""Integration test to verify all 5 critical WebSocket agent events are sent during execution.

CRITICAL BUSINESS VALUE: This test validates the core chat functionality that drives $500K+ ARR.

Tests the complete flow:
1. agent_started - User sees agent began processing  
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display  
5. agent_completed - Final results ready

This test uses REAL components with mock WebSocket capture to validate the complete event flow.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock
import pytest

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.ssot.e2e_auth_helper import get_test_user_context


class MockWebSocketEventCapture:
    """Captures WebSocket events for validation."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_types: List[str] = []
        
    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Mock WebSocket event sending."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)
        self.event_types.append(event_type)
        print(f"🔔 WebSocket Event: {event_type} - {data.get('tool_name', data.get('agent_name', 'unknown'))}")
        return True
        
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get all events of a specific type."""
        return [event for event in self.events if event["type"] == event_type]
        
    def has_all_critical_events(self) -> bool:
        """Check if all 5 critical events were received."""
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        received_events = set(self.event_types)
        return required_events.issubset(received_events)


class SimpleTestAgent:
    """Simple test agent that uses tools."""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        self.websocket_bridge = None
        self._run_id = None
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for notifications."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, should_continue: bool = True) -> Dict[str, Any]:
        """Execute agent with tool usage."""
        
        # Emit thinking event during execution
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=self.name,
                reasoning="Analyzing the problem and selecting appropriate tools...",
                step_number=1
            )
        
        # Simulate tool usage (this should trigger tool_executing and tool_completed events)
        if hasattr(state, 'tool_dispatcher') and state.tool_dispatcher:
            try:
                # Execute a test tool
                tool_result = await state.tool_dispatcher.execute_tool(
                    "test_tool",
                    {"test_param": "test_value"}
                )
                
                # Emit another thinking event after tool usage
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=run_id,
                        agent_name=self.name,
                        reasoning="Processing tool results and preparing final response...",
                        step_number=2
                    )
                    
                return {
                    "success": True,
                    "result": "Agent executed successfully with tool usage",
                    "tool_result": str(tool_result),
                    "agent_name": self.name
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Tool execution failed: {e}",
                    "agent_name": self.name
                }
        
        return {
            "success": True,
            "result": "Agent executed successfully without tools",
            "agent_name": self.name
        }


async def create_mock_tool_dispatcher(user_context: UserExecutionContext, websocket_manager) -> UnifiedToolDispatcher:
    """Create mock tool dispatcher with WebSocket support."""
    
    # Create dispatcher using proper factory method
    dispatcher = await UnifiedToolDispatcher.create_for_user(
        user_context=user_context,
        websocket_bridge=websocket_manager  # Pass as websocket_bridge
    )
    
    # Register a simple test tool
    class TestTool:
        name = "test_tool"
        
        async def arun(self, test_param: str = "default") -> str:
            await asyncio.sleep(0.1)  # Simulate work
            return f"Tool executed with param: {test_param}"
    
    test_tool = TestTool()
    dispatcher.register_tool(test_tool)
    
    return dispatcher


@pytest.fixture
async def websocket_event_capture():
    """Create WebSocket event capture fixture."""
    return MockWebSocketEventCapture()


@pytest.fixture 
async def user_context():
    """Create test user context."""
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        thread_id=f"thread_{uuid.uuid4().hex[:8]}",
        session_id=f"session_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture
async def websocket_manager(websocket_event_capture):
    """Create WebSocket manager that captures events."""
    manager = Mock()
    manager.send_event = websocket_event_capture.send_event
    return manager


@pytest.fixture
async def websocket_bridge(websocket_manager, user_context):
    """Create WebSocket bridge with event capture."""
    bridge = AgentWebSocketBridge(user_context)
    # Set the websocket manager directly
    bridge._websocket_manager = websocket_manager
    return bridge


@pytest.fixture
async def agent_registry():
    """Create agent registry."""
    registry = AgentRegistry()
    return registry


@pytest.fixture
async def test_agent():
    """Create test agent."""
    return SimpleTestAgent("TestChatAgent")


@pytest.mark.asyncio
async def test_complete_websocket_event_flow(
    websocket_event_capture,
    user_context,
    websocket_manager, 
    websocket_bridge,
    agent_registry,
    test_agent
):
    """Test complete WebSocket event flow with all 5 critical events.
    
    CRITICAL: This test validates the core chat functionality.
    ALL 5 events MUST be sent for proper user experience.
    """
    
    # Setup: Register agent and set WebSocket manager
    agent_registry.register(test_agent.name, test_agent)
    agent_registry.set_websocket_manager(websocket_manager)
    
    # Create tool dispatcher with WebSocket support
    tool_dispatcher = await create_mock_tool_dispatcher(user_context, websocket_bridge)
    
    # Create deep agent state with tool dispatcher
    state = DeepAgentState(
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        conversation_history=[],
        tool_dispatcher=tool_dispatcher
    )
    
    # Create execution context
    execution_context = AgentExecutionContext(
        agent_name=test_agent.name,
        run_id=user_context.run_id,
        correlation_id=f"corr_{uuid.uuid4().hex[:8]}",
        retry_count=0
    )
    
    # Create agent execution core
    execution_core = AgentExecutionCore(
        registry=agent_registry,
        websocket_bridge=websocket_bridge
    )
    
    # Execute agent (this should trigger all WebSocket events)
    result = await execution_core.execute_agent(
        context=execution_context,
        state=state,
        timeout=30.0
    )
    
    # Validate results
    assert result is not None, "Agent execution should return a result"
    assert result.success, f"Agent execution should succeed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
    
    # CRITICAL VALIDATION: All 5 events must be present
    print(f"\n🔍 Captured {len(websocket_event_capture.events)} WebSocket events:")
    for event in websocket_event_capture.events:
        print(f"  - {event['type']}: {event['data'].get('agent_name', event['data'].get('tool_name', 'unknown'))}")
    
    # Check individual events
    assert len(websocket_event_capture.get_events_by_type("agent_started")) >= 1, \
        "Must send agent_started event for user transparency"
        
    assert len(websocket_event_capture.get_events_by_type("agent_thinking")) >= 1, \
        "Must send agent_thinking events for real-time user feedback"
        
    assert len(websocket_event_capture.get_events_by_type("tool_executing")) >= 1, \
        "Must send tool_executing event for tool usage transparency"
        
    assert len(websocket_event_capture.get_events_by_type("tool_completed")) >= 1, \
        "Must send tool_completed event for tool result visibility"
        
    assert len(websocket_event_capture.get_events_by_type("agent_completed")) >= 1, \
        "Must send agent_completed event for user closure"
    
    # CRITICAL: Validate all 5 events are present
    assert websocket_event_capture.has_all_critical_events(), \
        f"Missing critical events. Received: {set(websocket_event_capture.event_types)}"
    
    print("✅ SUCCESS: All 5 critical WebSocket events validated!")
    print(f"   Events sent: {', '.join(sorted(set(websocket_event_capture.event_types)))}")


@pytest.mark.asyncio 
async def test_websocket_events_with_tool_dispatcher_integration(
    websocket_event_capture,
    user_context,
    websocket_manager
):
    """Test WebSocket events specifically through tool dispatcher integration.
    
    This test focuses on the tool_executing and tool_completed events.
    """
    
    # Create WebSocket bridge
    bridge = AgentWebSocketBridge(user_context)
    bridge._websocket_manager = websocket_manager
    
    # Create tool dispatcher with WebSocket bridge
    dispatcher = await UnifiedToolDispatcher.create_for_user(
        user_context=user_context,
        websocket_bridge=bridge
    )
    
    # Register a test tool
    class TestTool:
        name = "integration_test_tool"
        
        async def arun(self, message: str = "test") -> str:
            await asyncio.sleep(0.05)  # Brief work simulation
            return f"Processed: {message}"
    
    test_tool = TestTool()
    dispatcher.register_tool(test_tool)
    
    # Execute tool (should trigger WebSocket events)
    result = await dispatcher.execute_tool(
        "integration_test_tool",
        {"message": "Hello from integration test"}
    )
    
    # Validate tool execution
    assert result.success, f"Tool execution should succeed: {result.error if hasattr(result, 'error') else 'Unknown'}"
    
    # Validate WebSocket events
    tool_executing_events = websocket_event_capture.get_events_by_type("tool_executing")
    tool_completed_events = websocket_event_capture.get_events_by_type("tool_completed")
    
    assert len(tool_executing_events) >= 1, "Must send tool_executing event"
    assert len(tool_completed_events) >= 1, "Must send tool_completed event"
    
    # Validate event data
    executing_event = tool_executing_events[0]
    completed_event = tool_completed_events[0]
    
    assert executing_event["data"]["tool_name"] == "integration_test_tool"
    assert completed_event["data"]["tool_name"] == "integration_test_tool"
    assert completed_event["data"]["status"] == "success"
    
    print("✅ Tool dispatcher WebSocket integration validated!")


if __name__ == "__main__":
    """Run the test directly for debugging."""
    asyncio.run(test_complete_websocket_event_flow(
        MockWebSocketEventCapture(),
        UserExecutionContext(
            user_id="direct_test_user",
            run_id="direct_test_run", 
            thread_id="direct_test_thread",
            session_id="direct_test_session"
        ),
        Mock(),
        AgentWebSocketBridge(),
        AgentRegistry(),
        SimpleTestAgent()
    ))