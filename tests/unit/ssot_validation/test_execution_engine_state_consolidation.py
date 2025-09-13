#!/usr/bin/env python3
"""
Execution Engine State Consolidation Tests for AgentExecutionTracker SSOT

This test validates that all execution engines use AgentExecutionTracker 
as the single source of truth for execution state, eliminating duplicate
state management systems.

Business Value:
- Segment: Platform/Internal  
- Goal: Stability & State Consistency
- Value Impact: Prevents state corruption and race conditions in $500K+ ARR chat
- Strategic Impact: Essential for reliable multi-user agent execution
"""

import pytest
import importlib
import inspect
import ast
from typing import Dict, List, Any, Set, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestExecutionEngineStateConsolidation(SSotBaseTestCase):
    """
    Test that all execution engines use consolidated state management.
    
    These tests detect multiple execution state systems (SSOT violations)
    and validate consolidation to AgentExecutionTracker.
    """

    def test_multiple_execution_engines_detected(self):
        """
        Should FAIL - Detects multiple execution engine implementations.
        
        CURRENT EXPECTED RESULT: FAIL (Multiple execution engines exist)
        POST-CONSOLIDATION EXPECTED: PASS (Single consolidated execution engine)
        """
        execution_engines = []
        
        # Known execution engine modules to check
        engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated', 
            'netra_backend.app.core.execution_engine',
            'netra_backend.app.services.unified_tool_registry.execution_engine',
            'netra_backend.app.agents.execution_tracking.execution_engine',
            'netra_backend.app.core.user_execution_engine'
        ]
        
        for module_name in engine_modules:
            try:
                module = importlib.import_module(module_name)
                
                # Look for ExecutionEngine classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (inspect.isclass(attr) and 
                        'ExecutionEngine' in attr_name and 
                        attr.__module__ == module_name):
                        execution_engines.append(f"{module_name}.{attr_name}")
                        
            except ImportError:
                # Module doesn't exist - that's fine
                continue
                
        # After consolidation, should have only one primary execution engine
        if len(execution_engines) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(execution_engines)} execution engine implementations. "
                f"Should be consolidated to single AgentExecutionTracker-based engine. "
                f"Found: {', '.join(execution_engines)}"
            )

    def test_execution_engines_have_separate_state_storage(self):
        """
        Should FAIL - Execution engines should not maintain separate state.
        
        CURRENT EXPECTED RESULT: FAIL (Separate state storage detected)
        POST-CONSOLIDATION EXPECTED: PASS (Only AgentExecutionTracker stores state)
        """
        state_violations = []
        
        # Check execution engine implementations for state storage
        engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated',
            'netra_backend.app.services.unified_tool_registry.execution_engine'
        ]
        
        for module_name in engine_modules:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__file__') and module.__file__:
                    with open(module.__file__, 'r') as f:
                        source = f.read()
                        
                    # Look for state storage patterns (SSOT violations)
                    state_storage_patterns = [
                        'self._executions =',
                        'self.executions =',
                        'self._execution_state =',
                        'self.execution_state =',
                        'self._state_cache =',
                        'self.state_cache =',
                        'self._execution_registry =',
                        'self.execution_registry =',
                        '_execution_states =',
                        'execution_states =',
                        '_active_executions =',
                        'active_executions ='
                    ]
                    
                    for pattern in state_storage_patterns:
                        if pattern in source:
                            state_violations.append(f"{module_name}: {pattern}")
                            
            except (ImportError, FileNotFoundError, OSError):
                continue
                
        if state_violations:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(state_violations)} execution engines with separate state storage. "
                f"All state should be managed by AgentExecutionTracker. "
                f"Violations: {', '.join(state_violations)}"
            )

    def test_execution_engines_use_direct_state_management(self):
        """
        Should FAIL - Execution engines should delegate state to AgentExecutionTracker.
        
        CURRENT EXPECTED RESULT: FAIL (Direct state management found)
        POST-CONSOLIDATION EXPECTED: PASS (State delegated to AgentExecutionTracker)
        """
        direct_state_violations = []
        
        engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated'
        ]
        
        for module_name in engine_modules:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__file__') and module.__file__:
                    with open(module.__file__, 'r') as f:
                        source = f.read()
                        
                    # Look for direct state management (should be delegated)
                    direct_state_patterns = [
                        'def update_state(',
                        'def set_state(',
                        'def get_state(',
                        'def transition_state(',
                        'def manage_state(',
                        'state = ExecutionState.',
                        'execution.state =',
                        'self.state =',
                        'state_machine',
                        'StateManager(',
                        'create_state(',
                        'persist_state('
                    ]
                    
                    # Check if AgentExecutionTracker is used (should be present)
                    uses_agent_execution_tracker = (
                        'AgentExecutionTracker' in source or
                        'get_execution_tracker' in source
                    )
                    
                    found_direct_patterns = []
                    for pattern in direct_state_patterns:
                        if pattern in source:
                            found_direct_patterns.append(pattern)
                            
                    if found_direct_patterns and not uses_agent_execution_tracker:
                        direct_state_violations.append(
                            f"{module_name}: Direct state management without AgentExecutionTracker: {found_direct_patterns}"
                        )
                    elif found_direct_patterns:
                        # Has both - should be migrated to only use AgentExecutionTracker
                        direct_state_violations.append(
                            f"{module_name}: Mixed state management (should only use AgentExecutionTracker): {found_direct_patterns}"
                        )
                        
            except (ImportError, FileNotFoundError, OSError):
                continue
                
        if direct_state_violations:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(direct_state_violations)} execution engines with direct state management. "
                f"Should delegate all state operations to AgentExecutionTracker. "
                f"Violations: {direct_state_violations}"
            )

    def test_factory_patterns_use_consolidated_tracker(self):
        """
        Should PASS - Factory patterns should use consolidated AgentExecutionTracker.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Factory not updated)
        POST-CONSOLIDATION EXPECTED: PASS (Factory uses AgentExecutionTracker)
        """
        try:
            from netra_backend.app.core.user_execution_engine import UserExecutionEngineFactory
        except ImportError:
            self.skip("UserExecutionEngineFactory not available")
            
        # Check factory implementation
        source = inspect.getsource(UserExecutionEngineFactory)
        
        factory_violations = []
        
        # Should use AgentExecutionTracker
        if 'AgentExecutionTracker' not in source:
            factory_violations.append("Factory does not use AgentExecutionTracker")
            
        # Should not use deprecated state managers
        deprecated_managers = [
            'AgentStateTracker',
            'AgentExecutionTimeoutManager',
            'LegacyExecutionTracker'
        ]
        
        for deprecated in deprecated_managers:
            if deprecated in source:
                factory_violations.append(f"Factory uses deprecated {deprecated}")
                
        # Should not have its own state storage
        factory_state_patterns = [
            'self._state =',
            'self.state =',
            '_execution_cache =',
            'execution_cache ='
        ]
        
        for pattern in factory_state_patterns:
            if pattern in source:
                factory_violations.append(f"Factory has own state storage: {pattern}")
                
        if factory_violations:
            pytest.fail(
                f"Factory pattern SSOT violations: {', '.join(factory_violations)}"
            )

    def test_no_execution_state_duplication_across_engines(self):
        """
        Should FAIL - Multiple engines should not duplicate execution state.
        
        CURRENT EXPECTED RESULT: FAIL (State duplication exists)
        POST-CONSOLIDATION EXPECTED: PASS (No state duplication)
        """
        state_duplication_issues = []
        
        # Check for common execution state patterns across multiple engines
        engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated',
            'netra_backend.app.services.unified_tool_registry.execution_engine'
        ]
        
        # Common state management patterns that indicate duplication
        common_state_patterns = [
            'PENDING',
            'RUNNING', 
            'COMPLETED',
            'FAILED',
            'TIMEOUT',
            'ExecutionState',
            'execution_id',
            'start_time',
            'end_time',
            'status'
        ]
        
        modules_with_state = {}
        
        for module_name in engine_modules:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__file__') and module.__file__:
                    with open(module.__file__, 'r') as f:
                        source = f.read()
                        
                    found_patterns = []
                    for pattern in common_state_patterns:
                        if pattern in source:
                            found_patterns.append(pattern)
                            
                    if found_patterns:
                        modules_with_state[module_name] = found_patterns
                        
            except (ImportError, FileNotFoundError, OSError):
                continue
                
        # If multiple modules have overlapping state patterns, that's duplication
        if len(modules_with_state) > 1:
            overlap_analysis = {}
            modules = list(modules_with_state.keys())
            
            for i, module1 in enumerate(modules):
                for module2 in modules[i+1:]:
                    patterns1 = set(modules_with_state[module1])
                    patterns2 = set(modules_with_state[module2])
                    overlap = patterns1.intersection(patterns2)
                    
                    if len(overlap) > 3:  # Significant overlap
                        overlap_analysis[f"{module1} vs {module2}"] = list(overlap)
                        
            if overlap_analysis:
                state_duplication_issues = [
                    f"{modules}: {patterns}" 
                    for modules, patterns in overlap_analysis.items()
                ]
                
        if state_duplication_issues:
            pytest.fail(
                f"SSOT VIOLATION: Found execution state duplication across {len(state_duplication_issues)} module pairs. "
                f"All state should be in AgentExecutionTracker only. "
                f"Duplications: {'; '.join(state_duplication_issues)}"
            )

    def test_execution_engines_delegate_to_agent_execution_tracker(self):
        """
        Should PASS - Execution engines should delegate to AgentExecutionTracker.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Delegation not implemented)
        POST-CONSOLIDATION EXPECTED: PASS (Proper delegation to AgentExecutionTracker)
        """
        delegation_issues = []
        
        engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated'
        ]
        
        for module_name in engine_modules:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__file__') and module.__file__:
                    with open(module.__file__, 'r') as f:
                        source = f.read()
                        
                    # Should have AgentExecutionTracker delegation
                    delegation_patterns = [
                        'self.execution_tracker',
                        'get_execution_tracker',
                        'AgentExecutionTracker',
                        'tracker.create_execution',
                        'tracker.update_execution',
                        'tracker.get_execution'
                    ]
                    
                    has_delegation = any(pattern in source for pattern in delegation_patterns)
                    
                    if not has_delegation:
                        delegation_issues.append(f"{module_name} does not delegate to AgentExecutionTracker")
                        
                    # Should not have direct state operations
                    direct_operations = [
                        'self._execute_state =',
                        'self.execute_state =',
                        'execution.state =',
                        'state_dict[',
                        'self._states[',
                        'self.states['
                    ]
                    
                    found_direct = [op for op in direct_operations if op in source]
                    if found_direct:
                        delegation_issues.append(
                            f"{module_name} has direct state operations: {found_direct}"
                        )
                        
            except (ImportError, FileNotFoundError, OSError):
                continue
                
        if delegation_issues:
            pytest.fail(
                f"Execution engine delegation issues: {', '.join(delegation_issues)}"
            )

    @pytest.mark.asyncio
    async def test_consolidated_state_consistency_across_engines(self):
        """
        Test that all engines see consistent state through AgentExecutionTracker.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Inconsistent state across engines)
        POST-CONSOLIDATION EXPECTED: PASS (Consistent state via AgentExecutionTracker)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
        except ImportError:
            self.skip("AgentExecutionTracker not available for consistency testing")
            
        # Test that different engines see the same state
        tracker = AgentExecutionTracker()
        consistency_issues = []
        
        try:
            # Create an execution through the tracker
            if hasattr(tracker, 'create_execution'):
                exec_id = tracker.create_execution(
                    agent_name='consistency_test',
                    thread_id='test_thread',
                    user_id='test_user'
                )
                
                # Update state through tracker
                if hasattr(tracker, 'update_execution_state'):
                    tracker.update_execution_state(exec_id, 'RUNNING')
                    
                # Try to access from different engines (if they exist and delegate properly)
                engines_to_test = []
                
                try:
                    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
                    engines_to_test.append(('SupervisorExecutionEngine', ExecutionEngine))
                except ImportError:
                    pass
                    
                try:
                    from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine as ConsolidatedEngine
                    engines_to_test.append(('ConsolidatedExecutionEngine', ConsolidatedEngine))
                except ImportError:
                    pass
                    
                # Test state consistency across engines
                for engine_name, engine_class in engines_to_test:
                    try:
                        # If engine uses AgentExecutionTracker, it should see the same state
                        if hasattr(engine_class, 'get_execution_state'):
                            engine_instance = engine_class()
                            engine_state = engine_instance.get_execution_state(exec_id)
                            
                            tracker_state = tracker.get_execution(exec_id)
                            
                            if engine_state != tracker_state:
                                consistency_issues.append(
                                    f"{engine_name} sees different state than AgentExecutionTracker"
                                )
                                
                    except Exception as e:
                        consistency_issues.append(f"{engine_name} state access failed: {e}")
                        
        except Exception as e:
            consistency_issues.append(f"Consistency test setup failed: {e}")
            
        if consistency_issues:
            pytest.fail(
                f"State consistency issues across engines: {', '.join(consistency_issues)}"
            )

    def test_no_circular_dependencies_in_state_management(self):
        """
        Validate no circular dependencies in consolidated state management.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Circular dependencies exist)
        POST-CONSOLIDATION EXPECTED: PASS (Clean dependency structure)
        """
        circular_dependency_issues = []
        
        # Check for circular imports/dependencies
        modules_to_check = [
            'netra_backend.app.core.agent_execution_tracker',
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated'
        ]
        
        module_dependencies = {}
        
        for module_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__file__') and module.__file__:
                    with open(module.__file__, 'r') as f:
                        source = f.read()
                        
                    # Parse imports to detect dependencies
                    try:
                        tree = ast.parse(source)
                        imports = []
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports.append(alias.name)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports.append(node.module)
                                    
                        # Filter to only relevant modules
                        relevant_imports = [
                            imp for imp in imports 
                            if any(check_mod in imp for check_mod in modules_to_check)
                        ]
                        
                        module_dependencies[module_name] = relevant_imports
                        
                    except SyntaxError:
                        # Can't parse - skip this module
                        continue
                        
            except (ImportError, FileNotFoundError, OSError):
                continue
                
        # Check for circular dependencies
        for module, deps in module_dependencies.items():
            for dep in deps:
                if dep in module_dependencies:
                    if module in module_dependencies[dep]:
                        circular_dependency_issues.append(f"{module} <-> {dep}")
                        
        if circular_dependency_issues:
            pytest.fail(
                f"Circular dependency issues in state management: {', '.join(circular_dependency_issues)}"
            )


if __name__ == "__main__":
    """
    Run execution engine state consolidation validation tests.
    
    These tests detect SSOT violations where multiple execution engines
    maintain separate state instead of using AgentExecutionTracker.
    """
    pytest.main([__file__, "-v", "--tb=short", "-x"])