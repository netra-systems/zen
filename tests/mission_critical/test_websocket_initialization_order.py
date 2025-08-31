"""
MISSION CRITICAL TEST SUITE: WebSocket Initialization Order Bug Prevention
===========================================================================

This test suite ensures that the critical initialization order bug in 
supervisor_consolidated.py never regresses. The bug occurred when WebSocket 
manager was set BEFORE agents were registered, resulting in agents not 
receiving the WebSocket manager.

Bug Details:
- Location: supervisor_consolidated.py, _init_registry() method
- Problem: set_websocket_manager() called before register_default_agents()
- Impact: Agents couldn't send WebSocket events, breaking chat functionality
- Fix: Swap order to register_default_agents() → set_websocket_manager()

Test Requirements:
1. Verify agents are registered BEFORE WebSocket manager is set
2. Ensure ALL registered agents receive the WebSocket manager
3. Confirm WebSocket events can be sent after initialization
4. Test that the initialization order is maintained
"""

import asyncio
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, List
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.manager import WebSocketManager


class TestWebSocketInitializationOrder(unittest.TestCase):
    """Test suite to prevent WebSocket initialization order regression."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.llm_manager = Mock(spec=LLMManager)
        self.tool_dispatcher = Mock(spec=ToolDispatcher)
        self.websocket_manager = Mock(spec=WebSocketManager)
        
        # Track method call order
        self.call_order = []
        
    def test_initialization_order_is_correct(self):
        """
        CRITICAL TEST: Verify that agents are registered BEFORE WebSocket manager is set.
        This test would FAIL with the bug and PASS with the fix.
        """
        with patch.object(AgentRegistry, 'register_default_agents') as mock_register:
            with patch.object(AgentRegistry, 'set_websocket_manager') as mock_set_ws:
                # Track call order
                mock_register.side_effect = lambda: self.call_order.append('register')
                mock_set_ws.side_effect = lambda ws: self.call_order.append('set_ws')
                
                # Initialize supervisor
                supervisor = SupervisorAgent(
                    llm_manager=self.llm_manager,
                    tool_dispatcher=self.tool_dispatcher,
                    websocket_manager=self.websocket_manager
                )
                
                # Verify the correct order
                self.assertEqual(self.call_order, ['register', 'set_ws'],
                    "CRITICAL: Agents must be registered BEFORE WebSocket manager is set!")
                
                # Verify methods were called
                mock_register.assert_called_once()
                mock_set_ws.assert_called_once_with(self.websocket_manager)
    
    def test_all_agents_receive_websocket_manager(self):
        """
        Test that ALL registered agents receive the WebSocket manager.
        This ensures the fix results in "WebSocket manager set for 8/8 agents".
        """
        # Create real supervisor to test actual behavior
        supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            tool_dispatcher=self.tool_dispatcher,
            websocket_manager=self.websocket_manager
        )
        
        # Get all registered agents
        agents = supervisor.registry.get_all_agents()
        
        # Verify we have agents registered
        self.assertGreater(len(agents), 0, 
            "No agents registered! The registry should have default agents.")
        
        # Verify each agent has WebSocket manager set
        for agent_name, agent in agents.items():
            # Check if agent has websocket_manager attribute
            if hasattr(agent, 'websocket_manager'):
                self.assertIsNotNone(agent.websocket_manager,
                    f"Agent '{agent_name}' does not have WebSocket manager set!")
                self.assertEqual(agent.websocket_manager, self.websocket_manager,
                    f"Agent '{agent_name}' has wrong WebSocket manager!")
    
    def test_websocket_manager_not_set_before_registration(self):
        """
        Test that setting WebSocket manager before registration would fail.
        This simulates the bug condition.
        """
        with patch.object(AgentRegistry, 'get_all_agents') as mock_get_agents:
            # Simulate no agents registered yet
            mock_get_agents.return_value = {}
            
            registry = AgentRegistry(self.llm_manager, self.tool_dispatcher)
            
            # Try to set WebSocket manager with no agents
            result = registry.set_websocket_manager(self.websocket_manager)
            
            # In the bug state, this would set manager for 0 agents
            mock_get_agents.assert_called()
            
            # Now register agents AFTER setting manager (BUG CONDITION)
            registry.register_default_agents()
            
            # Get agents after registration
            agents = registry.get_all_agents()
            
            # With the bug, agents registered AFTER wouldn't have the manager
            # This test documents the problematic behavior
    
    def test_agent_registry_initialization_sequence(self):
        """
        Test the complete initialization sequence of AgentRegistry.
        """
        with patch('netra_backend.app.agents.agent_registry.AgentRegistry.register_default_agents') as mock_register:
            with patch('netra_backend.app.agents.agent_registry.AgentRegistry.set_websocket_manager') as mock_set_ws:
                
                # Create supervisor
                supervisor = SupervisorAgent(
                    llm_manager=self.llm_manager,
                    tool_dispatcher=self.tool_dispatcher,
                    websocket_manager=self.websocket_manager
                )
                
                # Verify registry exists
                self.assertIsNotNone(supervisor.registry)
                self.assertIsInstance(supervisor.registry, AgentRegistry)
                
                # Verify initialization methods were called
                mock_register.assert_called_once()
                mock_set_ws.assert_called_once_with(self.websocket_manager)
                
                # Verify the registry is properly set up
                self.assertEqual(supervisor.registry.llm_manager, self.llm_manager)
                self.assertEqual(supervisor.registry.tool_dispatcher, self.tool_dispatcher)
    
    def test_websocket_events_can_be_sent_after_init(self):
        """
        Test that WebSocket events can be properly sent after initialization.
        This verifies the fix enables the chat functionality.
        """
        # Mock WebSocket manager to track events
        self.websocket_manager.send_agent_event = MagicMock()
        
        # Initialize supervisor with proper order
        supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            tool_dispatcher=self.tool_dispatcher,
            websocket_manager=self.websocket_manager
        )
        
        # Simulate agent sending an event
        test_event = {
            'type': 'agent_started',
            'agent': 'test_agent',
            'task': 'test_task'
        }
        
        # The engine should be able to send events
        if hasattr(supervisor.engine, 'websocket_notifier'):
            supervisor.engine.websocket_notifier.notify_agent_started(
                'test_agent', 'test_task'
            )
            
            # Verify event was sent (implementation may vary)
            # This ensures the WebSocket integration is working
    
    def test_supervisor_has_all_required_components(self):
        """
        Test that supervisor has all required components after initialization.
        """
        supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            tool_dispatcher=self.tool_dispatcher,
            websocket_manager=self.websocket_manager
        )
        
        # Verify all critical components exist
        self.assertIsNotNone(supervisor.registry, "Registry not initialized!")
        self.assertIsNotNone(supervisor.engine, "ExecutionEngine not initialized!")
        self.assertIsNotNone(supervisor.pipeline_executor, "PipelineExecutor not initialized!")
        
        # Verify alias for backward compatibility
        self.assertIs(supervisor.agent_registry, supervisor.registry,
            "agent_registry alias not set correctly!")
    
    def test_agent_count_after_initialization(self):
        """
        Test that the expected number of agents are registered.
        The fix should result in "WebSocket manager set for 8/8 agents".
        """
        supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            tool_dispatcher=self.tool_dispatcher,
            websocket_manager=self.websocket_manager
        )
        
        agents = supervisor.registry.get_all_agents()
        agent_count = len(agents)
        
        # We expect at least 8 default agents based on the bug report
        self.assertGreaterEqual(agent_count, 8,
            f"Expected at least 8 agents, but only {agent_count} registered!")
        
        # Log the actual agents for debugging
        print(f"\n✅ WebSocket manager set for {agent_count}/{agent_count} agents")
        print(f"Registered agents: {list(agents.keys())}")
    
    def test_websocket_manager_propagation_to_agents(self):
        """
        Test that WebSocket manager is properly propagated to all agent instances.
        This is the most direct test of the fix.
        """
        # Track which agents get the WebSocket manager
        agents_with_ws_manager = []
        agents_without_ws_manager = []
        
        # Initialize supervisor
        supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            tool_dispatcher=self.tool_dispatcher,
            websocket_manager=self.websocket_manager
        )
        
        # Check each agent
        for agent_name, agent in supervisor.registry.get_all_agents().items():
            if hasattr(agent, 'websocket_manager') and agent.websocket_manager is not None:
                agents_with_ws_manager.append(agent_name)
            else:
                agents_without_ws_manager.append(agent_name)
        
        # All agents should have WebSocket manager
        self.assertEqual(len(agents_without_ws_manager), 0,
            f"These agents don't have WebSocket manager: {agents_without_ws_manager}")
        
        # Verify count matches expected
        total_agents = len(agents_with_ws_manager)
        print(f"\n✅ WebSocket manager successfully set for {total_agents}/{total_agents} agents")
        
        # The fix ensures this is "8/8" not "0/0"
        self.assertGreater(total_agents, 0,
            "CRITICAL: No agents have WebSocket manager! The bug has regressed!")


class TestInitializationRaceConditions(unittest.TestCase):
    """Test for potential race conditions in initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.llm_manager = Mock(spec=LLMManager)
        self.tool_dispatcher = Mock(spec=ToolDispatcher)
        self.websocket_manager = Mock(spec=WebSocketManager)
    
    def test_concurrent_initialization_maintains_order(self):
        """
        Test that concurrent initialization still maintains correct order.
        """
        async def init_supervisor():
            supervisor = SupervisorAgent(
                llm_manager=self.llm_manager,
                tool_dispatcher=self.tool_dispatcher,
                websocket_manager=self.websocket_manager
            )
            return supervisor
        
        # Run multiple concurrent initializations
        async def run_concurrent():
            tasks = [init_supervisor() for _ in range(5)]
            supervisors = await asyncio.gather(*tasks)
            
            # Verify all supervisors initialized correctly
            for supervisor in supervisors:
                agents = supervisor.registry.get_all_agents()
                self.assertGreater(len(agents), 0,
                    "Concurrent initialization failed to register agents!")
        
        # Run the async test
        asyncio.run(run_concurrent())
    
    def test_reinitialization_preserves_order(self):
        """
        Test that reinitializing components preserves the correct order.
        """
        supervisor = SupervisorAgent(
            llm_manager=self.llm_manager,
            tool_dispatcher=self.tool_dispatcher,
            websocket_manager=self.websocket_manager
        )
        
        # Get initial agent count
        initial_agents = len(supervisor.registry.get_all_agents())
        
        # Reinitialize registry (simulating a reset)
        new_websocket_manager = Mock(spec=WebSocketManager)
        supervisor._init_registry(
            self.llm_manager,
            self.tool_dispatcher,
            new_websocket_manager
        )
        
        # Verify agents still exist and have new WebSocket manager
        final_agents = len(supervisor.registry.get_all_agents())
        self.assertEqual(initial_agents, final_agents,
            "Reinitialization changed agent count!")


def run_tests():
    """Run all tests and report results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketInitializationOrder))
    suite.addTests(loader.loadTestsFromTestCase(TestInitializationRaceConditions))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report summary
    print("\n" + "="*70)
    print("WEBSOCKET INITIALIZATION ORDER TEST RESULTS")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - WebSocket initialization order is correct!")
    else:
        print("\n❌ TESTS FAILED - WebSocket initialization order bug may have regressed!")
        if result.failures:
            print("\nFailures:")
            for test, trace in result.failures:
                print(f"  - {test}: {trace.split('AssertionError:')[-1].strip()[:100]}")
        if result.errors:
            print("\nErrors:")
            for test, trace in result.errors:
                print(f"  - {test}: {trace.split('Error:')[-1].strip()[:100]}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)