from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
'''INTEGRATION WebSocket Bridge Test with Real Agent Classes

This test validates that the WebSocket bridge integration works with
the actual agent classes from the codebase, ensuring that the bridge
propagation patterns work end-to-end.

CRITICAL: This test prevents regressions in bridge propagation by testing
against the real BaseAgent and WebSocketBridgeAdapter classes.
'''

import sys
import os
import unittest
import asyncio
from typing import Dict, List, Any
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Force minimal environment
os.environ.update({}
'WEBSOCKET_TEST_ISOLATED': 'true',
'SKIP_REAL_SERVICES': 'true',
'USE_REAL_SERVICES': 'false'



class ComprehensiveMockBridge:
    "Mock bridge that captures all WebSocket events for validation.

    def __init__(self):
        pass
        self.events_captured = []
        self.state = active""
        self.run_id_contexts = {}

    async def notify_agent_started(self, run_id: str, agent_name: str, **kwargs):
        pass
        event = {type: agent_started, run_id: run_id, agent_name": agent_name, "kwargs: kwargs}
        self.events_captured.append(event)
        await asyncio.sleep(0)
        return True

    async def notify_agent_thinking(self, run_id: str, agent_name: str, message: str, **kwargs):
        pass
        event = {type: agent_thinking, run_id": run_id, "agent_name: agent_name, message: message, kwargs: kwargs}
        self.events_captured.append(event)
        await asyncio.sleep(0)
        return True

    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict = None, **kwargs):
        pass
        event = {type: "tool_executing, run_id": run_id, agent_name: agent_name, tool_name: tool_name, parameters: parameters, kwargs": kwargs}"
        self.events_captured.append(event)
        await asyncio.sleep(0)
        return True

    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict = None, execution_time_ms: float = None, **kwargs):
        pass
        event = {type: tool_completed, run_id: run_id, agent_name": agent_name, "tool_name: tool_name, result: result, execution_time_ms: execution_time_ms, kwargs: kwargs}
        self.events_captured.append(event)
        await asyncio.sleep(0)
        return True

    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Dict = None, execution_time_ms: float = None, **kwargs):
        pass
        event = {"type: agent_completed", run_id: run_id, agent_name: agent_name, result: result, execution_time_ms": execution_time_ms, "kwargs: kwargs}
        self.events_captured.append(event)
        await asyncio.sleep(0)
        return True

    async def notify_agent_error(self, run_id: str, agent_name: str, error: str, error_type: str = None, **kwargs):
        pass
        event = {type: agent_error, run_id": run_id, "agent_name: agent_name, error: error, error_type: error_type, kwargs: kwargs}"
        self.events_captured.append(event)
        await asyncio.sleep(0)
        return True

    def get_events_for_run(self, run_id: str) -> List[Dict]:
        return [item for item in []]

    def get_critical_events_for_run(self, run_id: str) -> List[Dict]:
        "Get the 5 critical events for business value.
        critical_types = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
        return [event for event in self.events_captured )
        if event.get(run_id") == run_id and event["type] in critical_types]


class TestWebSocketBridgeIntegration(unittest.IsolatedAsyncioTestCase):
        Integration tests with real agent classes."

    def setUp(self):
        "Set up test environment with mocks.
        self.bridge = ComprehensiveMockBridge()

    # Mock the environment and external dependencies
        self.patches = [
        patch('netra_backend.app.core.config.get_config'),
        patch('netra_backend.app.llm.llm_manager.LLMManager'),
        patch('netra_backend.app.redis_manager.RedisManager'),
        patch('netra_backend.app.agents.tool_dispatcher.ToolDispatcher'),
    

        for p in self.patches:
        mock = p.start()
        if hasattr(mock, 'return_value'):
        mock.return_value = Magic
    def tearDown(self):
        ""Clean up mocks.
        pass
        for p in self.patches:
        p.stop()

    async def test_websocket_bridge_adapter_integration(self):
        CRITICAL: WebSocketBridgeAdapter must work with real bridge.""
        try:
        from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        except ImportError as e:
        self.skipTest(formatted_string)

        adapter = WebSocketBridgeAdapter()

                    # Initially no bridge
        self.assertFalse(adapter.has_websocket_bridge())

                    # Set bridge
        adapter.set_websocket_bridge(self.bridge)
        self.assertTrue(adapter.has_websocket_bridge())

                    # Test event emission through adapter
        run_id = "adapter_test_run"

        await adapter.emit_thinking(Test thinking message)
        await adapter.emit_tool_executing(test_tool, {param": "value}
        await adapter.emit_tool_completed(test_tool, {result: success"}"

                    # Note: WebSocketBridgeAdapter may not have run_id context by default,
                    # so we check that events were emitted regardless of run_id
        self.assertTrue(len(self.bridge.events_captured) >= 3)

                    # Verify event types
        event_types = [event[type] for event in self.bridge.events_captured]
        self.assertIn(agent_thinking, event_types)"
        self.assertIn("tool_executing, event_types)
        self.assertIn(tool_completed, event_types)

    async def test_base_agent_websocket_integration(self):
        "CRITICAL: BaseAgent must integrate with WebSocket bridge."
        pass
        try:
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError as e:
        self.skipTest(formatted_string)"

                                # Create a test agent that extends BaseAgent
class TestBaseAgent(BaseAgent):
    async def __init__(self):
        pass
        super().__init__(name="TestBaseAgent)

    async def execute(self, state=None, run_id=, stream_updates=False):
        "Execute with WebSocket event emission."
        await self.emit_thinking(BaseAgent is processing)"
        await self.emit_tool_executing("base_tool, {test: True}
        await self.emit_tool_completed(base_tool, {result: "base_success}"
        await asyncio.sleep(0)
        return {status: completed, agent: self.name}"

        agent = TestBaseAgent()

    # Initially no WebSocket context
        self.assertFalse(agent.has_websocket_context())

    # Set WebSocket bridge
        agent.set_websocket_bridge(self.bridge)
        self.assertTrue(agent.has_websocket_context())

    # Execute agent
        run_id = "base_agent_test_run
        result = await agent.execute(None, run_id, True)

    # Verify execution succeeded
        self.assertIsNotNone(result)
        self.assertEqual(result[status], completed)
        self.assertEqual(result[agent"], "TestBaseAgent)

    # Verify events were emitted (note: run_id might not be propagated automatically)
        events = self.bridge.events_captured
        self.assertTrue(len(events) >= 3)

    # Check for expected event types
        event_types = [event[type] for event in events]
        self.assertIn(agent_thinking, event_types)"
        self.assertIn(tool_executing", event_types)
        self.assertIn(tool_completed, event_types)

    # Check specific event content
        thinking_events = [item for item in []] == agent_thinking"]"
        self.assertTrue(len(thinking_events) > 0)
        self.assertEqual(thinking_events[0][message], BaseAgent is processing)
        self.assertEqual(thinking_events[0][agent_name], TestBaseAgent")

    async def test_nested_agent_bridge_propagation(self):
        "CRITICAL: WebSocket bridge must propagate through nested agents.
        pass
        try:
        from netra_backend.app.agents.base_agent import BaseAgent
        except ImportError as e:
        self.skipTest(formatted_string")"

class ParentAgent(BaseAgent):
    async def __init__(self, child_agent=None):
        pass
        super().__init__(name=ParentAgent)
        self.child_agent = child_agent

    async def execute(self, state=None, run_id=, stream_updates=False):"
        pass
        await self.emit_thinking("Parent agent starting)

        if self.child_agent:
        # Propagate bridge to child
        if self.has_websocket_context() and hasattr(self.child_agent, 'set_websocket_bridge'):
        self.child_agent.set_websocket_bridge(self._websocket_adapter._websocket_bridge)

        child_result = await self.child_agent.execute(state, run_id, stream_updates)

        await self.emit_thinking(Parent agent completing)
        await asyncio.sleep(0)
        return {"status: parent_completed"}

class ChildAgent(BaseAgent):
    async def __init__(self):
        pass
        super().__init__(name=ChildAgent)

    async def execute(self, state=None, run_id=, stream_updates=False):"
        pass
        await self.emit_thinking("Child agent executing)
        await self.emit_tool_executing(child_tool, {nested: True}
        await self.emit_tool_completed(child_tool", {"child_result: success}
        await asyncio.sleep(0)
        return {status: child_completed"}

    # Set up nested agents
        child = ChildAgent()
        parent = ParentAgent(child)

    # Set bridge only on parent
        parent.set_websocket_bridge(self.bridge)

    # Execute parent (which should propagate to child)
        run_id = "nested_test_run
        result = await parent.execute(None, run_id, True)

    # Verify execution
        self.assertEqual(result[status], parent_completed)

    Verify events from both agents
        events = self.bridge.events_captured
        self.assertTrue(len(events) >= 5)  # At least 2 thinking + 1 tool_executing + 1 tool_completed + 1 thinking

    Check for events from both agents
        agent_names = {event[agent_name"] for event in events}"
        self.assertIn(ParentAgent, agent_names)
        self.assertIn(ChildAgent, agent_names)"

    # Verify child agent events (shows bridge was propagated)
        child_events = [item for item in []] == "ChildAgent]
        self.assertTrue(len(child_events) >= 3)

        child_event_types = {e[type] for e in child_events}
        self.assertIn("agent_thinking, child_event_types)"
        self.assertIn(tool_executing, child_event_types)
        self.assertIn(tool_completed, child_event_types)"

    async def test_agent_registry_bridge_propagation(self):
        "CRITICAL: AgentRegistry must propagate bridge to registered agents.
        try:
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        except ImportError as e:
        self.skipTest(""

class RegistryTestAgent(BaseAgent):
    def __init__(self, llm_manager=None, tool_dispatcher=None):
        super().__init__(name=RegistryTestAgent)
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher

    # Create registry with mocks
        mock_llm = MagicMock(spec=LLMManager)
        mock_dispatcher = MagicMock(spec=ToolDispatcher)
        mock_dispatcher.has_websocket_support = True
        mock_dispatcher.executor = MagicMock(); mock_dispatcher.diagnose_websocket_wiring = MagicMock(return_value={"critical_issues: []}"

        registry = AgentRegistry()

    # Register test agent
        test_agent = RegistryTestAgent(mock_llm, mock_dispatcher)
        registry.register(test_agent, test_agent)

    # Set bridge on registry (should propagate to agents)
        registry.set_websocket_bridge(self.bridge)

    # Verify agent received the bridge
        self.assertTrue(test_agent.has_websocket_context())

    # Test agent can emit events
        await test_agent.emit_thinking(Registry test message)"

    # Verify event was captured
        events = self.bridge.events_captured
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[-1][type"], agent_thinking)
        self.assertEqual(events[-1][message], Registry test message)
        self.assertEqual(events[-1][agent_name"], "RegistryTestAgent)

    async def test_error_handling_and_recovery(self):
        CRITICAL: Bridge must handle errors gracefully and allow recovery."
        pass
        try:
        from netra_backend.app.agents.base_agent import BaseAgent
        except ImportError as e:
        self.skipTest("

class ErrorTestAgent(BaseAgent):
    async def __init__(self):
        pass
        super().__init__(name=ErrorTestAgent)"
        self.error_on_next = False

    async def execute(self, state=None, run_id=", stream_updates=False):
        pass
        if self.error_on_next:
        await self.emit_error(Test error, test_error_type)
        raise Exception(Test error condition")"

        await self.emit_thinking(Error test agent working normally)
        await asyncio.sleep(0)
        return {status: "success}

        agent = ErrorTestAgent()
        agent.set_websocket_bridge(self.bridge)

        # Normal execution first
        run_id1 = error_test_normal"
        result1 = await agent.execute(None, run_id1, True)
        self.assertEqual(result1[status], success)

        # Error execution
        agent.error_on_next = True
        run_id2 = "error_test_error"

        with self.assertRaises(Exception):
        await agent.execute(None, run_id2, True)

            # Recovery execution
        agent.error_on_next = False
        run_id3 = error_test_recovery
        result3 = await agent.execute(None, run_id3, True)
        self.assertEqual(result3[status], success")

            # Verify error event was captured
        error_events = [item for item in []] == "agent_error]
        self.assertTrue(len(error_events) >= 1)
        self.assertEqual(error_events[0][error], Test error)
        self.assertEqual(error_events[0][error_type"], "test_error_type)

            # Verify bridge still works after error
        normal_events = [item for item in []] == agent_thinking]
        self.assertTrue(len(normal_events) >= 2)  # Before and after error


        if __name__ == '__main__':
                # Run the integration test suite
        unittest.main(verbosity=2)


class TestWebSocketConnection:
        Real WebSocket connection for testing instead of mocks.""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        Send JSON message.""
        if self._closed:
        raise RuntimeError(WebSocket is closed)
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure):"
        "Close WebSocket connection.
        pass
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        ""Get all sent messages.""
        await asyncio.sleep(0)
        return self.messages_sent.copy()
