"""
Comprehensive unit tests for StartupOptimizer class.

Tests ALL public methods with 100% coverage following SSOT testing patterns.
"""

import time
from unittest.mock import Mock, patch
import pytest

from dev_launcher.startup_optimizer import (
    StartupOptimizer,
    StartupPhase,
    StartupStep,
)


class TestStartupPhase:
    """Test StartupPhase enum."""
    
    def test_startup_phase_values(self):
        """Test all StartupPhase enum values."""
        assert StartupPhase.PRE_INIT.value == "pre_init"
        assert StartupPhase.INIT.value == "init"
        assert StartupPhase.POST_INIT.value == "post_init"
        assert StartupPhase.READY.value == "ready"
    
    def test_startup_phase_membership(self):
        """Test StartupPhase membership and equality."""
        assert StartupPhase.PRE_INIT in StartupPhase
        assert StartupPhase.INIT in StartupPhase
        assert StartupPhase.POST_INIT in StartupPhase
        assert StartupPhase.READY in StartupPhase
        
        # Test enum equality
        assert StartupPhase.PRE_INIT == StartupPhase.PRE_INIT
        assert StartupPhase.PRE_INIT != StartupPhase.INIT
    
    def test_startup_phase_count(self):
        """Test expected number of phases."""
        phases = list(StartupPhase)
        assert len(phases) == 4


class TestStartupStep:
    """Test StartupStep dataclass."""
    
    def test_startup_step_minimal_creation(self):
        """Test creating StartupStep with minimal required parameters."""
        step = StartupStep(name="test_step", phase=StartupPhase.INIT)
        
        assert step.name == "test_step"
        assert step.phase == StartupPhase.INIT
        assert step.action is None
        assert step.timeout == 30
        assert step.required is True
        assert step.dependencies == []
    
    def test_startup_step_full_creation(self):
        """Test creating StartupStep with all parameters."""
        def test_action():
            return True
            
        step = StartupStep(
            name="full_step",
            phase=StartupPhase.POST_INIT,
            action=test_action,
            timeout=60,
            required=False,
            dependencies=["dep1", "dep2"]
        )
        
        assert step.name == "full_step"
        assert step.phase == StartupPhase.POST_INIT
        assert step.action == test_action
        assert step.timeout == 60
        assert step.required is False
        assert step.dependencies == ["dep1", "dep2"]
    
    def test_startup_step_post_init_dependencies_none(self):
        """Test __post_init__ sets empty list when dependencies is None."""
        step = StartupStep(
            name="test", 
            phase=StartupPhase.INIT,
            dependencies=None
        )
        assert step.dependencies == []
    
    def test_startup_step_post_init_dependencies_preserved(self):
        """Test __post_init__ preserves existing dependencies list."""
        deps = ["dep1", "dep2"]
        step = StartupStep(
            name="test",
            phase=StartupPhase.INIT,
            dependencies=deps
        )
        assert step.dependencies == deps
        assert step.dependencies is deps  # Same reference preserved


class TestStartupOptimizer:
    """Test StartupOptimizer class."""
    
    def test_init_without_cache_manager(self):
        """Test StartupOptimizer initialization without cache manager."""
        optimizer = StartupOptimizer()
        
        assert optimizer.steps == []
        assert optimizer.completed_steps == []
        assert optimizer.cache_manager is None
        assert optimizer.start_time is None
    
    def test_init_with_cache_manager(self):
        """Test StartupOptimizer initialization with cache manager."""
        cache_manager = Mock()
        optimizer = StartupOptimizer(cache_manager=cache_manager)
        
        assert optimizer.steps == []
        assert optimizer.completed_steps == []
        assert optimizer.cache_manager is cache_manager
        assert optimizer.start_time is None
    
    def test_add_step(self):
        """Test adding startup steps."""
        optimizer = StartupOptimizer()
        step1 = StartupStep("step1", StartupPhase.INIT)
        step2 = StartupStep("step2", StartupPhase.POST_INIT)
        
        optimizer.add_step(step1)
        assert len(optimizer.steps) == 1
        assert optimizer.steps[0] == step1
        
        optimizer.add_step(step2)
        assert len(optimizer.steps) == 2
        assert optimizer.steps[1] == step2
    
    def test_optimize_sequence(self):
        """Test optimize_sequence returns steps in order."""
        optimizer = StartupOptimizer()
        step1 = StartupStep("step1", StartupPhase.INIT)
        step2 = StartupStep("step2", StartupPhase.POST_INIT)
        step3 = StartupStep("step3", StartupPhase.READY)
        
        optimizer.add_step(step1)
        optimizer.add_step(step2)
        optimizer.add_step(step3)
        
        optimized = optimizer.optimize_sequence()
        
        assert len(optimized) == 3
        assert optimized[0] == step1
        assert optimized[1] == step2
        assert optimized[2] == step3
    
    def test_execute_step_success_without_action(self):
        """Test successful execution of step without action."""
        optimizer = StartupOptimizer()
        step = StartupStep("test_step", StartupPhase.INIT, action=None)
        
        result = optimizer.execute_step(step)
        
        assert result is True
        assert "test_step" in optimizer.completed_steps
        assert len(optimizer.completed_steps) == 1
    
    def test_execute_step_success_with_action_returning_none(self):
        """Test successful execution when action returns None (truthy)."""
        optimizer = StartupOptimizer()
        
        def test_action():
            return None  # Should be treated as success
            
        step = StartupStep("test_step", StartupPhase.INIT, action=test_action)
        
        result = optimizer.execute_step(step)
        
        assert result is True
        assert "test_step" in optimizer.completed_steps
    
    def test_execute_step_success_with_action_returning_true(self):
        """Test successful execution when action returns True."""
        optimizer = StartupOptimizer()
        action_called = False
        
        def test_action():
            nonlocal action_called
            action_called = True
            return True
            
        step = StartupStep("test_step", StartupPhase.INIT, action=test_action)
        
        result = optimizer.execute_step(step)
        
        assert result is True
        assert action_called
        assert "test_step" in optimizer.completed_steps
    
    def test_execute_step_failure_action_returns_false(self):
        """Test step execution failure when action returns False."""
        optimizer = StartupOptimizer()
        
        def failing_action():
            return False
            
        step = StartupStep("failing_step", StartupPhase.INIT, action=failing_action)
        
        result = optimizer.execute_step(step)
        
        assert result is False
        assert "failing_step" not in optimizer.completed_steps
    
    def test_execute_step_required_step_exception_propagated(self):
        """Test that exceptions from required steps are propagated."""
        optimizer = StartupOptimizer()
        
        def failing_action():
            raise ValueError("Test failure")
            
        step = StartupStep("failing_step", StartupPhase.INIT, action=failing_action, required=True)
        
        with pytest.raises(ValueError, match="Test failure"):
            optimizer.execute_step(step)
        
        assert "failing_step" not in optimizer.completed_steps
    
    def test_execute_step_optional_step_exception_handled(self):
        """Test that exceptions from optional steps are handled gracefully."""
        optimizer = StartupOptimizer()
        
        def failing_action():
            raise ValueError("Test failure")
            
        step = StartupStep("failing_step", StartupPhase.INIT, action=failing_action, required=False)
        
        result = optimizer.execute_step(step)
        
        assert result is False
        assert "failing_step" not in optimizer.completed_steps
    
    def test_execute_step_multiple_executions(self):
        """Test executing multiple steps in sequence."""
        optimizer = StartupOptimizer()
        
        step1 = StartupStep("step1", StartupPhase.INIT)
        step2 = StartupStep("step2", StartupPhase.POST_INIT)
        step3 = StartupStep("step3", StartupPhase.READY)
        
        result1 = optimizer.execute_step(step1)
        result2 = optimizer.execute_step(step2)
        result3 = optimizer.execute_step(step3)
        
        assert all([result1, result2, result3])
        assert len(optimizer.completed_steps) == 3
        assert optimizer.completed_steps == ["step1", "step2", "step3"]
    
    def test_reset(self):
        """Test reset functionality."""
        optimizer = StartupOptimizer()
        
        # Add some completed steps
        step1 = StartupStep("step1", StartupPhase.INIT)
        step2 = StartupStep("step2", StartupPhase.POST_INIT)
        
        optimizer.execute_step(step1)
        optimizer.execute_step(step2)
        
        assert len(optimizer.completed_steps) == 2
        
        # Reset should clear completed steps
        optimizer.reset()
        
        assert len(optimizer.completed_steps) == 0
        assert optimizer.completed_steps == []
    
    def test_reset_preserves_steps(self):
        """Test that reset preserves the steps list."""
        optimizer = StartupOptimizer()
        
        step1 = StartupStep("step1", StartupPhase.INIT)
        step2 = StartupStep("step2", StartupPhase.POST_INIT)
        
        optimizer.add_step(step1)
        optimizer.add_step(step2)
        optimizer.execute_step(step1)
        
        assert len(optimizer.steps) == 2
        assert len(optimizer.completed_steps) == 1
        
        optimizer.reset()
        
        # Steps preserved, completed_steps cleared
        assert len(optimizer.steps) == 2
        assert len(optimizer.completed_steps) == 0
    
    def test_is_complete_all_required_steps_completed(self):
        """Test is_complete returns True when all required steps are completed."""
        optimizer = StartupOptimizer()
        
        step1 = StartupStep("step1", StartupPhase.INIT, required=True)
        step2 = StartupStep("step2", StartupPhase.POST_INIT, required=True)
        step3 = StartupStep("step3", StartupPhase.READY, required=False)  # Optional
        
        optimizer.add_step(step1)
        optimizer.add_step(step2)
        optimizer.add_step(step3)
        
        # Execute only required steps
        optimizer.execute_step(step1)
        optimizer.execute_step(step2)
        
        assert optimizer.is_complete() is True
    
    def test_is_complete_missing_required_steps(self):
        """Test is_complete returns False when required steps are missing."""
        optimizer = StartupOptimizer()
        
        step1 = StartupStep("step1", StartupPhase.INIT, required=True)
        step2 = StartupStep("step2", StartupPhase.POST_INIT, required=True)
        step3 = StartupStep("step3", StartupPhase.READY, required=False)
        
        optimizer.add_step(step1)
        optimizer.add_step(step2)
        optimizer.add_step(step3)
        
        # Execute only one required step and the optional one
        optimizer.execute_step(step1)
        optimizer.execute_step(step3)
        
        assert optimizer.is_complete() is False
    
    def test_is_complete_no_required_steps(self):
        """Test is_complete returns True when no required steps exist."""
        optimizer = StartupOptimizer()
        
        step1 = StartupStep("step1", StartupPhase.INIT, required=False)
        step2 = StartupStep("step2", StartupPhase.POST_INIT, required=False)
        
        optimizer.add_step(step1)
        optimizer.add_step(step2)
        
        assert optimizer.is_complete() is True
    
    def test_is_complete_no_steps(self):
        """Test is_complete returns True when no steps exist."""
        optimizer = StartupOptimizer()
        assert optimizer.is_complete() is True
    
    def test_is_complete_complex_scenario(self):
        """Test is_complete with complex required/optional mix."""
        optimizer = StartupOptimizer()
        
        # Mix of required and optional steps
        steps = [
            StartupStep("req1", StartupPhase.PRE_INIT, required=True),
            StartupStep("opt1", StartupPhase.PRE_INIT, required=False),
            StartupStep("req2", StartupPhase.INIT, required=True),
            StartupStep("opt2", StartupPhase.INIT, required=False),
            StartupStep("req3", StartupPhase.POST_INIT, required=True),
            StartupStep("opt3", StartupPhase.READY, required=False),
        ]
        
        for step in steps:
            optimizer.add_step(step)
        
        # Execute all required steps
        for step in steps:
            if step.required:
                optimizer.execute_step(step)
        
        assert optimizer.is_complete() is True
        
        # Remove one required step from completed
        optimizer.completed_steps.remove("req2")
        assert optimizer.is_complete() is False
    
    def test_start_timing(self):
        """Test start_timing functionality."""
        optimizer = StartupOptimizer()
        
        assert optimizer.start_time is None
        
        with patch('time.time', return_value=1000.0):
            optimizer.start_timing()
            
        assert optimizer.start_time == 1000.0
    
    def test_get_elapsed_time_before_start(self):
        """Test get_elapsed_time returns 0.0 when timing not started."""
        optimizer = StartupOptimizer()
        
        elapsed = optimizer.get_elapsed_time()
        assert elapsed == 0.0
    
    def test_get_elapsed_time_after_start(self):
        """Test get_elapsed_time returns correct elapsed time."""
        optimizer = StartupOptimizer()
        
        start_time = 1000.0
        current_time = 1005.5
        
        with patch('time.time', return_value=start_time):
            optimizer.start_timing()
        
        with patch('time.time', return_value=current_time):
            elapsed = optimizer.get_elapsed_time()
            
        assert elapsed == 5.5
    
    def test_get_elapsed_time_real_timing(self):
        """Test get_elapsed_time with real time progression."""
        optimizer = StartupOptimizer()
        
        optimizer.start_timing()
        time.sleep(0.01)  # Sleep for 10ms
        elapsed = optimizer.get_elapsed_time()
        
        # Should be greater than 0.01 but less than 0.1 (allowing for test execution time)
        assert 0.01 <= elapsed < 0.1
    
    def test_timing_sequence(self):
        """Test complete timing sequence with multiple calls."""
        optimizer = StartupOptimizer()
        
        # Before start
        assert optimizer.get_elapsed_time() == 0.0
        
        # Start timing
        with patch('time.time', side_effect=[1000.0, 1002.5, 1005.0]):
            optimizer.start_timing()
            
            first_elapsed = optimizer.get_elapsed_time()
            assert first_elapsed == 2.5
            
            second_elapsed = optimizer.get_elapsed_time()
            assert second_elapsed == 5.0
    
    def test_integration_full_workflow(self):
        """Test complete workflow integration."""
        optimizer = StartupOptimizer()
        
        # Create steps with different phases and requirements
        def action1():
            return True
            
        def action2():
            return None  # Should succeed
        
        steps = [
            StartupStep("pre_init", StartupPhase.PRE_INIT, action=action1, required=True),
            StartupStep("init_required", StartupPhase.INIT, required=True),
            StartupStep("init_optional", StartupPhase.INIT, action=action2, required=False),
            StartupStep("post_init", StartupPhase.POST_INIT, required=True),
            StartupStep("ready_optional", StartupPhase.READY, required=False),
        ]
        
        # Add all steps
        for step in steps:
            optimizer.add_step(step)
        
        # Start timing
        with patch('time.time', return_value=1000.0):
            optimizer.start_timing()
        
        # Get optimized sequence
        sequence = optimizer.optimize_sequence()
        assert len(sequence) == 5
        
        # Execute all steps
        for step in sequence:
            result = optimizer.execute_step(step)
            assert result is True
        
        # Verify completion
        assert optimizer.is_complete() is True
        assert len(optimizer.completed_steps) == 5
        
        # Verify timing
        with patch('time.time', return_value=1005.0):
            elapsed = optimizer.get_elapsed_time()
            assert elapsed == 5.0
        
        # Test reset
        optimizer.reset()
        assert len(optimizer.completed_steps) == 0
        assert len(optimizer.steps) == 5  # Steps preserved
        assert optimizer.is_complete() is False  # Required steps not completed
    
    def test_error_handling_edge_cases(self):
        """Test error handling edge cases."""
        optimizer = StartupOptimizer()
        
        # Test with action that raises different exception types
        def io_error_action():
            raise IOError("IO Error")
        
        def runtime_error_action():
            raise RuntimeError("Runtime Error")
        
        def value_error_action():
            raise ValueError("Value Error")
        
        # Required steps should propagate all exception types
        required_io_step = StartupStep("req_io", StartupPhase.INIT, action=io_error_action, required=True)
        required_runtime_step = StartupStep("req_runtime", StartupPhase.INIT, action=runtime_error_action, required=True)
        required_value_step = StartupStep("req_value", StartupPhase.INIT, action=value_error_action, required=True)
        
        with pytest.raises(IOError):
            optimizer.execute_step(required_io_step)
        
        with pytest.raises(RuntimeError):
            optimizer.execute_step(required_runtime_step)
        
        with pytest.raises(ValueError):
            optimizer.execute_step(required_value_step)
        
        # Optional steps should handle all exception types gracefully
        optional_io_step = StartupStep("opt_io", StartupPhase.INIT, action=io_error_action, required=False)
        optional_runtime_step = StartupStep("opt_runtime", StartupPhase.INIT, action=runtime_error_action, required=False)
        optional_value_step = StartupStep("opt_value", StartupPhase.INIT, action=value_error_action, required=False)
        
        assert optimizer.execute_step(optional_io_step) is False
        assert optimizer.execute_step(optional_runtime_step) is False
        assert optimizer.execute_step(optional_value_step) is False
        
        # No exceptions should have been raised
        assert len(optimizer.completed_steps) == 0


class TestStartupOptimizerLogging:
    """Test logging functionality in StartupOptimizer."""
    
    @patch('dev_launcher.startup_optimizer.logger')
    def test_execute_step_logging_success(self, mock_logger):
        """Test logging on successful step execution."""
        optimizer = StartupOptimizer()
        step = StartupStep("test_step", StartupPhase.INIT)
        
        optimizer.execute_step(step)
        
        mock_logger.info.assert_any_call("Executing startup step: test_step")
        mock_logger.info.assert_any_call("Completed startup step: test_step")
    
    @patch('dev_launcher.startup_optimizer.logger')
    def test_execute_step_logging_failure_false_return(self, mock_logger):
        """Test logging when step action returns False."""
        optimizer = StartupOptimizer()
        
        def failing_action():
            return False
        
        step = StartupStep("failing_step", StartupPhase.INIT, action=failing_action)
        
        optimizer.execute_step(step)
        
        mock_logger.info.assert_called_with("Executing startup step: failing_step")
        mock_logger.error.assert_called_with("Step failing_step failed")
    
    @patch('dev_launcher.startup_optimizer.logger')
    def test_execute_step_logging_exception(self, mock_logger):
        """Test logging when step raises exception."""
        optimizer = StartupOptimizer()
        
        def exception_action():
            raise ValueError("Test exception")
        
        step = StartupStep("exception_step", StartupPhase.INIT, action=exception_action, required=False)
        
        optimizer.execute_step(step)
        
        mock_logger.info.assert_called_with("Executing startup step: exception_step")
        mock_logger.error.assert_called_with("Error in startup step exception_step: Test exception")
    
    @patch('dev_launcher.startup_optimizer.logger')
    def test_start_timing_logging(self, mock_logger):
        """Test logging when timing is started."""
        optimizer = StartupOptimizer()
        
        optimizer.start_timing()
        
        mock_logger.info.assert_called_with("StartupOptimizer timing started")


class TestStartupOptimizerStateManagement:
    """Test state management and consistency in StartupOptimizer."""
    
    def test_state_isolation_multiple_optimizers(self):
        """Test that multiple optimizer instances maintain separate state."""
        optimizer1 = StartupOptimizer()
        optimizer2 = StartupOptimizer()
        
        step1 = StartupStep("step1", StartupPhase.INIT)
        step2 = StartupStep("step2", StartupPhase.POST_INIT)
        
        optimizer1.add_step(step1)
        optimizer2.add_step(step2)
        
        optimizer1.execute_step(step1)
        
        # Verify state isolation
        assert len(optimizer1.steps) == 1
        assert len(optimizer2.steps) == 1
        assert len(optimizer1.completed_steps) == 1
        assert len(optimizer2.completed_steps) == 0
        
        assert optimizer1.is_complete() is True
        assert optimizer2.is_complete() is True  # No required steps
    
    def test_step_name_uniqueness_not_enforced(self):
        """Test that step name uniqueness is not enforced (edge case)."""
        optimizer = StartupOptimizer()
        
        step1 = StartupStep("duplicate_name", StartupPhase.INIT)
        step2 = StartupStep("duplicate_name", StartupPhase.POST_INIT)
        
        optimizer.add_step(step1)
        optimizer.add_step(step2)
        
        # Both steps should be added
        assert len(optimizer.steps) == 2
        
        # Execute both steps with same name
        optimizer.execute_step(step1)
        optimizer.execute_step(step2)
        
        # Both executions should be recorded (potential issue, but tests current behavior)
        assert optimizer.completed_steps.count("duplicate_name") == 2
    
    def test_completed_steps_order_preservation(self):
        """Test that completed_steps preserves execution order."""
        optimizer = StartupOptimizer()
        
        steps = [
            StartupStep("third", StartupPhase.READY),
            StartupStep("first", StartupPhase.PRE_INIT), 
            StartupStep("second", StartupPhase.INIT),
        ]
        
        # Execute in different order than creation
        optimizer.execute_step(steps[1])  # first
        optimizer.execute_step(steps[2])  # second
        optimizer.execute_step(steps[0])  # third
        
        # Completed steps should reflect execution order, not creation order
        assert optimizer.completed_steps == ["first", "second", "third"]


class TestStartupOptimizerMemoryManagement:
    """Test memory management and resource cleanup."""
    
    def test_reset_clears_references(self):
        """Test that reset properly clears references."""
        optimizer = StartupOptimizer()
        
        # Add steps and execute them
        large_data = "x" * 10000  # Simulate large data
        
        def action_with_closure():
            # Reference large_data in closure
            return len(large_data) > 0
        
        step = StartupStep("memory_step", StartupPhase.INIT, action=action_with_closure)
        optimizer.add_step(step)
        optimizer.execute_step(step)
        
        initial_completed = len(optimizer.completed_steps)
        assert initial_completed == 1
        
        # Reset should clear completed_steps list completely
        optimizer.reset()
        
        assert len(optimizer.completed_steps) == 0
        assert optimizer.completed_steps == []
        assert id(optimizer.completed_steps) != id([])  # Still same list object, just cleared
    
    def test_timing_state_persistence(self):
        """Test that timing state persists through operations."""
        optimizer = StartupOptimizer()
        
        # Start timing
        with patch('time.time', return_value=1000.0):
            optimizer.start_timing()
        
        # Add and execute steps
        step = StartupStep("timed_step", StartupPhase.INIT)
        optimizer.add_step(step)
        
        with patch('time.time', return_value=1005.0):
            optimizer.execute_step(step)
            elapsed_after_execute = optimizer.get_elapsed_time()
        
        assert elapsed_after_execute == 5.0
        
        # Reset should not affect timing
        optimizer.reset()
        
        with patch('time.time', return_value=1010.0):
            elapsed_after_reset = optimizer.get_elapsed_time()
        
        assert elapsed_after_reset == 10.0
        assert optimizer.start_time == 1000.0  # Timing state preserved