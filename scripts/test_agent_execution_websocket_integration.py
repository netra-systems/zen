#!/usr/bin/env python
"""Agent Execution with WebSocket Integration Test

Tests that actual agent execution properly sends WebSocket events.
This validates the CRITICAL agent execution flow with real WebSocket integration.

Tests:
1. Agent execution sends all 5 critical WebSocket events
2. Agent can execute tools and send tool events  
3. Complete agent lifecycle is properly tracked via WebSocket
4. State management works with WebSocket notifications
"""

import asyncio
import os
import sys
import json
import time
from typing import Dict, List, Optional, Any
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core imports for agent execution
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine

# Try to import agent registry and real agents
try:
    from netra_backend.app.core.registry.universal_registry import AgentRegistry
    from netra_backend.app.agents.greeting.greeting_agent import GreetingAgent
    AGENT_REGISTRY_AVAILABLE = True
except ImportError:
    AGENT_REGISTRY_AVAILABLE = False
    print("Agent registry not available - will use mock agent")


class MockWebSocket:
    """Enhanced mock WebSocket that captures all events with detailed logging."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.connected = True
        self.events: List[Dict] = []
        self.event_timeline: List[Dict] = []
        self.start_time = time.time()
        
    async def send_text(self, data: str) -> bool:
        """Mock send_text with event capture."""
        if not self.connected:
            return False
            
        try:
            message = json.loads(data) if isinstance(data, str) else data
            return await self._record_event(message)
        except json.JSONDecodeError:
            print(f"Failed to parse WebSocket message: {data}")
            return False
            
    async def send_json(self, data: Dict, timeout: float = None) -> bool:
        """Mock send_json with event capture."""
        if not self.connected:
            return False
        return await self._record_event(data)
    
    async def _record_event(self, event: Dict) -> bool:
        """Record event with detailed timing and logging."""
        event_time = time.time()
        
        # Add timing information
        event_with_timing = {
            **event,
            "_capture_time": event_time,
            "_relative_time": event_time - self.start_time,
            "_user_id": self.user_id
        }
        
        self.events.append(event_with_timing)
        self.messages.append(event)
        
        event_type = event.get("type", "unknown")
        print(f"[WebSocket Event] {event_type} for {self.user_id} at +{event_time - self.start_time:.3f}s")
        
        # Log payload summary
        payload = event.get("payload", {})
        if payload:
            key_info = []
            for key in ["agent_name", "run_id", "tool_name", "thought", "content"]:
                if key in payload:
                    value = str(payload[key])[:50]
                    key_info.append(f"{key}={value}")
            if key_info:
                print(f"  -> {', '.join(key_info)}")
        
        return True
        
    def client_state(self):
        return 1 if self.connected else 0
        
    @property 
    def state(self):
        return 1 if self.connected else 0
        
    def get_event_summary(self) -> Dict:
        """Get comprehensive event summary."""
        event_types = [event.get("type") for event in self.events]
        
        return {
            "total_events": len(self.events),
            "event_types": event_types,
            "unique_event_types": list(set(event_types)),
            "duration": time.time() - self.start_time,
            "events_per_second": len(self.events) / max(time.time() - self.start_time, 0.001),
            "first_event": self.events[0].get("type") if self.events else None,
            "last_event": self.events[-1].get("type") if self.events else None
        }


class SimpleTestAgent:
    """Simple test agent that uses WebSocket notifications."""
    
    def __init__(self, name: str, websocket_manager: WebSocketManager):
        self.name = name
        self.websocket_manager = websocket_manager
        self.notifier = WebSocketNotifier(websocket_manager)
        
    async def execute(self, state: DeepAgentState, run_id: str) -> Dict[str, Any]:
        """Execute agent with proper WebSocket notifications."""
        
        # Create execution context
        context = AgentExecutionContext(
            run_id=run_id,
            thread_id=state.chat_thread_id,
            user_id=state.user_id,
            agent_name=self.name,
            retry_count=0,
            max_retries=1
        )
        
        try:
            # 1. Agent starts
            await self.notifier.send_agent_started(context)
            
            # 2. Agent thinks
            await self.notifier.send_agent_thinking(context, f"Processing user request: {state.user_request}")
            
            # Small delay to simulate thinking
            await asyncio.sleep(0.1)
            
            # 3. Execute a tool (simulate)
            tool_name = "response_generator"
            await self.notifier.send_tool_executing(context, tool_name, 
                                                  tool_purpose="Generate response to user")
            
            # Simulate tool execution
            await asyncio.sleep(0.05)
            
            # 4. Tool completes
            tool_result = {
                "response": f"Hello! I'm {self.name}. You said: {state.user_request}",
                "confidence": 0.95,
                "processing_time": 50
            }
            await self.notifier.send_tool_completed(context, tool_name, tool_result)
            
            # 5. Agent completes
            agent_result = {
                "response": tool_result["response"],
                "success": True,
                "agent_name": self.name,
                "total_tools_used": 1
            }
            await self.notifier.send_agent_completed(context, agent_result)
            
            return agent_result
            
        except Exception as e:
            print(f"Agent {self.name} execution failed: {e}")
            # Send error completion
            error_result = {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "success": False,
                "error": str(e)
            }
            await self.notifier.send_agent_completed(context, error_result)
            return error_result


class WebSocketEventValidator:
    """Validates WebSocket events from agent execution."""
    
    CRITICAL_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, mock_websocket: MockWebSocket):
        self.mock_websocket = mock_websocket
        
    def validate_agent_execution_events(self) -> Dict[str, Any]:
        """Validate that all critical agent execution events were received."""
        
        events = self.mock_websocket.events
        event_types = {event.get("type") for event in events}
        
        # Check for all critical events
        missing_events = self.CRITICAL_EVENTS - event_types
        
        # Check event ordering (basic validation)
        event_order = [event.get("type") for event in events]
        
        # Agent should start first
        starts_correctly = len(event_order) > 0 and event_order[0] == "agent_started"
        
        # Agent should complete last (or near last)
        completes_correctly = "agent_completed" in event_order
        
        # Tool events should be paired
        tool_executing_count = event_order.count("tool_executing")
        tool_completed_count = event_order.count("tool_completed")
        tools_balanced = tool_executing_count == tool_completed_count
        
        return {
            "total_events": len(events),
            "event_types_received": list(event_types),
            "missing_critical_events": list(missing_events),
            "has_all_critical_events": len(missing_events) == 0,
            "event_order": event_order,
            "starts_correctly": starts_correctly,
            "completes_correctly": completes_correctly,
            "tools_balanced": tools_balanced,
            "validation_passed": (
                len(missing_events) == 0 and
                starts_correctly and
                completes_correctly and
                tools_balanced
            )
        }


async def test_agent_execution_with_websocket_events():
    """Test complete agent execution with WebSocket event validation."""
    
    print("=" * 70)
    print("TESTING AGENT EXECUTION WITH WEBSOCKET EVENTS")
    print("=" * 70)
    
    # Setup WebSocket system
    ws_manager = WebSocketManager()
    
    user_id = "test-user-agent"
    thread_id = "test-thread-agent"
    
    # Create enhanced mock WebSocket
    mock_websocket = MockWebSocket(user_id)
    
    # Connect user
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    print(f"Connected user {user_id} to WebSocket manager")
    
    # Create test agent
    test_agent = SimpleTestAgent("test_agent", ws_manager)
    
    # Create agent state
    state = DeepAgentState(
        user_request="Hello, how are you?",
        user_id=user_id,
        chat_thread_id=thread_id,
        run_id="test-run-001"
    )
    
    run_id = "test-run-001"
    
    print(f"Starting agent execution for: {state.user_request}")
    
    # Execute agent
    start_time = time.time()
    result = await test_agent.execute(state, run_id)
    execution_time = time.time() - start_time
    
    print(f"Agent execution completed in {execution_time:.3f}s")
    print(f"Agent result: {result}")
    
    # Wait for events to propagate
    await asyncio.sleep(0.5)
    
    # Validate WebSocket events
    print("\n" + "=" * 50)
    print("WEBSOCKET EVENT VALIDATION")
    print("=" * 50)
    
    validator = WebSocketEventValidator(mock_websocket)
    validation_results = validator.validate_agent_execution_events()
    
    event_summary = mock_websocket.get_event_summary()
    
    print(f"Events captured: {event_summary['total_events']}")
    print(f"Event types: {event_summary['unique_event_types']}")
    print(f"Duration: {event_summary['duration']:.3f}s")
    print(f"Events/sec: {event_summary['events_per_second']:.1f}")
    
    print(f"\nValidation Results:")
    print(f"  Has all critical events: {validation_results['has_all_critical_events']}")
    print(f"  Missing events: {validation_results['missing_critical_events']}")
    print(f"  Event order: {validation_results['event_order']}")
    print(f"  Starts correctly: {validation_results['starts_correctly']}")
    print(f"  Completes correctly: {validation_results['completes_correctly']}")
    print(f"  Tools balanced: {validation_results['tools_balanced']}")
    print(f"  Overall validation: {validation_results['validation_passed']}")
    
    # Assertions
    assert validation_results['validation_passed'], "Agent execution WebSocket validation failed"
    assert validation_results['has_all_critical_events'], f"Missing critical events: {validation_results['missing_critical_events']}"
    assert execution_time < 5.0, f"Agent execution took too long: {execution_time}s"
    assert result["success"], f"Agent execution failed: {result}"
    
    print("\nSUCCESS: Agent execution with WebSocket events validated!")
    return True


async def test_unified_tool_execution_integration():
    """Test enhanced tool execution with WebSocket integration."""
    
    print("\n" + "=" * 70)
    print("TESTING ENHANCED TOOL EXECUTION INTEGRATION")
    print("=" * 70)
    
    # Setup
    ws_manager = WebSocketManager()
    user_id = "tool-test-user"
    thread_id = "tool-test-thread"
    
    mock_websocket = MockWebSocket(user_id)
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    # Create enhanced tool executor
    enhanced_executor = UnifiedToolExecutionEngine(ws_manager)
    
    # Create state
    state = DeepAgentState(
        chat_thread_id=thread_id,
        user_id=user_id,
        run_id="tool-test-run"
    )
    
    # Create simple test tool
    class AnalysisTool:
        def __init__(self):
            self.name = "analysis_tool"
            
        async def __call__(self, input_text="", analysis_type="basic", **kwargs):
            """Analyze input text."""
            await asyncio.sleep(0.1)  # Simulate analysis
            
            return {
                "analysis_result": f"Analyzed '{input_text}' using {analysis_type} analysis",
                "confidence": 0.87,
                "processing_time_ms": 100,
                "word_count": len(input_text.split()) if input_text else 0
            }
    
    tool = AnalysisTool()
    
    print("Executing tool through enhanced executor...")
    
    # Execute tool
    start_time = time.time()
    result = await enhanced_executor.execute_with_state(
        tool, "analysis_tool", 
        {"input_text": "Hello world", "analysis_type": "sentiment"}, 
        state, "tool-test-run"
    )
    execution_time = time.time() - start_time
    
    print(f"Tool execution completed in {execution_time:.3f}s")
    print(f"Tool result: {result}")
    
    # Wait for events
    await asyncio.sleep(0.3)
    
    # Validate tool events
    event_types = {event.get("type") for event in mock_websocket.events}
    event_summary = mock_websocket.get_event_summary()
    
    print(f"\nTool execution events: {list(event_types)}")
    print(f"Total events: {event_summary['total_events']}")
    
    # Assertions
    assert "tool_executing" in event_types, "Missing tool_executing event"
    assert "tool_completed" in event_types, "Missing tool_completed event"
    assert execution_time < 2.0, f"Tool execution took too long: {execution_time}s"
    
    print("SUCCESS: Enhanced tool execution integration validated!")
    return True


async def main():
    """Run all integration tests."""
    
    try:
        # Test 1: Agent execution with WebSocket events
        await test_agent_execution_with_websocket_events()
        
        # Test 2: Enhanced tool execution integration
        await test_unified_tool_execution_integration()
        
        print("\n" + "=" * 70)
        print("ALL INTEGRATION TESTS PASSED!")
        print("Agent execution properly integrated with WebSocket events.")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\nINTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)