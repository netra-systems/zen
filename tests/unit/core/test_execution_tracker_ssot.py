"""
Test Unified ExecutionTracker SSOT Compliance
=============================================

Business Value Justification (BVJ):
- Segment: Platform Infrastructure - Critical for all tiers
- Business Goal: System Stability - Eliminate execution tracker duplication
- Value Impact: Ensures single source of truth for execution tracking across all modules
- Strategic Impact: $500K+ ARR depends on consistent execution tracking without fragmentation

This test validates that there is only one ExecutionTracker implementation and that
all execution tracking functionality is consolidated under SSOT principles.

CRITICAL FRAGMENTATION ISSUE: Currently there are multiple execution tracking implementations:
1. `netra_backend/app/core/execution_tracker.py` - Basic execution tracking
2. `netra_backend/app/core/agent_execution_tracker.py` - Enhanced agent tracking
3. `netra_backend/app/agents/execution_tracking/tracker.py` - Orchestration layer

CRITICAL: This test will FAIL before SSOT consolidation and PASS after unification.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Optional
import asyncio
import inspect
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestExecutionTrackerSSotCompliance(SSotAsyncTestCase):
    """Test ExecutionTracker SSOT compliance across all implementations."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.mock_factory = SSotMockFactory()
        
    def test_single_execution_tracker_implementation_exists(self):
        """
        Test that only one ExecutionTracker implementation exists (SSOT principle).
        
        CRITICAL: This test MUST FAIL before SSOT consolidation due to multiple
        ExecutionTracker classes across different modules.
        
        After consolidation: All ExecutionTracker references should point to same class.
        """
        # Import all ExecutionTracker implementations
        tracker_implementations = []
        
        try:
            from netra_backend.app.core.execution_tracker import ExecutionTracker as CoreTracker
            tracker_implementations.append(("core.execution_tracker", CoreTracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker as AgentTracker
            # Also test ExecutionTracker alias
            from netra_backend.app.core.agent_execution_tracker import ExecutionTracker as AgentExecutionTrackerAlias
            tracker_implementations.append(("core.agent_execution_tracker.AgentExecutionTracker", AgentTracker))
            tracker_implementations.append(("core.agent_execution_tracker.ExecutionTracker", AgentExecutionTrackerAlias))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.agents.execution_tracking.tracker import ExecutionTracker as OrchestrationTracker
            tracker_implementations.append(("agents.execution_tracking.tracker", OrchestrationTracker))
        except ImportError:
            pass
        
        # CRITICAL ASSERTION: Should have only one unique ExecutionTracker class
        unique_classes = set()
        for module_name, tracker_class in tracker_implementations:
            unique_classes.add(id(tracker_class))  # Use id to check if it's the same class object
        
        self.assertEqual(
            len(unique_classes), 1,
            f"SSOT VIOLATION: Found {len(unique_classes)} different ExecutionTracker implementations! "
            f"Modules: {[impl[0] for impl in tracker_implementations]}. "
            f"Should have only ONE unified ExecutionTracker class."
        )
        
        # Verify all implementations are actually the same class
        if len(tracker_implementations) > 1:
            base_class = tracker_implementations[0][1]
            for module_name, tracker_class in tracker_implementations[1:]:
                self.assertIs(
                    tracker_class, base_class,
                    f"ExecutionTracker from {module_name} is different class than base implementation. "
                    f"This violates SSOT principle - all should reference the same class."
                )
    
    def test_execution_tracker_interface_consistency(self):
        """
        Test that all ExecutionTracker implementations have consistent interfaces.
        
        This test validates that regardless of where ExecutionTracker is imported from,
        it provides the same interface and functionality.
        """
        tracker_classes = []
        
        # Collect all available ExecutionTracker classes
        try:
            from netra_backend.app.core.execution_tracker import ExecutionTracker
            tracker_classes.append(("execution_tracker", ExecutionTracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            tracker_classes.append(("agent_execution_tracker", AgentExecutionTracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.agents.execution_tracking.tracker import ExecutionTracker as OrchTracker
            tracker_classes.append(("orchestration_tracker", OrchTracker))
        except ImportError:
            pass
        
        if len(tracker_classes) <= 1:
            # If there's only one implementation, that's good for SSOT
            return
        
        # Check interface consistency across all implementations
        expected_methods = set()
        method_signatures = {}
        
        # Get methods from first implementation
        first_class = tracker_classes[0][1]
        expected_methods = {
            method for method in dir(first_class) 
            if not method.startswith('_') and callable(getattr(first_class, method, None))
        }
        
        # Get method signatures from first implementation
        for method_name in expected_methods:
            try:
                method = getattr(first_class, method_name)
                sig = inspect.signature(method)
                method_signatures[method_name] = sig
            except (AttributeError, ValueError):
                pass
        
        # Verify all other implementations have the same interface
        for module_name, tracker_class in tracker_classes[1:]:
            class_methods = {
                method for method in dir(tracker_class)
                if not method.startswith('_') and callable(getattr(tracker_class, method, None))
            }
            
            # Check for missing methods
            missing_methods = expected_methods - class_methods
            if missing_methods:
                self.fail(
                    f"SSOT Interface Violation: {module_name} ExecutionTracker missing methods: "
                    f"{missing_methods}. All ExecutionTracker implementations must have identical interfaces."
                )
            
            # Check for extra methods (could indicate divergence)
            extra_methods = class_methods - expected_methods
            if extra_methods:
                # Allow some extra methods, but log them
                print(f"Warning: {module_name} has additional methods: {extra_methods}")
            
            # Check method signatures match
            for method_name in expected_methods.intersection(class_methods):
                try:
                    method = getattr(tracker_class, method_name)
                    sig = inspect.signature(method)
                    expected_sig = method_signatures.get(method_name)
                    
                    if expected_sig and sig != expected_sig:
                        # Method signature mismatch
                        print(f"Warning: {module_name}.{method_name} has different signature: {sig} vs {expected_sig}")
                except (AttributeError, ValueError):
                    pass
    
    async def test_execution_tracker_factory_consistency(self):
        """
        Test that factory functions return consistent ExecutionTracker instances.
        
        This test validates that all factory functions that create ExecutionTracker
        instances return objects with consistent behavior.
        """
        factory_functions = []
        
        # Collect factory functions
        try:
            from netra_backend.app.core.execution_tracker import get_execution_tracker
            factory_functions.append(("get_execution_tracker", get_execution_tracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker as get_agent_tracker
            factory_functions.append(("get_agent_execution_tracker", get_agent_tracker))
        except ImportError:
            pass
        
        if len(factory_functions) <= 1:
            # Only one factory is good for SSOT
            return
        
        # Test that all factories return instances of the same class
        tracker_instances = []
        
        for factory_name, factory_func in factory_functions:
            try:
                instance = factory_func()
                tracker_instances.append((factory_name, instance, type(instance)))
            except Exception as e:
                self.fail(f"Factory function {factory_name} failed: {e}")
        
        # CRITICAL ASSERTION: All instances should be of the same type (SSOT)
        if len(tracker_instances) > 1:
            base_type = tracker_instances[0][2]
            for factory_name, instance, instance_type in tracker_instances[1:]:
                self.assertEqual(
                    instance_type, base_type,
                    f"SSOT VIOLATION: Factory {factory_name} returns {instance_type}, "
                    f"but base factory returns {base_type}. "
                    f"All ExecutionTracker factories should return the same type."
                )
    
    def test_execution_tracker_import_paths_consistency(self):
        """
        Test that ExecutionTracker can be imported from expected SSOT locations.
        
        After SSOT consolidation, there should be a clear primary import path
        with compatibility aliases for backward compatibility.
        """
        # Expected primary import path (after SSOT consolidation)
        primary_imports = [
            ("netra_backend.app.core.agent_execution_tracker", "AgentExecutionTracker"),
            ("netra_backend.app.core.agent_execution_tracker", "ExecutionTracker"),  # Alias
        ]
        
        # Legacy import paths (should work for backward compatibility)
        legacy_imports = [
            ("netra_backend.app.core.execution_tracker", "ExecutionTracker"),
        ]
        
        # Test primary imports
        primary_classes = []
        for module_path, class_name in primary_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                primary_classes.append((f"{module_path}.{class_name}", cls))
            except (ImportError, AttributeError) as e:
                self.fail(f"Primary import failed: {module_path}.{class_name} - {e}")
        
        # Test legacy imports (optional for backward compatibility)
        legacy_classes = []
        for module_path, class_name in legacy_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                legacy_classes.append((f"{module_path}.{class_name}", cls))
            except (ImportError, AttributeError):
                # Legacy imports might not exist after consolidation - that's ok
                pass
        
        # If legacy imports exist, they should point to the same class as primary
        if primary_classes and legacy_classes:
            primary_class = primary_classes[0][1]
            for legacy_path, legacy_class in legacy_classes:
                self.assertIs(
                    legacy_class, primary_class,
                    f"Legacy import {legacy_path} should reference same class as primary import "
                    f"for backward compatibility"
                )
    
    async def test_execution_tracker_functionality_consistency(self):
        """
        Test that all ExecutionTracker implementations provide consistent functionality.
        
        This test validates that key execution tracking operations work consistently
        across all implementations.
        """
        # Get available tracker implementations
        trackers_to_test = []
        
        try:
            from netra_backend.app.core.execution_tracker import get_execution_tracker
            tracker = get_execution_tracker()
            trackers_to_test.append(("core_tracker", tracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker as get_agent_tracker
            tracker = get_agent_tracker()
            trackers_to_test.append(("agent_tracker", tracker))
        except ImportError:
            pass
        
        # Test basic functionality on each tracker
        for tracker_name, tracker in trackers_to_test:
            # Test execution creation
            if hasattr(tracker, 'create_execution'):
                exec_id = tracker.create_execution(
                    agent_name="test_agent",
                    thread_id="test-thread",
                    user_id="test-user"
                )
                self.assertIsNotNone(exec_id, f"{tracker_name}: create_execution should return execution ID")
                
                # Test execution retrieval
                if hasattr(tracker, 'get_execution'):
                    execution = tracker.get_execution(exec_id)
                    self.assertIsNotNone(execution, f"{tracker_name}: should be able to retrieve created execution")
            
            # Test metrics functionality
            if hasattr(tracker, 'get_metrics'):
                metrics = tracker.get_metrics()
                self.assertIsInstance(metrics, dict, f"{tracker_name}: get_metrics should return dict")
                
                # Common metric fields
                expected_metric_fields = ['total_executions', 'active_executions']
                for field in expected_metric_fields:
                    if field not in metrics:
                        print(f"Warning: {tracker_name} metrics missing field: {field}")
    
    def test_execution_state_consistency_across_trackers(self):
        """
        Test that ExecutionState enums are consistent across all tracker implementations.
        
        This test ensures that all ExecutionTracker implementations use the same
        ExecutionState enum, preventing state synchronization issues.
        """
        execution_states = []
        
        # Collect ExecutionState from each tracker module
        try:
            from netra_backend.app.core.execution_tracker import ExecutionState as CoreState
            execution_states.append(("core.execution_tracker", CoreState))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentState
            execution_states.append(("core.agent_execution_tracker", AgentState))
        except ImportError:
            pass
        
        try:
            # Check if orchestration tracker has its own ExecutionState
            from netra_backend.app.agents.execution_tracking.registry import ExecutionState as OrchState
            execution_states.append(("agents.execution_tracking.registry", OrchState))
        except ImportError:
            pass
        
        if len(execution_states) <= 1:
            # Only one ExecutionState is good for SSOT
            return
        
        # CRITICAL ASSERTION: All ExecutionState enums should be the same
        base_enum = execution_states[0][1]
        base_values = set(state.value for state in base_enum)
        
        for module_name, execution_state_enum in execution_states[1:]:
            current_values = set(state.value for state in execution_state_enum)
            
            # Values should be identical
            self.assertEqual(
                base_values, current_values,
                f"SSOT VIOLATION: ExecutionState from {module_name} has different values: "
                f"{current_values} vs base: {base_values}"
            )
            
            # Preferably should be the same enum class
            if execution_state_enum is not base_enum:
                print(f"Warning: ExecutionState from {module_name} is different enum class than base")


@pytest.mark.unit
@pytest.mark.ssot_validation
class TestExecutionTrackerConsolidationReadiness:
    """Test readiness for ExecutionTracker consolidation."""
    
    def test_execution_tracker_dependency_mapping(self):
        """
        Test and map all dependencies on ExecutionTracker implementations.
        
        This test identifies which modules depend on which ExecutionTracker
        implementations to plan consolidation strategy.
        """
        # This test would normally scan import statements across the codebase
        # For now, we test known dependency patterns
        
        dependency_tests = [
            # (importing_module, imported_class, expected_to_work)
            ("netra_backend.app.agents.supervisor.agent_execution_core", "get_execution_tracker", True),
            ("netra_backend.app.core.agent_execution_tracker", "AgentExecutionTracker", True),
            ("netra_backend.app.core.execution_tracker", "ExecutionTracker", True),
        ]
        
        working_dependencies = []
        broken_dependencies = []
        
        for module_path, class_name, expected in dependency_tests:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                working_dependencies.append((module_path, class_name))
            except (ImportError, AttributeError):
                broken_dependencies.append((module_path, class_name))
        
        # Log dependency status for consolidation planning
        if working_dependencies:
            print(f"Working ExecutionTracker dependencies: {working_dependencies}")
        if broken_dependencies:
            print(f"Broken ExecutionTracker dependencies: {broken_dependencies}")
        
        # After consolidation, all expected dependencies should work
        # For now, we just ensure we can identify the current state
        assert len(working_dependencies) > 0, "Should have at least some working ExecutionTracker dependencies"
    
    def test_execution_tracker_interface_requirements(self):
        """
        Test that ExecutionTracker implementations meet interface requirements.
        
        This test defines the minimum interface requirements that any
        consolidated ExecutionTracker implementation must provide.
        """
        # Minimum required interface for ExecutionTracker SSOT
        required_methods = [
            'create_execution',
            'get_execution', 
            'update_execution_state',
            'get_active_executions',
            'get_metrics'
        ]
        
        optional_methods = [
            'start_monitoring',
            'stop_monitoring',
            'heartbeat',
            'complete_execution'
        ]
        
        # Test against available implementations
        tracker_classes = []
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            tracker_classes.append(("AgentExecutionTracker", AgentExecutionTracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.execution_tracker import ExecutionTracker
            tracker_classes.append(("ExecutionTracker", ExecutionTracker))
        except ImportError:
            pass
        
        for class_name, tracker_class in tracker_classes:
            # Check required methods
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(tracker_class, method_name),
                    f"{class_name} missing required method: {method_name}"
                )
            
            # Check optional methods (log warnings only)
            for method_name in optional_methods:
                if not hasattr(tracker_class, method_name):
                    print(f"Note: {class_name} missing optional method: {method_name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])