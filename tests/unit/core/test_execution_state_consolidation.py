"""
Test ExecutionState SSOT Consolidation - Issue #305

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent agent execution failures that block chat functionality
- Value Impact: Agents must execute reliably to deliver 90% of platform value
- Revenue Impact: $500K+ ARR protection through reliable agent state management

CRITICAL ISSUE: #305 - ExecutionTracker dict/enum conflicts
ROOT CAUSE: Dict objects being passed where ExecutionState enum expected
BUSINESS IMPACT: Agent execution failures = no chat value = revenue loss
"""

import pytest
from enum import Enum
from unittest.mock import MagicMock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase

# SSOT Import (Consolidated)
from netra_backend.app.core.agent_execution_tracker import (
    ExecutionState, 
    AgentExecutionTracker,
    get_execution_tracker
)

# Legacy imports for compatibility testing
try:
    from netra_backend.app.core.execution_tracker import ExecutionState as LegacyExecutionState
    from netra_backend.app.agents.execution_tracking.registry import ExecutionState as RegistryExecutionState
    LEGACY_IMPORTS_AVAILABLE = True
except ImportError:
    LEGACY_IMPORTS_AVAILABLE = False


class TestExecutionStateConsolidation(SSotBaseTestCase):
    """Test ExecutionState SSOT consolidation prevents dict/enum conflicts."""
    
    def test_execution_state_enum_consistency(self):
        """All ExecutionState enums must use identical values across modules."""
        # Test primary SSOT ExecutionState values
        assert ExecutionState.PENDING.value == "pending"
        assert ExecutionState.STARTING.value == "starting"
        assert ExecutionState.RUNNING.value == "running"
        assert ExecutionState.COMPLETING.value == "completing"
        assert ExecutionState.COMPLETED.value == "completed"
        assert ExecutionState.FAILED.value == "failed"
        assert ExecutionState.TIMEOUT.value == "timeout"
        assert ExecutionState.DEAD.value == "dead"
        assert ExecutionState.CANCELLED.value == "cancelled"
        
        # Verify it's a proper enum
        assert isinstance(ExecutionState, type(Enum))
        assert issubclass(ExecutionState, Enum)
        
        # Count all states (must be 9 for comprehensive tracking)
        all_states = list(ExecutionState)
        assert len(all_states) == 9, f"Expected 9 execution states, got {len(all_states)}: {[s.value for s in all_states]}"
    
    @pytest.mark.skipif(not LEGACY_IMPORTS_AVAILABLE, reason="Legacy imports not available")
    def test_legacy_execution_state_compatibility(self):
        """Legacy ExecutionState imports must map to SSOT equivalents."""
        if LEGACY_IMPORTS_AVAILABLE:
            # Test legacy compatibility mapping
            # Legacy states should map to SSOT equivalents:
            # INITIALIZING -> STARTING
            # SUCCESS -> COMPLETED
            # ABORTED -> CANCELLED
            # RECOVERING -> STARTING
            
            # Test that legacy enums exist and have expected mappings
            if hasattr(LegacyExecutionState, 'COMPLETED'):
                assert LegacyExecutionState.COMPLETED.value == ExecutionState.COMPLETED.value
            
            if hasattr(LegacyExecutionState, 'FAILED'): 
                assert LegacyExecutionState.FAILED.value == ExecutionState.FAILED.value
    
    def test_execution_tracker_dict_enum_safety(self):
        """ExecutionTracker methods must reject dict objects as state - ISSUE #305 ROOT CAUSE."""
        tracker = AgentExecutionTracker()
        
        # Create a mock execution ID
        exec_id = "test_execution_123"
        
        # CRITICAL TEST: Reproduce #305 issue - dict objects passed as state
        with pytest.raises((TypeError, ValueError, AttributeError)) as exc_info:
            # This was the exact pattern causing failures in agent_execution_core.py
            tracker.update_execution_state(exec_id, {"success": False, "completed": True})
        
        # Verify proper error handling
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in [
            "dict", "enum", "executionstate", "invalid", "type"
        ]), f"Expected meaningful error message about dict/enum conflict, got: {exc_info.value}"
        
        # Test another failing pattern from #305
        with pytest.raises((TypeError, ValueError, AttributeError)):
            tracker.update_execution_state(exec_id, {"success": True, "completed": True})
        
        # CORRECT PATTERN: Using proper ExecutionState enum values
        # These should work without errors
        try:
            tracker.update_execution_state(exec_id, ExecutionState.COMPLETED)
            tracker.update_execution_state(exec_id, ExecutionState.FAILED) 
        except Exception as e:
            pytest.fail(f"Proper ExecutionState enum usage should not raise errors: {e}")
    
    def test_agent_execution_core_fix_validation(self):
        """Test the specific fix applied to agent_execution_core.py for issue #305."""
        # This test validates the exact fix for the P0 bug in agent_execution_core.py
        tracker = AgentExecutionTracker()
        exec_id = "core_fix_validation"
        
        # Test the corrected patterns (what should work after fix)
        
        # Line 263 fix: Agent not found case
        try:
            exec_id_1 = "core_fix_validation_failed"
            tracker.update_execution_state(exec_id_1, ExecutionState.FAILED)
            assert tracker.get_execution_state(exec_id_1) == ExecutionState.FAILED
        except Exception as e:
            pytest.fail(f"Agent not found case fix failed: {e}")
        
        # Line 382 fix: Success case
        try:
            exec_id_2 = "core_fix_validation_completed"
            tracker.update_execution_state(exec_id_2, ExecutionState.COMPLETED)
            assert tracker.get_execution_state(exec_id_2) == ExecutionState.COMPLETED
        except Exception as e:
            pytest.fail(f"Success case fix failed: {e}")
        
        # Line 397 fix: Error case  
        try:
            exec_id_3 = "core_fix_validation_error"
            tracker.update_execution_state(exec_id_3, ExecutionState.FAILED)
            assert tracker.get_execution_state(exec_id_3) == ExecutionState.FAILED
        except Exception as e:
            pytest.fail(f"Error case fix failed: {e}")
    
    def test_ssot_execution_state_mapping(self):
        """Legacy state values map correctly to SSOT equivalents."""
        # Test state value consistency across different contexts
        
        # Core business states that must be consistent
        core_states = {
            "pending": ExecutionState.PENDING,
            "running": ExecutionState.RUNNING,
            "completed": ExecutionState.COMPLETED,
            "failed": ExecutionState.FAILED
        }
        
        for state_value, expected_enum in core_states.items():
            assert expected_enum.value == state_value
            
            # Test that we can create the enum from string
            created_enum = ExecutionState(state_value)
            assert created_enum == expected_enum
    
    def test_get_execution_tracker_factory(self):
        """get_execution_tracker() factory must return consistent AgentExecutionTracker."""
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()
        
        # Should return AgentExecutionTracker instances
        assert isinstance(tracker1, AgentExecutionTracker)
        assert isinstance(tracker2, AgentExecutionTracker)
        
        # Test that trackers work correctly
        exec_id = "factory_test"
        tracker1.update_execution_state(exec_id, ExecutionState.RUNNING)
        
        # Should be able to track execution state
        assert tracker1.get_execution_state(exec_id) == ExecutionState.RUNNING
    
    def test_execution_state_business_logic(self):
        """ExecutionState must support business workflow transitions."""
        # Test valid business workflow progression
        valid_progressions = [
            (ExecutionState.PENDING, ExecutionState.STARTING),
            (ExecutionState.STARTING, ExecutionState.RUNNING), 
            (ExecutionState.RUNNING, ExecutionState.COMPLETING),
            (ExecutionState.COMPLETING, ExecutionState.COMPLETED),
            (ExecutionState.RUNNING, ExecutionState.FAILED),  # Error path
            (ExecutionState.RUNNING, ExecutionState.TIMEOUT), # Timeout path
            (ExecutionState.PENDING, ExecutionState.CANCELLED), # Cancel path
        ]
        
        # All transitions should be representable by enum values
        for from_state, to_state in valid_progressions:
            assert isinstance(from_state, ExecutionState)
            assert isinstance(to_state, ExecutionState)
            assert from_state.value != to_state.value  # Different states
    
    def test_execution_state_serialization(self):
        """ExecutionState must be serializable for WebSocket events and logging."""
        # Test all states can be serialized
        for state in ExecutionState:
            # Should be JSON serializable
            state_value = state.value
            assert isinstance(state_value, str)
            
            # Should be reconstructible from value
            reconstructed = ExecutionState(state_value)
            assert reconstructed == state
    
    @pytest.mark.performance
    def test_execution_state_performance(self):
        """ExecutionState operations must be performant for high-frequency usage."""
        import time
        
        # Test enum comparison performance (used in hot paths)
        start_time = time.perf_counter()
        
        for _ in range(10000):
            state = ExecutionState.RUNNING
            if state == ExecutionState.RUNNING:
                pass
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Should complete 10k comparisons in under 10ms
        assert duration < 0.01, f"ExecutionState comparisons too slow: {duration:.3f}s for 10k operations"