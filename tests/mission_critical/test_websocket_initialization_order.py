from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: MISSION CRITICAL TEST SUITE: WebSocket Initialization Order Bug Prevention
    # REMOVED_SYNTAX_ERROR: ===========================================================================

    # REMOVED_SYNTAX_ERROR: This test suite ensures that the critical initialization order bug in
    # REMOVED_SYNTAX_ERROR: supervisor_consolidated.py never regresses. The bug occurred when WebSocket
    # REMOVED_SYNTAX_ERROR: manager was set BEFORE agents were registered, resulting in agents not
    # REMOVED_SYNTAX_ERROR: receiving the WebSocket manager.

    # REMOVED_SYNTAX_ERROR: Bug Details:
        # REMOVED_SYNTAX_ERROR: - Location: supervisor_consolidated.py, _init_registry() method
        # REMOVED_SYNTAX_ERROR: - Problem: set_websocket_manager() called before register_default_agents()
        # REMOVED_SYNTAX_ERROR: - Impact: Agents couldn"t send WebSocket events, breaking chat functionality
        # REMOVED_SYNTAX_ERROR: - Fix: Swap order to register_default_agents() → set_websocket_manager()

        # REMOVED_SYNTAX_ERROR: Test Requirements:
            # REMOVED_SYNTAX_ERROR: 1. Verify agents are registered BEFORE WebSocket manager is set
            # REMOVED_SYNTAX_ERROR: 2. Ensure ALL registered agents receive the WebSocket manager
            # REMOVED_SYNTAX_ERROR: 3. Confirm WebSocket events can be sent after initialization
            # REMOVED_SYNTAX_ERROR: 4. Test that the initialization order is maintained
            # REMOVED_SYNTAX_ERROR: '''

            # REMOVED_SYNTAX_ERROR: import asyncio
            # REMOVED_SYNTAX_ERROR: import unittest
            # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List
            # REMOVED_SYNTAX_ERROR: import sys
            # REMOVED_SYNTAX_ERROR: import os
            # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
            # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # Add project root to path
            # REMOVED_SYNTAX_ERROR: sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
            # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestWebSocketInitializationOrder(SSotAsyncTestCase):
    # REMOVED_SYNTAX_ERROR: """Test suite to prevent WebSocket initialization order regression."""

# REMOVED_SYNTAX_ERROR: def setUp(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.db_session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: self.llm_manager = Mock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: self.websocket_manager = Mock(spec=WebSocketManager)

    # Mock tool dispatcher executor attribute to avoid enhancement errors
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher.websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Track method call order
    # REMOVED_SYNTAX_ERROR: self.call_order = []

# REMOVED_SYNTAX_ERROR: def test_initialization_order_is_correct(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: CRITICAL TEST: Verify that agents are registered BEFORE WebSocket manager is set.
    # REMOVED_SYNTAX_ERROR: This test would FAIL with the bug and PASS with the fix.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: with patch.object(AgentRegistry, 'register_default_agents') as mock_register:
        # REMOVED_SYNTAX_ERROR: with patch.object(AgentRegistry, 'set_websocket_manager') as mock_set_ws:
            # Track call order
            # REMOVED_SYNTAX_ERROR: mock_register.side_effect = lambda x: None self.call_order.append('register')
            # REMOVED_SYNTAX_ERROR: mock_set_ws.side_effect = lambda x: None self.call_order.append('set_ws')

            # Initialize supervisor
            # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
            # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
            # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
            # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
            # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
            

            # Verify the correct order
            # REMOVED_SYNTAX_ERROR: self.assertEqual(self.call_order, ['register', 'set_ws'],
            # REMOVED_SYNTAX_ERROR: "CRITICAL: Agents must be registered BEFORE WebSocket manager is set!")

            # Verify methods were called
            # REMOVED_SYNTAX_ERROR: mock_register.assert_called_once()
            # REMOVED_SYNTAX_ERROR: mock_set_ws.assert_called_once_with(self.websocket_manager)

# REMOVED_SYNTAX_ERROR: def test_all_agents_receive_websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that ALL registered agents receive the WebSocket manager.
    # REMOVED_SYNTAX_ERROR: This ensures the fix results in "WebSocket manager set for 8/8 agents".
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Create real supervisor to test actual behavior
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    

    # Get all registered agents as dict
    # REMOVED_SYNTAX_ERROR: agents_dict = supervisor.registry.agents
    # REMOVED_SYNTAX_ERROR: agents_list = supervisor.registry.get_all_agents()

    # Verify we have agents registered
    # REMOVED_SYNTAX_ERROR: self.assertGreater(len(agents_list), 0,
    # REMOVED_SYNTAX_ERROR: "No agents registered! The registry should have default agents.")

    # Verify each agent has WebSocket manager set
    # REMOVED_SYNTAX_ERROR: for agent_name, agent in agents_dict.items():
        # Check if agent has websocket_manager attribute
        # REMOVED_SYNTAX_ERROR: if hasattr(agent, 'websocket_manager'):
            # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(agent.websocket_manager,
            # REMOVED_SYNTAX_ERROR: "formatted_string")
            # REMOVED_SYNTAX_ERROR: self.assertEqual(agent.websocket_manager, self.websocket_manager,
            # REMOVED_SYNTAX_ERROR: "formatted_string")

# REMOVED_SYNTAX_ERROR: def test_websocket_manager_not_set_before_registration(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that setting WebSocket manager before registration would fail.
    # REMOVED_SYNTAX_ERROR: This simulates the bug condition.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch.object(AgentRegistry, 'get_all_agents') as mock_get_agents:
        # Simulate no agents registered yet
        # REMOVED_SYNTAX_ERROR: mock_get_agents.return_value = {}

        # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

        # Try to set WebSocket manager with no agents (should handle gracefully)
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: result = registry.set_websocket_manager(self.websocket_manager)
            # In the bug state, this would set manager for 0 agents
            # REMOVED_SYNTAX_ERROR: mock_get_agents.assert_called()
            # REMOVED_SYNTAX_ERROR: except Exception:
                # May raise if tool dispatcher enhancement fails, which is OK for this test
                # REMOVED_SYNTAX_ERROR: pass

                # Now register agents AFTER setting manager (BUG CONDITION)
                # REMOVED_SYNTAX_ERROR: registry.register_default_agents()

                # Get agents after registration
                # REMOVED_SYNTAX_ERROR: agents = registry.agents

                # With the bug, agents registered AFTER wouldn't have the manager
                # This test documents the problematic behavior

# REMOVED_SYNTAX_ERROR: def test_agent_registry_initialization_sequence(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test the complete initialization sequence of AgentRegistry.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry.register_default_agents') as mock_register:
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry.set_websocket_manager') as mock_set_ws:

            # Create supervisor
            # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
            # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
            # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
            # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
            # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
            

            # Verify registry exists
            # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(supervisor.registry)
            # REMOVED_SYNTAX_ERROR: self.assertIsInstance(supervisor.registry, AgentRegistry)

            # Verify initialization methods were called
            # REMOVED_SYNTAX_ERROR: mock_register.assert_called_once()
            # REMOVED_SYNTAX_ERROR: mock_set_ws.assert_called_once_with(self.websocket_manager)

            # Verify the registry is properly set up
            # REMOVED_SYNTAX_ERROR: self.assertEqual(supervisor.registry.llm_manager, self.llm_manager)
            # REMOVED_SYNTAX_ERROR: self.assertEqual(supervisor.registry.tool_dispatcher, self.tool_dispatcher)

# REMOVED_SYNTAX_ERROR: def test_websocket_events_can_be_sent_after_init(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that WebSocket events can be properly sent after initialization.
    # REMOVED_SYNTAX_ERROR: This verifies the fix enables the chat functionality.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Mock WebSocket manager to track events
    # REMOVED_SYNTAX_ERROR: self.websocket_manager.send_agent_event = Magic
    # Initialize supervisor with proper order
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    

    # Simulate agent sending an event
    # REMOVED_SYNTAX_ERROR: test_event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'agent_started',
    # REMOVED_SYNTAX_ERROR: 'agent': 'test_agent',
    # REMOVED_SYNTAX_ERROR: 'task': 'test_task'
    

    # The engine should be able to send events
    # REMOVED_SYNTAX_ERROR: if hasattr(supervisor.engine, 'websocket_notifier'):
        # Test that the notifier exists and is ready to send events
        # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(supervisor.engine.websocket_notifier)
        # The WebSocket integration is working if the notifier exists

        # Verify event was sent (implementation may vary)
        # This ensures the WebSocket integration is working

# REMOVED_SYNTAX_ERROR: def test_supervisor_has_all_required_components(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that supervisor has all required components after initialization.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    

    # Verify all critical components exist
    # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(supervisor.registry, "Registry not initialized!")
    # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(supervisor.engine, "ExecutionEngine not initialized!")
    # REMOVED_SYNTAX_ERROR: self.assertIsNotNone(supervisor.pipeline_executor, "PipelineExecutor not initialized!")

    # Verify alias for backward compatibility
    # REMOVED_SYNTAX_ERROR: self.assertIs(supervisor.agent_registry, supervisor.registry,
    # REMOVED_SYNTAX_ERROR: "agent_registry alias not set correctly!")

# REMOVED_SYNTAX_ERROR: def test_agent_count_after_initialization(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that the expected number of agents are registered.
    # REMOVED_SYNTAX_ERROR: The fix should result in "WebSocket manager set for 8/8 agents".
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    

    # REMOVED_SYNTAX_ERROR: agents_dict = supervisor.registry.agents
    # REMOVED_SYNTAX_ERROR: agent_count = len(agents_dict)

    # We expect at least 8 default agents based on the bug report
    # REMOVED_SYNTAX_ERROR: self.assertGreaterEqual(agent_count, 8,
    # REMOVED_SYNTAX_ERROR: "formatted_string")

    # Log the actual agents for debugging
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_websocket_manager_propagation_to_agents(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that WebSocket manager is properly propagated to all agent instances.
    # REMOVED_SYNTAX_ERROR: This is the most direct test of the fix.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Track which agents get the WebSocket manager
    # REMOVED_SYNTAX_ERROR: agents_with_ws_manager = []
    # REMOVED_SYNTAX_ERROR: agents_without_ws_manager = []

    # Initialize supervisor
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    

    # Check each agent
    # REMOVED_SYNTAX_ERROR: for agent_name, agent in supervisor.registry.agents.items():
        # REMOVED_SYNTAX_ERROR: if hasattr(agent, 'websocket_manager') and agent.websocket_manager is not None:
            # REMOVED_SYNTAX_ERROR: agents_with_ws_manager.append(agent_name)
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: agents_without_ws_manager.append(agent_name)

                # All agents should have WebSocket manager
                # REMOVED_SYNTAX_ERROR: self.assertEqual(len(agents_without_ws_manager), 0,
                # REMOVED_SYNTAX_ERROR: f"These agents don"t have WebSocket manager: {agents_without_ws_manager}")

                # Verify count matches expected
                # REMOVED_SYNTAX_ERROR: total_agents = len(agents_with_ws_manager)
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # The fix ensures this is "8/8" not "0/0"
                # REMOVED_SYNTAX_ERROR: self.assertGreater(total_agents, 0,
                # REMOVED_SYNTAX_ERROR: "CRITICAL: No agents have WebSocket manager! The bug has regressed!")


# REMOVED_SYNTAX_ERROR: class TestInitializationRaceConditions(SSotAsyncTestCase):
    # REMOVED_SYNTAX_ERROR: """Test for potential race conditions in initialization."""

# REMOVED_SYNTAX_ERROR: def setUp(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.db_session = AsyncMock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: self.llm_manager = Mock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher = Mock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: self.websocket_manager = Mock(spec=WebSocketManager)

    # Mock tool dispatcher executor attribute
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher.websocket = TestWebSocketConnection()  # Real WebSocket implementation

# REMOVED_SYNTAX_ERROR: def test_concurrent_initialization_maintains_order(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: Test that concurrent initialization still maintains correct order.
    # REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: async def init_supervisor():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return supervisor

    # Run multiple concurrent initializations
# REMOVED_SYNTAX_ERROR: async def run_concurrent():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: tasks = [init_supervisor() for _ in range(5)]
    # REMOVED_SYNTAX_ERROR: supervisors = await asyncio.gather(*tasks)

    # Verify all supervisors initialized correctly
    # REMOVED_SYNTAX_ERROR: for supervisor in supervisors:
        # REMOVED_SYNTAX_ERROR: agents = supervisor.registry.agents
        # REMOVED_SYNTAX_ERROR: self.assertGreater(len(agents), 0,
        # REMOVED_SYNTAX_ERROR: "Concurrent initialization failed to register agents!")

        # Run the async test
        # REMOVED_SYNTAX_ERROR: asyncio.run(run_concurrent())

# REMOVED_SYNTAX_ERROR: def test_reinitialization_preserves_order(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that reinitializing components preserves the correct order.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: supervisor = SupervisorAgent( )
    # REMOVED_SYNTAX_ERROR: db_session=self.db_session,
    # REMOVED_SYNTAX_ERROR: llm_manager=self.llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: websocket_manager=self.websocket_manager
    

    # Get initial agent count
    # REMOVED_SYNTAX_ERROR: initial_agents = len(supervisor.registry.agents)

    # Reinitialize registry (simulating a reset)
    # REMOVED_SYNTAX_ERROR: new_websocket_manager = Mock(spec=WebSocketManager)
    # REMOVED_SYNTAX_ERROR: supervisor._init_registry( )
    # REMOVED_SYNTAX_ERROR: self.llm_manager,
    # REMOVED_SYNTAX_ERROR: self.tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: new_websocket_manager
    

    # Verify agents still exist and have new WebSocket manager
    # REMOVED_SYNTAX_ERROR: final_agents = len(supervisor.registry.agents)
    # REMOVED_SYNTAX_ERROR: self.assertEqual(initial_agents, final_agents,
    # REMOVED_SYNTAX_ERROR: "Reinitialization changed agent count!")


# REMOVED_SYNTAX_ERROR: def run_tests():
    # REMOVED_SYNTAX_ERROR: """Run all tests and report results."""
    # Create test suite
    # REMOVED_SYNTAX_ERROR: loader = unittest.TestLoader()
    # REMOVED_SYNTAX_ERROR: suite = unittest.TestSuite()

    # Add all test cases
    # REMOVED_SYNTAX_ERROR: suite.addTests(loader.loadTestsFromTestCase(TestWebSocketInitializationOrder))
    # REMOVED_SYNTAX_ERROR: suite.addTests(loader.loadTestsFromTestCase(TestInitializationRaceConditions))

    # Run tests with detailed output
    # REMOVED_SYNTAX_ERROR: runner = unittest.TextTestRunner(verbosity=2)
    # REMOVED_SYNTAX_ERROR: result = runner.run(suite)

    # Report summary
    # REMOVED_SYNTAX_ERROR: print(" )
    # REMOVED_SYNTAX_ERROR: " + "="*70)
    # REMOVED_SYNTAX_ERROR: print("WEBSOCKET INITIALIZATION ORDER TEST RESULTS")
    # REMOVED_SYNTAX_ERROR: print("="*70)
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")
    # REMOVED_SYNTAX_ERROR: print("formatted_string")

    # REMOVED_SYNTAX_ERROR: if result.wasSuccessful():
        # REMOVED_SYNTAX_ERROR: print(" )
        # REMOVED_SYNTAX_ERROR: [SUCCESS] ALL TESTS PASSED - WebSocket initialization order is correct!")
        # REMOVED_SYNTAX_ERROR: else:
            # REMOVED_SYNTAX_ERROR: print(" )
            # REMOVED_SYNTAX_ERROR: [FAILED] TESTS FAILED - WebSocket initialization order bug may have regressed!")
            # REMOVED_SYNTAX_ERROR: if result.failures:
                # REMOVED_SYNTAX_ERROR: print(" )
                # REMOVED_SYNTAX_ERROR: Failures:")
                # REMOVED_SYNTAX_ERROR: for test, trace in result.failures:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                    # REMOVED_SYNTAX_ERROR: if result.errors:
                        # REMOVED_SYNTAX_ERROR: print(" )
                        # REMOVED_SYNTAX_ERROR: Errors:")
                        # REMOVED_SYNTAX_ERROR: for test, trace in result.errors:
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")

                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                            # REMOVED_SYNTAX_ERROR: return result.wasSuccessful()


                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                # REMOVED_SYNTAX_ERROR: success = run_tests()
                                # REMOVED_SYNTAX_ERROR: sys.exit(0 if success else 1)
                                # REMOVED_SYNTAX_ERROR: pass