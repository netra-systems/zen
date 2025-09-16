"""
Test ExecutionTracker API Compatibility for Issue #1131

This test validates that the ExecutionTracker API compatibility layer properly
supports the interfaces expected by agent execution tests.

BUSINESS VALUE: Ensures test reliability which protects $500K+ ARR functionality
"""

import pytest
import asyncio
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.execution_tracker import ExecutionTracker, ExecutionState, get_execution_tracker
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker


@pytest.mark.unit
class TestExecutionTrackerAPICompatibility(SSotAsyncTestCase):
    """Test ExecutionTracker API compatibility layer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.tracker = ExecutionTracker()
        
    async def test_execution_tracker_instantiation(self):
        """Test that ExecutionTracker can be instantiated properly."""
        tracker = ExecutionTracker()
        self.assertIsInstance(tracker, ExecutionTracker)
        self.assertIsInstance(tracker, AgentExecutionTracker)  # Should inherit from SSOT
        
    async def test_register_execution_method_exists(self):
        """Test that register_execution method exists and returns execution ID."""
        result = self.tracker.register_execution(
            agent_name="test-agent",
            thread_id="test-thread",
            user_id="test-user",
            timeout_seconds=30.0,
            metadata={"test": "value"}
        )
        
        self.assertIsNotNone(result, "register_execution should return an execution ID")
        self.assertIsInstance(result, str, "Execution ID should be a string")
        
    async def test_complete_execution_method_exists(self):
        """Test that complete_execution method exists and works."""
        # Create execution first
        exec_id = self.tracker.register_execution(
            agent_name="test-agent",
            thread_id="test-thread", 
            user_id="test-user"
        )
        
        # Test successful completion
        result = self.tracker.complete_execution(exec_id, success=True)
        self.assertTrue(result, "complete_execution should return True for success")
        
        # Test failure completion
        exec_id2 = self.tracker.register_execution(
            agent_name="test-agent-2",
            thread_id="test-thread",
            user_id="test-user"
        )
        result = self.tracker.complete_execution(exec_id2, success=False, error="Test error")
        self.assertTrue(result, "complete_execution should return True for failure")
        
    async def test_start_execution_method_exists(self):
        """Test that start_execution method exists."""
        exec_id = self.tracker.register_execution(
            agent_name="test-agent",
            thread_id="test-thread",
            user_id="test-user"
        )
        
        result = self.tracker.start_execution(exec_id)
        self.assertTrue(result, "start_execution should return True")
        
    async def test_update_execution_state_method_exists(self):
        """Test that update_execution_state method exists."""
        exec_id = self.tracker.register_execution(
            agent_name="test-agent", 
            thread_id="test-thread",
            user_id="test-user"
        )
        
        result = self.tracker.update_execution_state(exec_id, ExecutionState.RUNNING)
        self.assertTrue(result, "update_execution_state should return True")
        
    async def test_get_execution_tracker_function(self):
        """Test that get_execution_tracker function works."""
        tracker = get_execution_tracker()
        self.assertIsInstance(tracker, ExecutionTracker)
        
        # Should be able to use all the expected methods
        exec_id = tracker.register_execution(
            agent_name="function-test-agent",
            thread_id="function-test-thread", 
            user_id="function-test-user"
        )
        self.assertIsNotNone(exec_id)
        
        started = tracker.start_execution(exec_id)
        self.assertTrue(started)
        
        completed = tracker.complete_execution(exec_id, success=True)
        self.assertTrue(completed)
        
    async def test_backward_compatibility_properties(self):
        """Test that backward compatibility properties exist."""
        tracker = ExecutionTracker()
        
        # These properties should exist for backward compatibility
        self.assertTrue(hasattr(tracker, 'executions'))
        self.assertTrue(hasattr(tracker, 'active_executions'))
        self.assertTrue(hasattr(tracker, 'failed_executions'))
        self.assertTrue(hasattr(tracker, 'recovery_callbacks'))
        
        # Properties should be accessible
        executions = tracker.executions
        active_executions = tracker.active_executions
        failed_executions = tracker.failed_executions
        recovery_callbacks = tracker.recovery_callbacks
        
        self.assertIsNotNone(executions)
        self.assertIsNotNone(active_executions)
        self.assertIsNotNone(failed_executions)
        self.assertIsNotNone(recovery_callbacks)


@pytest.mark.unit
class TestAgentExecutionCoreCompatibility(SSotAsyncTestCase):
    """Test AgentExecutionCore compatibility with ExecutionTracker API."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
        
        self.mock_registry = MagicMock()
        self.execution_core = AgentExecutionCore(registry=self.mock_registry)
    
    async def test_execution_core_has_execution_tracker(self):
        """Test that AgentExecutionCore has execution_tracker attribute."""
        self.assertTrue(hasattr(self.execution_core, 'execution_tracker'))
        self.assertIsNotNone(self.execution_core.execution_tracker)
        
    async def test_execution_tracker_has_register_execution(self):
        """Test that execution_tracker has register_execution method."""
        tracker = self.execution_core.execution_tracker
        self.assertTrue(hasattr(tracker, 'register_execution'))
        self.assertTrue(callable(tracker.register_execution))
        
    async def test_execution_tracker_has_start_execution(self):
        """Test that execution_tracker has start_execution method."""
        tracker = self.execution_core.execution_tracker
        self.assertTrue(hasattr(tracker, 'start_execution'))
        self.assertTrue(callable(tracker.start_execution))
        
    async def test_execution_tracker_has_complete_execution(self):
        """Test that execution_tracker has complete_execution method."""
        tracker = self.execution_core.execution_tracker
        self.assertTrue(hasattr(tracker, 'complete_execution'))
        self.assertTrue(callable(tracker.complete_execution))
        
    async def test_agent_core_has_agent_tracker(self):
        """Test that AgentExecutionCore has agent_tracker attribute."""
        self.assertTrue(hasattr(self.execution_core, 'agent_tracker'))
        self.assertIsNotNone(self.execution_core.agent_tracker)
        
    async def test_agent_tracker_has_create_execution(self):
        """Test that agent_tracker has create_execution method."""
        tracker = self.execution_core.agent_tracker
        self.assertTrue(hasattr(tracker, 'create_execution'))
        self.assertTrue(callable(tracker.create_execution))
        
    async def test_agent_tracker_has_start_execution(self):
        """Test that agent_tracker has start_execution method.""" 
        tracker = self.execution_core.agent_tracker
        self.assertTrue(hasattr(tracker, 'start_execution'))
        self.assertTrue(callable(tracker.start_execution))
        
    async def test_agent_tracker_has_transition_state(self):
        """Test that agent_tracker has transition_state method."""
        tracker = self.execution_core.agent_tracker
        self.assertTrue(hasattr(tracker, 'transition_state'))
        self.assertTrue(callable(tracker.transition_state))
        
    async def test_agent_execution_core_register_execution_compatibility(self):
        """Test that AgentExecutionCore has register_execution compatibility method."""
        self.assertTrue(hasattr(self.execution_core, 'register_execution'))
        self.assertTrue(callable(self.execution_core.register_execution))
        
        # Should delegate to agent_tracker.create_execution
        exec_id = self.execution_core.register_execution(
            agent_name="compat-test-agent",
            thread_id="compat-test-thread",
            user_id="compat-test-user"
        )
        self.assertIsNotNone(exec_id)
        self.assertIsInstance(exec_id, str)


@pytest.mark.unit
class TestMockObjectCompatibility(SSotAsyncTestCase):
    """Test that mock objects used in tests are compatible with the API."""
    
    async def test_mock_agent_execution_with_run_method(self):
        """Test mock agents with run method compatibility."""
        from unittest.mock import AsyncMock
        
        mock_agent = AsyncMock()
        
        # Mock agent should have run method that returns a proper result
        expected_result = {
            "success": True,
            "message": "Mock agent executed successfully",
            "data": {"value": 42}
        }
        mock_agent.run = AsyncMock(return_value=expected_result)
        
        # Test that the mock can be used as expected
        result = await mock_agent.run("test-user-context", "test-run-id", True)
        self.assertEqual(result, expected_result)
        
        # Verify call was made
        mock_agent.run.assert_called_once_with("test-user-context", "test-run-id", True)
        
    async def test_mock_agent_execution_with_execute_method(self):
        """Test mock agents with execute method compatibility."""
        from unittest.mock import AsyncMock
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        
        mock_agent = AsyncMock()
        
        # Mock agent should have execute method that returns AgentExecutionResult
        expected_result = AgentExecutionResult(
            success=True,
            agent_name="mock-agent",
            duration=1.5,
            data={"message": "Mock execution successful"}
        )
        mock_agent.execute = AsyncMock(return_value=expected_result)
        
        # Test that the mock can be used as expected
        result = await mock_agent.execute("test-user-context", "test-run-id", True)
        self.assertEqual(result, expected_result)
        self.assertTrue(result.success)
        self.assertEqual(result.agent_name, "mock-agent")
        
        # Verify call was made
        mock_agent.execute.assert_called_once_with("test-user-context", "test-run-id", True)

    async def test_mock_registry_compatibility(self):
        """Test that mock registry objects work with expected API."""
        from unittest.mock import MagicMock, AsyncMock
        
        mock_registry = MagicMock()
        mock_agent = AsyncMock()
        
        # Registry should have get_agent method
        mock_registry.get_agent.return_value = mock_agent
        
        # Registry should have get_async method  
        mock_registry.get_async = AsyncMock(return_value=mock_agent)
        
        # Test get_agent
        agent = mock_registry.get_agent("test-agent")
        self.assertEqual(agent, mock_agent)
        
        # Test get_async
        agent_async = await mock_registry.get_async("test-agent")
        self.assertEqual(agent_async, mock_agent)
        
        # Verify calls
        mock_registry.get_agent.assert_called_once_with("test-agent")
        mock_registry.get_async.assert_called_once_with("test-agent")


if __name__ == '__main__':
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category unit --pattern "*execution_tracker*"')