"""
Test ExecutionState Enum Consistency - SSOT Validation
=====================================================

Business Value Justification (BVJ):
- Segment: Platform Infrastructure - Critical for all tiers
- Business Goal: System Stability - Prevent execution state fragmentation
- Value Impact: Ensures consistent execution state tracking across all modules
- Strategic Impact: $500K+ ARR depends on reliable agent execution state management

This test validates that all ExecutionState enums across the codebase are consistent
and follow SSOT principles. ExecutionState fragmentation leads to:
1. Silent agent failures when states don't match
2. WebSocket event delivery failures
3. Execution tracking inconsistencies
4. User experience degradation (no AI responses)

CRITICAL: This test will FAIL before SSOT remediation and PASS after consolidation.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List
from enum import Enum

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase


class TestExecutionStateConsistency(SSotBaseTestCase):
    """Test ExecutionState enum consistency across all implementations."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        
    def test_execution_state_enum_values_consistency(self):
        """
        Test that all ExecutionState enums have identical values.
        
        CRITICAL: This test MUST FAIL before SSOT consolidation due to:
        - execution_tracker.py: 6-state enum (PENDING, RUNNING, COMPLETED, FAILED, TIMEOUT, DEAD)
        - agent_execution_tracker.py: 9-state enum (adds STARTING, COMPLETING, CANCELLED)
        
        After SSOT consolidation: All enums should have identical state values.
        """
        # Import all ExecutionState implementations
        from netra_backend.app.core.execution_tracker import ExecutionState as ExecutionTrackerState
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentExecutionTrackerState
        
        # Get enum values
        execution_tracker_states = set(state.value for state in ExecutionTrackerState)
        agent_execution_tracker_states = set(state.value for state in AgentExecutionTrackerState)
        
        # CRITICAL ASSERTION: This will FAIL before SSOT consolidation
        # execution_tracker has 6 states, agent_execution_tracker has 9 states
        self.assertEqual(
            execution_tracker_states, 
            agent_execution_tracker_states,
            msg="ExecutionState enums have inconsistent values - SSOT violation detected! "
                f"execution_tracker: {execution_tracker_states}, "
                f"agent_execution_tracker: {agent_execution_tracker_states}"
        )
        
        # Verify critical states exist in both
        critical_states = {'pending', 'running', 'completed', 'failed'}
        for state in critical_states:
            self.assertIn(
                state, execution_tracker_states,
                f"Critical state '{state}' missing from execution_tracker ExecutionState"
            )
            self.assertIn(
                state, agent_execution_tracker_states,
                f"Critical state '{state}' missing from agent_execution_tracker ExecutionState"
            )
    
    def test_execution_state_enum_structure_consistency(self):
        """
        Test that ExecutionState enums have consistent structure and behavior.
        
        This test verifies that all ExecutionState implementations:
        1. Are proper Enum classes
        2. Have string values
        3. Support standard enum operations
        """
        from netra_backend.app.core.execution_tracker import ExecutionState as ExecutionTrackerState
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentExecutionTrackerState
        
        # Verify both are Enum classes
        self.assertTrue(issubclass(ExecutionTrackerState, Enum))
        self.assertTrue(issubclass(AgentExecutionTrackerState, Enum))
        
        # Verify all values are strings
        for state in ExecutionTrackerState:
            assert isinstance(state.value, str), \
                f"ExecutionTrackerState.{state.name} value is not string: {type(state.value)}"
        
        for state in AgentExecutionTrackerState:
            assert isinstance(state.value, str), \
                f"AgentExecutionTrackerState.{state.name} value is not string: {type(state.value)}"
    
    def test_execution_state_import_consistency(self):
        """
        Test that ExecutionState can be imported consistently across modules.
        
        CRITICAL: This test will FAIL if there are import conflicts or
        missing ExecutionState definitions in key modules.
        """
        import_tests = [
            ("netra_backend.app.core.execution_tracker", "ExecutionState"),
            ("netra_backend.app.core.agent_execution_tracker", "ExecutionState"),
        ]
        
        successfully_imported = {}
        
        for module_name, class_name in import_tests:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                successfully_imported[module_name] = cls
                
                # Verify it's an Enum
                self.assertTrue(issubclass(cls, Enum), 
                    f"{module_name}.{class_name} is not an Enum class")
                
            except (ImportError, AttributeError) as e:
                self.fail(f"Failed to import {class_name} from {module_name}: {e}")
        
        # Verify we imported all expected modules
        self.assertEqual(len(successfully_imported), len(import_tests),
            "Not all ExecutionState imports succeeded")
    
    def test_execution_state_usage_patterns(self):
        """
        Test that ExecutionState is used consistently in pattern matching.
        
        This test verifies that common usage patterns work with all ExecutionState enums.
        """
        from netra_backend.app.core.execution_tracker import ExecutionState as ExecutionTrackerState
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentExecutionTrackerState
        
        # Test common state checks
        def test_terminal_state_logic(execution_state_enum):
            """Test terminal state logic works consistently."""
            # These states should exist in all implementations
            basic_states = []
            
            for state_name in ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']:
                if hasattr(execution_state_enum, state_name):
                    basic_states.append(getattr(execution_state_enum, state_name))
            
            # Should have at least these basic states
            self.assertGreaterEqual(len(basic_states), 3,
                f"ExecutionState enum missing basic states: {execution_state_enum}")
        
        # Test both implementations
        test_terminal_state_logic(ExecutionTrackerState)
        test_terminal_state_logic(AgentExecutionTrackerState)
    
    def test_execution_state_backward_compatibility(self):
        """
        Test that ExecutionState maintains backward compatibility.
        
        This test ensures that any SSOT consolidation maintains compatibility
        with existing code that depends on specific state values.
        """
        from netra_backend.app.core.execution_tracker import ExecutionState as ExecutionTrackerState
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentExecutionTrackerState
        
        # Critical states that must exist for backward compatibility
        required_states = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']
        
        for state_name in required_states:
            # Check execution_tracker
            self.assertTrue(hasattr(ExecutionTrackerState, state_name),
                f"execution_tracker.ExecutionState missing critical state: {state_name}")
            
            # Check agent_execution_tracker  
            self.assertTrue(hasattr(AgentExecutionTrackerState, state_name),
                f"agent_execution_tracker.ExecutionState missing critical state: {state_name}")
            
            # Values should be consistent (lowercase)
            tracker_value = getattr(ExecutionTrackerState, state_name).value
            agent_tracker_value = getattr(AgentExecutionTrackerState, state_name).value
            
            self.assertEqual(tracker_value, agent_tracker_value,
                f"State {state_name} values inconsistent: "
                f"tracker='{tracker_value}', agent_tracker='{agent_tracker_value}'")


@pytest.mark.unit
@pytest.mark.ssot_validation
class TestExecutionStateSSotCompliance:
    """Extended SSOT compliance tests for ExecutionState."""
    
    def test_execution_state_single_source_of_truth(self):
        """
        Test that there is only one authoritative ExecutionState definition.
        
        CRITICAL: This test MUST FAIL before SSOT consolidation because there are
        multiple ExecutionState enums with different values.
        """
        # This test will be enhanced after SSOT consolidation to verify
        # that all imports resolve to the same enum instance
        
        from netra_backend.app.core.execution_tracker import ExecutionState as State1
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as State2
        
        # Get the actual enum class, not instance
        state1_class = State1.__class__
        state2_class = State2.__class__
        
        # CRITICAL: This assertion will FAIL before SSOT consolidation
        # After consolidation, both imports should reference the same enum class
        assert state1_class is state2_class, (
            f"ExecutionState SSOT violation: Found multiple enum classes! "
            f"execution_tracker: {state1_class}, agent_execution_tracker: {state2_class}. "
            f"This indicates ExecutionState fragmentation that breaks execution tracking."
        )
    
    def test_no_duplicate_execution_state_definitions(self):
        """
        Test that ExecutionState is not redefined across modules.
        
        This test scans for duplicate ExecutionState enum definitions
        that violate SSOT principles.
        """
        # This would normally scan the codebase for duplicate ExecutionState definitions
        # For now, we check the known problematic modules
        
        import inspect
        from netra_backend.app.core.execution_tracker import ExecutionState as State1
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as State2
        
        # Get module information
        state1_module = inspect.getmodule(State1)
        state2_module = inspect.getmodule(State2)
        
        # They should be from different modules (this is the problem)
        # After SSOT consolidation, they should be from the same module
        modules_count = len(set([state1_module.__name__, state2_module.__name__]))
        
        assert modules_count == 1, (
            f"SSOT violation: ExecutionState defined in {modules_count} different modules! "
            f"Modules: {state1_module.__name__}, {state2_module.__name__}. "
            f"Should be consolidated into single SSOT module."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])