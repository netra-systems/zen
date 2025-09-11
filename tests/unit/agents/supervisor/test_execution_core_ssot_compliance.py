"""
Test Agent Execution Core SSOT Compliance - Dictionary vs Enum Validation
========================================================================

Business Value Justification (BVJ):
- Segment: Platform Infrastructure - Critical for all tiers
- Business Goal: System Stability - Prevent agent execution failures
- Value Impact: Ensures agent execution core uses proper ExecutionState enums
- Strategic Impact: $500K+ ARR depends on reliable agent execution without silent failures

This test validates that agent_execution_core.py uses proper ExecutionState enum values
instead of dictionary objects when calling update_execution_state().

CRITICAL BUG PATTERN: Lines 263, 382, 397 in agent_execution_core.py historically
passed dictionary objects like {"success": False, "completed": True} instead of
ExecutionState enum values, causing 'dict' object has no attribute 'value' errors.

CRITICAL: This test will FAIL if dictionary usage returns, PASS with proper enum usage.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
import asyncio

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestAgentExecutionCoreSSotCompliance(SSotAsyncTestCase):
    """Test agent execution core SSOT compliance for ExecutionState usage."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.mock_factory = SSotMockFactory()
        
    async def test_agent_execution_core_uses_proper_execution_state_enums(self):
        """
        Test that agent_execution_core uses ExecutionState enums, not dictionaries.
        
        CRITICAL: This test validates the fix for the dictionary vs enum bug where
        update_execution_state() was called with dict objects instead of ExecutionState enums.
        
        This test will FAIL if the code reverts to passing dictionaries.
        """
        # Import required components
        from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        # Create mock registry and websocket bridge
        mock_registry = Mock()
        mock_registry.get_agent = Mock(return_value=None)
        
        mock_websocket_bridge = self.mock_factory.create_websocket_mock()
        
        # Create execution core
        execution_core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
        
        # Mock the agent tracker to capture update_execution_state calls
        mock_agent_tracker = Mock()
        execution_core.agent_tracker = mock_agent_tracker
        
        # Mock the execution tracker
        mock_execution_tracker = Mock()
        mock_execution_tracker.start_execution = AsyncMock()
        mock_execution_tracker.complete_execution = AsyncMock()
        execution_core.execution_tracker = mock_execution_tracker
        
        # Test context
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        context = AgentExecutionContext(
            agent_name="test_agent",
            run_id="test-run-123",
            thread_id="thread-123",
            user_id="user-123"
        )
        
        # Mock registry to return None (agent not found scenario)
        mock_registry.get_agent.return_value = None
        
        # Execute agent (this should trigger the agent not found path)
        try:
            await execution_core.execute_agent_safe(context)
        except Exception:
            pass  # We expect this to fail, we're testing the state update calls
        
        # CRITICAL ASSERTION: Verify update_execution_state was called with ExecutionState enum
        if mock_agent_tracker.update_execution_state.called:
            # Get the calls made to update_execution_state
            update_calls = mock_agent_tracker.update_execution_state.call_args_list
            
            for call_args in update_calls:
                args, kwargs = call_args
                
                # Second argument should be ExecutionState enum, not dict
                if len(args) >= 2:
                    state_arg = args[1]
                    
                    # CRITICAL: Must be ExecutionState enum, not dictionary
                    self.assertIsInstance(
                        state_arg, ExecutionState,
                        f"SSOT VIOLATION: update_execution_state called with {type(state_arg)} "
                        f"instead of ExecutionState enum! Value: {state_arg}. "
                        f"This indicates the dictionary vs enum bug has returned."
                    )
                    
                    # Verify it has the expected enum properties
                    self.assertTrue(
                        hasattr(state_arg, 'value'),
                        f"ExecutionState enum missing 'value' attribute: {state_arg}"
                    )
                    
                    self.assertIsInstance(
                        state_arg.value, str,
                        f"ExecutionState.value should be string, got {type(state_arg.value)}: {state_arg.value}"
                    )
    
    async def test_agent_execution_core_successful_path_enum_usage(self):
        """
        Test that successful agent execution uses ExecutionState.COMPLETED enum.
        
        This test ensures the success path (line 382 historically) uses proper enum.
        """
        from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        
        # Setup mocks
        mock_registry = Mock()
        mock_registry.get_agent = Mock()
        
        mock_websocket_bridge = self.mock_factory.create_websocket_mock()
        
        # Create mock agent that returns success
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value=AgentExecutionResult(
            success=True,
            data={"result": "test success"},
            agent_name="test_agent",
            duration=1.0
        ))
        
        mock_registry.get_agent.return_value = mock_agent
        
        # Create execution core
        execution_core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
        
        # Mock the trackers
        mock_agent_tracker = Mock()
        mock_agent_tracker.transition_state = AsyncMock()
        mock_agent_tracker.create_execution_with_full_context = Mock(return_value="state-exec-123")
        execution_core.agent_tracker = mock_agent_tracker
        
        mock_execution_tracker = Mock()
        mock_execution_tracker.start_execution = AsyncMock(return_value="exec-123")
        mock_execution_tracker.complete_execution = AsyncMock()
        execution_core.execution_tracker = mock_execution_tracker
        
        # Test context
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        context = AgentExecutionContext(
            agent_name="test_agent",
            run_id="test-run-123",
            thread_id="thread-123",
            user_id="user-123"
        )
        
        # Create mock user context
        user_context = Mock()
        user_context.user_id = "user-123"
        user_context.thread_id = "thread-123"
        
        # Execute agent successfully
        result = await execution_core.execute_agent(context, user_context)
        
        # Verify success
        self.assertTrue(result.success, "Agent execution should succeed")
        
        # CRITICAL ASSERTION: Check that update_execution_state was called with COMPLETED enum
        if mock_agent_tracker.update_execution_state.called:
            # Find the call with COMPLETED state
            update_calls = mock_agent_tracker.update_execution_state.call_args_list
            completed_calls = []
            
            for call_args in update_calls:
                args, kwargs = call_args
                if len(args) >= 2 and hasattr(args[1], 'value') and args[1].value == 'completed':
                    completed_calls.append(args[1])
            
            # Should have at least one COMPLETED state update
            self.assertGreater(
                len(completed_calls), 0,
                "Expected at least one update_execution_state call with ExecutionState.COMPLETED"
            )
            
            # Verify it's the correct enum type
            for completed_state in completed_calls:
                self.assertEqual(
                    completed_state, ExecutionState.COMPLETED,
                    f"Expected ExecutionState.COMPLETED, got {completed_state}"
                )
    
    async def test_agent_execution_core_failure_path_enum_usage(self):
        """
        Test that failed agent execution uses ExecutionState.FAILED enum.
        
        This test ensures the failure path (line 397 historically) uses proper enum.
        """
        from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
        
        # Setup mocks
        mock_registry = Mock()
        mock_registry.get_agent = Mock()
        
        mock_websocket_bridge = self.mock_factory.create_websocket_mock()
        
        # Create mock agent that returns failure
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value=AgentExecutionResult(
            success=False,
            error="Test agent failure",
            agent_name="test_agent",
            duration=0.5
        ))
        
        mock_registry.get_agent.return_value = mock_agent
        
        # Create execution core
        execution_core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
        
        # Mock the trackers
        mock_agent_tracker = Mock()
        mock_agent_tracker.transition_state = AsyncMock()
        mock_agent_tracker.create_execution_with_full_context = Mock(return_value="state-exec-123")
        execution_core.agent_tracker = mock_agent_tracker
        
        mock_execution_tracker = Mock()
        mock_execution_tracker.start_execution = AsyncMock(return_value="exec-123")
        mock_execution_tracker.complete_execution = AsyncMock()
        execution_core.execution_tracker = mock_execution_tracker
        
        # Test context
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        context = AgentExecutionContext(
            agent_name="test_agent",
            run_id="test-run-123",
            thread_id="thread-123",
            user_id="user-123"
        )
        
        # Create mock user context
        user_context = Mock()
        user_context.user_id = "user-123"
        user_context.thread_id = "thread-123"
        
        # Execute agent (should fail)
        result = await execution_core.execute_agent(context, user_context)
        
        # Verify failure
        self.assertFalse(result.success, "Agent execution should fail")
        
        # CRITICAL ASSERTION: Check that update_execution_state was called with FAILED enum
        if mock_agent_tracker.update_execution_state.called:
            # Find the call with FAILED state
            update_calls = mock_agent_tracker.update_execution_state.call_args_list
            failed_calls = []
            
            for call_args in update_calls:
                args, kwargs = call_args
                if len(args) >= 2 and hasattr(args[1], 'value') and args[1].value == 'failed':
                    failed_calls.append(args[1])
            
            # Should have at least one FAILED state update
            self.assertGreater(
                len(failed_calls), 0,
                "Expected at least one update_execution_state call with ExecutionState.FAILED"
            )
            
            # Verify it's the correct enum type
            for failed_state in failed_calls:
                self.assertEqual(
                    failed_state, ExecutionState.FAILED,
                    f"Expected ExecutionState.FAILED, got {failed_state}"
                )
    
    def test_execution_state_enum_attribute_validation(self):
        """
        Test that ExecutionState enums have required attributes and methods.
        
        This test validates that ExecutionState enums work as expected and
        won't cause 'dict' object has no attribute 'value' errors.
        """
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        # Test critical enum values exist
        critical_states = ['COMPLETED', 'FAILED', 'PENDING', 'RUNNING']
        
        for state_name in critical_states:
            # State should exist
            self.assertTrue(
                hasattr(ExecutionState, state_name),
                f"ExecutionState missing critical state: {state_name}"
            )
            
            # Get the state
            state = getattr(ExecutionState, state_name)
            
            # Should have 'value' attribute (this is what was failing with dicts)
            self.assertTrue(
                hasattr(state, 'value'),
                f"ExecutionState.{state_name} missing 'value' attribute"
            )
            
            # Value should be string
            self.assertIsInstance(
                state.value, str,
                f"ExecutionState.{state_name}.value should be string, got {type(state.value)}"
            )
            
            # Should be lowercase (convention check)
            self.assertEqual(
                state.value.lower(), state.value,
                f"ExecutionState.{state_name}.value should be lowercase: '{state.value}'"
            )
    
    def test_dictionary_objects_are_not_execution_states(self):
        """
        Test that dictionary objects don't masquerade as ExecutionState enums.
        
        This test ensures that the code can distinguish between actual ExecutionState
        enums and dictionary objects that might have similar properties.
        """
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        # Create dictionary that might look like state info (the bug pattern)
        fake_state_dict = {"success": True, "completed": True}
        state_like_dict = {"value": "completed"}  # Even has value attribute
        
        # Real ExecutionState enum
        real_state = ExecutionState.COMPLETED
        
        # Verify we can distinguish them
        self.assertNotIsInstance(
            fake_state_dict, ExecutionState,
            "Dictionary object incorrectly identified as ExecutionState"
        )
        
        self.assertNotIsInstance(
            state_like_dict, ExecutionState,
            "State-like dictionary incorrectly identified as ExecutionState"
        )
        
        self.assertIsInstance(
            real_state, ExecutionState,
            "Real ExecutionState not properly identified"
        )
        
        # Verify the bug pattern - dictionaries don't have enum behavior
        with self.assertRaises(AttributeError):
            # This is what was failing - accessing .value on a dict without 'value' key
            _ = fake_state_dict.value
        
        # But state-like dict might have value, which could mask the issue
        self.assertEqual(state_like_dict["value"], "completed")  # Dict access works
        
        # However, real enum should work properly
        self.assertEqual(real_state.value, "completed")  # Enum access works
        self.assertEqual(real_state.name, "COMPLETED")   # Enum has name attribute


@pytest.mark.unit
@pytest.mark.ssot_validation
class TestExecutionStateUsagePatterns:
    """Test execution state usage patterns for SSOT compliance."""
    
    def test_execution_state_in_conditional_logic(self):
        """Test that ExecutionState works properly in conditional logic."""
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        # Test common conditional patterns
        test_state = ExecutionState.COMPLETED
        
        # String comparison (common pattern)
        assert test_state.value == "completed"
        
        # Enum comparison (preferred pattern)
        assert test_state == ExecutionState.COMPLETED
        assert test_state is ExecutionState.COMPLETED
        
        # Boolean logic
        is_terminal = test_state in [ExecutionState.COMPLETED, ExecutionState.FAILED]
        assert is_terminal
        
        # Pattern matching style
        state_categories = {
            ExecutionState.PENDING: "active",
            ExecutionState.RUNNING: "active",
            ExecutionState.COMPLETED: "terminal",
            ExecutionState.FAILED: "terminal"
        }
        
        assert state_categories.get(test_state) == "terminal"
    
    def test_execution_state_serialization_compatibility(self):
        """Test that ExecutionState can be serialized/deserialized properly."""
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        import json
        
        # Test serialization
        state = ExecutionState.RUNNING
        
        # Should be able to get string value for serialization
        serialized = state.value
        assert isinstance(serialized, str)
        assert serialized == "running"
        
        # Should be able to create state from string (deserialization)
        deserialized = ExecutionState(serialized)
        assert deserialized == state
        assert deserialized is state  # Same enum instance
        
        # JSON serialization pattern
        state_data = {"execution_state": state.value}
        json_str = json.dumps(state_data)
        
        # JSON deserialization pattern
        loaded_data = json.loads(json_str)
        loaded_state = ExecutionState(loaded_data["execution_state"])
        assert loaded_state == state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])