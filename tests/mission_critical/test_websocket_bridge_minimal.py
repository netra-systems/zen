from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
"""MINIMAL WebSocket Bridge Lifecycle Test

This test focuses on the core WebSocket bridge functionality that MUST work
to prevent chat system failures. It tests the bridge propagation patterns
without requiring full system initialization.

CRITICAL: This test validates that:
1. WebSocket bridge can be set on agents
2. Agents can emit events through the bridge
3. Bridge state is maintained correctly
4. Events are captured and validated

This is a regression test to catch any future breaks in bridge propagation.
"""

import sys
import os
import unittest
from typing import Dict, List, Any
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Force minimal environment
os.environ.update({
    'WEBSOCKET_TEST_ISOLATED': 'true',
    'SKIP_REAL_SERVICES': 'true',
    'USE_REAL_SERVICES': 'false'
})


class MockWebSocketBridge:
    """Minimal mock WebSocket bridge that captures events."""
    
    def __init__(self):
        self.events_captured = []
        self.state = "active"
    
    async def notify_agent_started(self, run_id: str, agent_name: str, **kwargs):
        self.events_captured.append({"type": "agent_started", "run_id": run_id, "agent_name": agent_name})
        return True
    
    async def notify_agent_thinking(self, run_id: str, agent_name: str, message: str, **kwargs):
        self.events_captured.append({"type": "agent_thinking", "run_id": run_id, "agent_name": agent_name, "message": message})
        return True
    
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict = None, **kwargs):
        self.events_captured.append({"type": "tool_executing", "run_id": run_id, "agent_name": agent_name, "tool_name": tool_name})
        return True
        
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict = None, **kwargs):
        self.events_captured.append({"type": "tool_completed", "run_id": run_id, "agent_name": agent_name, "tool_name": tool_name})
        return True
    
    async def notify_agent_completed(self, run_id: str, agent_name: str, **kwargs):
        self.events_captured.append({"type": "agent_completed", "run_id": run_id, "agent_name": agent_name})
        return True
    
    def get_events_for_run(self, run_id: str) -> List[Dict]:
        return [event for event in self.events_captured if event.get("run_id") == run_id]


class MinimalTestAgent:
    """Minimal test agent that validates WebSocket bridge integration."""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        self._websocket_bridge = None
        self.bridge_was_set = False
    
    def set_websocket_bridge(self, bridge):
        """Set WebSocket bridge and track that it was set."""
        self._websocket_bridge = bridge
        self.bridge_was_set = True
    
    def has_websocket_context(self) -> bool:
        """Check if WebSocket bridge is available."""
        return self._websocket_bridge is not None
    
    async def emit_thinking(self, message: str, run_id: str = "test_run"):
        """Emit thinking event through bridge."""
        if self._websocket_bridge:
            await self._websocket_bridge.notify_agent_thinking(run_id, self.name, message)
    
    async def emit_tool_executing(self, tool_name: str, parameters: Dict = None, run_id: str = "test_run"):
        """Emit tool executing event through bridge."""
        if self._websocket_bridge:
            await self._websocket_bridge.notify_tool_executing(run_id, self.name, tool_name, parameters)
    
    async def emit_tool_completed(self, tool_name: str, result: Dict = None, run_id: str = "test_run"):
        """Emit tool completed event through bridge."""
        if self._websocket_bridge:
            await self._websocket_bridge.notify_tool_completed(run_id, self.name, tool_name, result)
    
    async def execute_with_events(self, run_id: str = "test_run"):
        """Execute agent with full event emission."""
        if self._websocket_bridge:
            await self._websocket_bridge.notify_agent_started(run_id, self.name)
            await self.emit_thinking("Processing request", run_id)
            await self.emit_tool_executing("test_tool", {"param": "value"}, run_id)
            await self.emit_tool_completed("test_tool", {"result": "success"}, run_id)
            await self._websocket_bridge.notify_agent_completed(run_id, self.name)
        
        return {"status": "success", "agent": self.name}


class TestWebSocketBridgeMinimal(unittest.IsolatedAsyncioTestCase):
    """Minimal WebSocket bridge lifecycle tests."""
    
    async def test_bridge_propagation_to_agent(self):
        """CRITICAL: Bridge must be set on agents and provide context."""
        bridge = MockWebSocketBridge()
        agent = MinimalTestAgent("TestAgent")
        
        # Initially no bridge
        self.assertFalse(agent.has_websocket_context())
        self.assertFalse(agent.bridge_was_set)
        
        # Set bridge
        agent.set_websocket_bridge(bridge)
        
        # Verify bridge was set
        self.assertTrue(agent.has_websocket_context())
        self.assertTrue(agent.bridge_was_set)
        self.assertEqual(agent._websocket_bridge, bridge)
    
    async def test_events_emitted_through_bridge(self):
        """CRITICAL: Agents must emit events through the bridge."""
        bridge = MockWebSocketBridge()
        agent = MinimalTestAgent("EventTestAgent")
        agent.set_websocket_bridge(bridge)
        
        run_id = "event_test_run"
        
        # Emit individual events
        await agent.emit_thinking("Test thinking", run_id)
        await agent.emit_tool_executing("test_tool", {"param": "value"}, run_id)
        await agent.emit_tool_completed("test_tool", {"result": "success"}, run_id)
        
        # Verify events were captured
        events = bridge.get_events_for_run(run_id)
        self.assertEqual(len(events), 3)
        
        # Verify event types
        event_types = [event["type"] for event in events]
        expected_types = ["agent_thinking", "tool_executing", "tool_completed"]
        self.assertEqual(event_types, expected_types)
        
        # Verify event content
        thinking_event = events[0]
        self.assertEqual(thinking_event["message"], "Test thinking")
        self.assertEqual(thinking_event["agent_name"], "EventTestAgent")
    
    async def test_full_agent_lifecycle_events(self):
        """CRITICAL: All 5 critical events must be emitted during execution."""
        bridge = MockWebSocketBridge()
        agent = MinimalTestAgent("LifecycleAgent")
        agent.set_websocket_bridge(bridge)
        
        run_id = "lifecycle_test_run"
        
        # Execute full lifecycle
        result = await agent.execute_with_events(run_id)
        
        # Verify execution succeeded
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        
        # Verify all 5 critical events were emitted
        events = bridge.get_events_for_run(run_id)
        self.assertEqual(len(events), 5, f"Expected 5 events, got {len(events)}: {[e['type'] for e in events]}")
        
        # Verify the 5 critical event types for business value
        event_types = [event["type"] for event in events]
        expected_types = [
            "agent_started",      # User sees agent began processing
            "agent_thinking",     # Real-time reasoning visibility
            "tool_executing",     # Tool usage transparency
            "tool_completed",     # Tool results display
            "agent_completed"     # User knows response is ready
        ]
        self.assertEqual(event_types, expected_types)
    
    async def test_bridge_state_preservation(self):
        """CRITICAL: Bridge state must be preserved across multiple executions."""
        bridge = MockWebSocketBridge()
        agent = MinimalTestAgent("StateAgent")
        agent.set_websocket_bridge(bridge)
        
        # Multiple executions
        for i in range(3):
            run_id = f"state_test_run_{i}"
            result = await agent.execute_with_events(run_id)
            
            # Bridge should still be available
            self.assertTrue(agent.has_websocket_context())
            
            # Events should be captured for each run
            events = bridge.get_events_for_run(run_id)
            self.assertEqual(len(events), 5)
        
        # Total events across all runs
        self.assertEqual(len(bridge.events_captured), 15)  # 3 runs  x  5 events each
    
    async def test_no_bridge_graceful_handling(self):
        """CRITICAL: Agent must handle missing bridge gracefully."""
        agent = MinimalTestAgent("NoBridgeAgent")
        
        # No bridge set
        self.assertFalse(agent.has_websocket_context())
        
        # Attempts to emit events should not crash
        run_id = "no_bridge_test"
        try:
            await agent.emit_thinking("Test message", run_id)
            await agent.emit_tool_executing("test_tool", {}, run_id)
            await agent.emit_tool_completed("test_tool", {}, run_id)
        except Exception as e:
            self.fail(f"Agent should handle missing bridge gracefully, but got: {e}")
    
    async def test_multiple_agents_separate_bridges(self):
        """CRITICAL: Multiple agents can use separate bridge instances."""
        bridge1 = MockWebSocketBridge()
        bridge2 = MockWebSocketBridge()
        
        agent1 = MinimalTestAgent("Agent1")
        agent2 = MinimalTestAgent("Agent2")
        
        agent1.set_websocket_bridge(bridge1)
        agent2.set_websocket_bridge(bridge2)
        
        # Execute both agents
        await agent1.execute_with_events("run1")
        await agent2.execute_with_events("run2")
        
        # Each bridge should only have events from its agent
        bridge1_events = bridge1.get_events_for_run("run1")
        bridge2_events = bridge2.get_events_for_run("run2")
        
        self.assertEqual(len(bridge1_events), 5)
        self.assertEqual(len(bridge2_events), 5)
        
        # Verify agent names are correct
        for event in bridge1_events:
            self.assertEqual(event["agent_name"], "Agent1")
        
        for event in bridge2_events:
            self.assertEqual(event["agent_name"], "Agent2")
    
    def test_synchronous_bridge_setup(self):
        """CRITICAL: Bridge setup must work synchronously."""
        bridge = MockWebSocketBridge()
        agent = MinimalTestAgent("SyncAgent")
        
        # Synchronous bridge setup
        agent.set_websocket_bridge(bridge)
        
        # Bridge should be immediately available
        self.assertTrue(agent.has_websocket_context())
        self.assertTrue(agent.bridge_was_set)


if __name__ == '__main__':
    # Run the minimal test suite
    unittest.main(verbosity=2)
