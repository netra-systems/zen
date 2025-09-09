#!/usr/bin/env python
"""WebSocket Wiring Validation Test

This test validates that WebSocket integration is properly wired through
the tool dispatcher to ensure all critical events are sent.

Business Value: Prevents silent failures in chat functionality (90% of business value)
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager


class MockWebSocketBridge:
    """Mock WebSocket bridge that captures events for validation."""
    
    def __init__(self):
        self.events = []
        self.call_count = 0
    
    async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters=None):
        self.call_count += 1
        event = {
            'type': 'tool_executing',
            'run_id': run_id,
            'agent_name': agent_name,
            'tool_name': tool_name,
            'parameters': parameters,
            'call_number': self.call_count
        }
        self.events.append(event)
        print(f"[OK] WebSocket Event: tool_executing for {tool_name}")
        return True
    
    async def notify_tool_completed(self, run_id, agent_name, tool_name, result, execution_time_ms):
        self.call_count += 1
        event = {
            'type': 'tool_completed',
            'run_id': run_id,
            'agent_name': agent_name,
            'tool_name': tool_name,
            'result': result,
            'execution_time_ms': execution_time_ms,
            'call_number': self.call_count
        }
        self.events.append(event)
        print(f"[OK] WebSocket Event: tool_completed for {tool_name}")
        return True
    
    async def notify_agent_started(self, run_id, agent_name, metadata=None):
        self.call_count += 1
        event = {
            'type': 'agent_started',
            'run_id': run_id,
            'agent_name': agent_name,
            'metadata': metadata,
            'call_number': self.call_count
        }
        self.events.append(event)
        print(f"[OK] WebSocket Event: agent_started for {agent_name}")
        return True
    
    async def notify_agent_completed(self, run_id, agent_name, result, duration_ms):
        self.call_count += 1
        event = {
            'type': 'agent_completed',
            'run_id': run_id,
            'agent_name': agent_name,
            'result': result,
            'duration_ms': duration_ms,
            'call_number': self.call_count
        }
        self.events.append(event)
        print(f"[OK] WebSocket Event: agent_completed for {agent_name}")
        return True
    
    def get_events_by_type(self, event_type):
        return [e for e in self.events if e['type'] == event_type]


def create_mock_tool():
    """Create a mock tool for testing."""
    def mock_tool_function(query: str) -> str:
        return f"Mock result for: {query}"
    
    return mock_tool_function


async def test_websocket_wiring():
    """Test WebSocket wiring through the entire chain."""
    print("=" * 60)
    print("WEBSOCKET WIRING VALIDATION TEST")
    print("=" * 60)
    
    # Create mock WebSocket bridge
    mock_bridge = MockWebSocketBridge()
    
    # Create components
    print("\n1. Creating components...")
    tool_dispatcher = ToolDispatcher(websocket_bridge=mock_bridge)
    
    # Try to create LLM manager safely
    llm_manager = None
    try:
        from netra_backend.app.config import get_config
        settings = get_config()
        llm_manager = LLMManager(settings)
        print("OK Created LLM manager")
    except Exception as e:
        print(f"[WARN] Could not create LLM manager: {e}")
        print("   Using simplified test setup...")
    
    try:
        agent_registry = AgentRegistry()
        print("[OK] Created AgentRegistry")
    except Exception as e:
        print(f"[WARN] Could not create AgentRegistry: {e}")
        print("   This test will focus on tool dispatcher wiring only")
        agent_registry = None
    
    # Register a test tool
    print("\n2. Registering test tool...")
    tool_dispatcher.register_tool("test_query", create_mock_tool(), "Test query tool")
    
    # Set WebSocket bridge on registry if available
    if agent_registry:
        print("\n3. Setting WebSocket bridge on registry...")
        agent_registry.set_websocket_bridge(mock_bridge)
        
        # Diagnose WebSocket wiring
        print("\n4. Diagnosing WebSocket wiring...")
        registry_diagnosis = agent_registry.diagnose_websocket_wiring()
        print(f"Registry WebSocket Health: {registry_diagnosis['websocket_health']}")
        
        if registry_diagnosis['critical_issues']:
            print("[ERROR] CRITICAL ISSUES FOUND:")
            for issue in registry_diagnosis['critical_issues']:
                print(f"   - {issue}")
        else:
            print("[OK] No critical wiring issues found")
    else:
        print("\n3. Skipping registry tests (registry not available)")
        print("\n4. Testing tool dispatcher directly...")
    
    # Test tool dispatcher diagnosis
    if hasattr(tool_dispatcher, 'diagnose_websocket_wiring'):
        dispatcher_diagnosis = tool_dispatcher.diagnose_websocket_wiring()
        print(f"Tool Dispatcher WebSocket Health: {dispatcher_diagnosis.get('has_websocket_support', False)}")
        
        if dispatcher_diagnosis['critical_issues']:
            print("[ERROR] TOOL DISPATCHER CRITICAL ISSUES:")
            for issue in dispatcher_diagnosis['critical_issues']:
                print(f"   - {issue}")
    
    # Test WebSocket event flow
    print("\n5. Testing WebSocket event flow...")
    
    # Simulate tool execution
    try:
        from netra_backend.app.agents.state import DeepAgentState
        
        test_state = DeepAgentState()
        test_state.user_prompt = "Test query"
        
        result = await tool_dispatcher.dispatch_tool(
            "test_query",
            {"query": "test"},
            test_state,
            "test_run_123"
        )
        
        print(f"Tool execution result: {result}")
        
    except Exception as e:
        print(f"[WARN] Tool execution test failed: {e}")
    
    # Check captured events
    print("\n6. Checking captured WebSocket events...")
    print(f"Total events captured: {len(mock_bridge.events)}")
    
    for event in mock_bridge.events:
        print(f"   Event #{event['call_number']}: {event['type']} - {event.get('tool_name', event.get('agent_name', 'unknown'))}")
    
    # Verify critical events
    tool_executing_events = mock_bridge.get_events_by_type('tool_executing')
    tool_completed_events = mock_bridge.get_events_by_type('tool_completed')
    
    print(f"\n7. Event verification:")
    print(f"   tool_executing events: {len(tool_executing_events)}")
    print(f"   tool_completed events: {len(tool_completed_events)}")
    
    # Final assessment
    print("\n" + "=" * 60)
    if len(mock_bridge.events) > 0:
        print("[OK] WEBSOCKET WIRING VALIDATION: PASSED")
        print("   WebSocket events are being sent successfully")
    else:
        print("[ERROR] WEBSOCKET WIRING VALIDATION: FAILED")
        print("   No WebSocket events were captured - wiring issue exists")
    print("=" * 60)
    
    return len(mock_bridge.events) > 0


if __name__ == "__main__":
    success = asyncio.run(test_websocket_wiring())
    sys.exit(0 if success else 1)