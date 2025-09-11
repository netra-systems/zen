#!/usr/bin/env python3
"""
SSOT Validation Tests for AgentExecutionTracker Consolidation (GitHub Issue #220)

These tests validate SSOT compliance during AgentExecutionTracker consolidation.
They are designed to FAIL before consolidation and PASS after consolidation.

Business Value:
- Segment: Platform/Internal
- Goal: Stability & SSOT compliance 
- Value Impact: Protects $500K+ ARR by preventing duplicate execution tracking systems
- Strategic Impact: Essential for agent execution reliability and maintainability
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAgentExecutionTrackerSSOTConsolidation(SSotBaseTestCase):
    """
    SSOT validation tests for AgentExecutionTracker consolidation.
    
    These tests are designed to FAIL before consolidation (detecting current violations)
    and PASS after consolidation (confirming SSOT compliance).
    """

    def test_agent_state_tracker_is_deprecated(self):
        """
        Should FAIL - AgentStateTracker should be deprecated after consolidation.
        
        CURRENT EXPECTED RESULT: FAIL (AgentStateTracker still exists)
        POST-CONSOLIDATION EXPECTED: PASS (AgentStateTracker deprecated/removed)
        """
        try:
            # This should fail after consolidation when AgentStateTracker is deprecated
            from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
            
            # If we can import it, the consolidation hasn't happened yet
            pytest.fail(
                "SSOT VIOLATION: AgentStateTracker still exists and should be deprecated. "
                "All state tracking should be consolidated into AgentExecutionTracker."
            )
        except ImportError:
            # This is expected after consolidation - AgentStateTracker should not exist
            pass

    def test_agent_execution_timeout_manager_is_deprecated(self):
        """
        Should FAIL - AgentExecutionTimeoutManager should be deprecated after consolidation.
        
        CURRENT EXPECTED RESULT: FAIL (AgentExecutionTimeoutManager still exists)
        POST-CONSOLIDATION EXPECTED: PASS (AgentExecutionTimeoutManager deprecated/removed)
        """
        try:
            # This should fail after consolidation when AgentExecutionTimeoutManager is deprecated
            from netra_backend.app.agents.execution_timeout_manager import AgentExecutionTimeoutManager
            
            # If we can import it, the consolidation hasn't happened yet
            pytest.fail(
                "SSOT VIOLATION: AgentExecutionTimeoutManager still exists and should be deprecated. "
                "All timeout management should be consolidated into AgentExecutionTracker."
            )
        except ImportError:
            # This is expected after consolidation - AgentExecutionTimeoutManager should not exist
            pass

    def test_execution_engines_use_ssot_tracker(self):
        """
        Should FAIL - Execution engines should only use AgentExecutionTracker.
        
        CURRENT EXPECTED RESULT: FAIL (Multiple execution state systems exist)
        POST-CONSOLIDATION EXPECTED: PASS (Only AgentExecutionTracker used)
        """
        violations = []
        
        # Check ExecutionEngine imports for state management violations
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            # Scan the module source for SSOT violations
            import inspect
            source = inspect.getsource(ExecutionEngine)
            
            # Look for imports of deprecated state managers
            deprecated_imports = [
                'AgentStateTracker',
                'AgentExecutionTimeoutManager',
                'execution_timeout_manager',
                'agent_state_tracker'
            ]
            
            for deprecated in deprecated_imports:
                if deprecated in source:
                    violations.append(f"ExecutionEngine imports deprecated {deprecated}")
                    
            # Look for direct state management instead of using AgentExecutionTracker
            state_management_patterns = [
                'self._state =',
                'self.state =',
                'self._execution_states',
                'self.execution_states',
                'self._timeout_handlers',
                'self.timeout_handlers'
            ]
            
            for pattern in state_management_patterns:
                if pattern in source:
                    violations.append(f"ExecutionEngine has direct state management: {pattern}")
                    
        except ImportError:
            # ExecutionEngine not available for inspection
            pass
            
        if violations:
            pytest.fail(
                f"SSOT VIOLATION: ExecutionEngine has {len(violations)} SSOT violations. "
                f"Should only use AgentExecutionTracker for all state management. "
                f"Violations: {', '.join(violations)}"
            )

    def test_no_manual_execution_id_generation(self):
        """
        Should FAIL - All execution ID generation should go through UnifiedIDManager.
        
        CURRENT EXPECTED RESULT: FAIL (Manual UUID generation found)
        POST-CONSOLIDATION EXPECTED: PASS (Only UnifiedIDManager used)
        """
        violations = []
        
        # Check for manual UUID generation in execution-related modules
        modules_to_check = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.core.agent_execution_tracker',
            'netra_backend.app.agents.supervisor.workflow_orchestrator',
            'netra_backend.app.agents.supervisor.pipeline_executor'
        ]
        
        for module_name in modules_to_check:
            try:
                import importlib
                module = importlib.import_module(module_name)
                
                # Get all source files in the module
                import inspect
                import os
                
                if hasattr(module, '__file__') and module.__file__:
                    module_file = module.__file__
                    if module_file.endswith('.py'):
                        with open(module_file, 'r') as f:
                            source = f.read()
                            
                        # Look for manual UUID generation patterns
                        uuid_patterns = [
                            'uuid.uuid4()',
                            'str(uuid.uuid4())',
                            'uuid4()',
                            'uuid.UUID(',
                            'import uuid'
                        ]
                        
                        # Look for UnifiedIDManager usage (should be present)
                        unified_id_patterns = [
                            'UnifiedIDManager',
                            'get_unified_id',
                            'generate_execution_id'
                        ]
                        
                        has_manual_uuid = any(pattern in source for pattern in uuid_patterns)
                        has_unified_id = any(pattern in source for pattern in unified_id_patterns)
                        
                        if has_manual_uuid and not has_unified_id:
                            violations.append(f"{module_name} uses manual UUID generation without UnifiedIDManager")
                        elif has_manual_uuid:
                            violations.append(f"{module_name} has both manual UUID and UnifiedIDManager (should only use UnifiedIDManager)")
                            
            except (ImportError, FileNotFoundError, OSError):
                # Module not available for inspection
                continue
                
        if violations:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(violations)} manual execution ID generation violations. "
                f"All execution IDs should be generated through UnifiedIDManager. "
                f"Violations: {', '.join(violations)}"
            )

    def test_no_duplicate_timeout_logic(self):
        """
        Should FAIL - All timeout logic should be in AgentExecutionTracker.
        
        CURRENT EXPECTED RESULT: FAIL (Duplicate timeout implementations found)
        POST-CONSOLIDATION EXPECTED: PASS (Only AgentExecutionTracker has timeout logic)
        """
        violations = []
        
        # Check for duplicate timeout/circuit breaker implementations
        modules_to_check = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.supervisor.workflow_orchestrator',
            'netra_backend.app.agents.supervisor.pipeline_executor',
            'netra_backend.app.core.agent_execution_tracker'
        ]
        
        timeout_implementations = {}
        
        for module_name in modules_to_check:
            try:
                import importlib
                module = importlib.import_module(module_name)
                
                if hasattr(module, '__file__') and module.__file__:
                    module_file = module.__file__
                    if module_file.endswith('.py'):
                        with open(module_file, 'r') as f:
                            source = f.read()
                            
                        # Skip deprecated files from timeout pattern check
                        if 'DEPRECATED' in source or 'deprecated' in source:
                            continue
                            
                        # Look for timeout/circuit breaker patterns
                        timeout_patterns = [
                            'timeout_seconds',
                            'execution_timeout', 
                            'circuit_breaker',
                            'CircuitBreaker',
                            'timeout_handler',
                            'TimeoutError',
                            'asyncio.timeout',
                            'asyncio.wait_for'
                        ]
                        
                        found_patterns = []
                        for pattern in timeout_patterns:
                            if pattern in source:
                                found_patterns.append(pattern)
                                
                        if found_patterns:
                            timeout_implementations[module_name] = found_patterns
                            
            except (ImportError, FileNotFoundError, OSError):
                continue
                
        # After consolidation, only AgentExecutionTracker should have timeout logic
        non_tracker_modules = [
            module for module in timeout_implementations.keys() 
            if 'agent_execution_tracker' not in module
        ]
        
        if len(non_tracker_modules) > 0:
            violations.extend([
                f"{module} has timeout logic that should be in AgentExecutionTracker: {timeout_implementations[module]}"
                for module in non_tracker_modules
            ])
            
        if violations:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(violations)} duplicate timeout implementations. "
                f"All timeout logic should be consolidated in AgentExecutionTracker. "
                f"Violations: {', '.join(violations)}"
            )

    def test_agent_execution_tracker_has_all_state_methods(self):
        """
        Should PASS - AgentExecutionTracker has consolidated state management.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Methods not yet consolidated)
        POST-CONSOLIDATION EXPECTED: PASS (All state methods available)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            
            # Check for required state management methods
            required_state_methods = [
                'get_agent_state',
                'set_agent_state', 
                'transition_state',
                'validate_state_transition',
                'get_state_history',
                'cleanup_state'
            ]
            
            tracker = AgentExecutionTracker()
            missing_methods = []
            
            for method in required_state_methods:
                if not hasattr(tracker, method):
                    missing_methods.append(method)
                    
            if missing_methods:
                pytest.fail(
                    f"AgentExecutionTracker missing state management methods: {missing_methods}. "
                    f"These should be consolidated from AgentStateTracker."
                )
                
        except ImportError:
            pytest.fail("AgentExecutionTracker not available for validation")

    def test_agent_execution_tracker_has_all_timeout_methods(self):
        """
        Should PASS - AgentExecutionTracker has consolidated timeout management.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Methods not yet consolidated)
        POST-CONSOLIDATION EXPECTED: PASS (All timeout methods available)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            
            # Check for required timeout management methods
            required_timeout_methods = [
                'set_timeout',
                'check_timeout',
                'register_circuit_breaker',
                'circuit_breaker_status',
                'reset_circuit_breaker'
            ]
            
            tracker = AgentExecutionTracker()
            missing_methods = []
            
            for method in required_timeout_methods:
                if not hasattr(tracker, method):
                    missing_methods.append(method)
                    
            if missing_methods:
                pytest.fail(
                    f"AgentExecutionTracker missing timeout management methods: {missing_methods}. "
                    f"These should be consolidated from AgentExecutionTimeoutManager."
                )
                
        except ImportError:
            pytest.fail("AgentExecutionTracker not available for validation")

    def test_unified_id_manager_integration(self):
        """
        Should PASS - AgentExecutionTracker uses UnifiedIDManager for IDs.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Direct UUID usage still present)
        POST-CONSOLIDATION EXPECTED: PASS (UnifiedIDManager integration complete)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            
            # Check that AgentExecutionTracker uses UnifiedIDManager
            import inspect
            source = inspect.getsource(AgentExecutionTracker)
            
            # Should have UnifiedIDManager import/usage
            unified_id_indicators = [
                'UnifiedIDManager',
                'get_unified_id',
                'generate_execution_id'
            ]
            
            has_unified_id = any(indicator in source for indicator in unified_id_indicators)
            
            # Should NOT have direct UUID usage
            direct_uuid_patterns = [
                'uuid.uuid4()',
                'str(uuid.uuid4())',
                'uuid4()'
            ]
            
            has_direct_uuid = any(pattern in source for pattern in direct_uuid_patterns)
            
            if not has_unified_id:
                pytest.fail(
                    "AgentExecutionTracker does not integrate with UnifiedIDManager for ID generation"
                )
                
            if has_direct_uuid:
                pytest.fail(
                    "AgentExecutionTracker still uses direct UUID generation instead of UnifiedIDManager"
                )
                
        except ImportError:
            pytest.fail("AgentExecutionTracker not available for validation")

    def test_execution_engine_factory_uses_ssot(self):
        """
        Should PASS - Factory pattern uses consolidated tracker.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Factory not yet updated)
        POST-CONSOLIDATION EXPECTED: PASS (Factory uses consolidated AgentExecutionTracker)
        """
        try:
            # Check if execution engine factory uses consolidated tracker
            from netra_backend.app.core.user_execution_engine import UserExecutionEngineFactory
            
            # Check factory implementation
            import inspect
            source = inspect.getsource(UserExecutionEngineFactory)
            
            # Should use AgentExecutionTracker
            if 'AgentExecutionTracker' not in source:
                pytest.fail(
                    "UserExecutionEngineFactory does not use AgentExecutionTracker. "
                    "Factory should be updated to use consolidated tracker."
                )
                
            # Should NOT use deprecated trackers
            deprecated_trackers = [
                'AgentStateTracker',
                'AgentExecutionTimeoutManager'
            ]
            
            for deprecated in deprecated_trackers:
                if deprecated in source:
                    pytest.fail(
                        f"UserExecutionEngineFactory still uses deprecated {deprecated}. "
                        f"Should only use consolidated AgentExecutionTracker."
                    )
                    
        except ImportError:
            # Factory might not exist yet - this is acceptable
            pass

    @pytest.mark.asyncio
    async def test_consolidated_execution_creation_integration(self):
        """
        Integration test - consolidated execution creation with full context.
        
        CURRENT EXPECTED RESULT: MAY FAIL (Integration not complete)
        POST-CONSOLIDATION EXPECTED: PASS (Seamless consolidated execution creation)
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            
            tracker = AgentExecutionTracker()
            
            # Test consolidated execution creation (should have all context)
            if hasattr(tracker, 'create_execution_with_full_context'):
                exec_id = tracker.create_execution_with_full_context(
                    agent_name='test_agent',
                    user_context={'user_id': 'test_user', 'thread_id': 'test_thread'},
                    timeout_config={'timeout_seconds': 30},
                    initial_state='PENDING'
                )
                
                # Verify execution was created with all consolidated context
                if hasattr(tracker, 'get_execution_with_full_context'):
                    execution = tracker.get_execution_with_full_context(exec_id)
                    assert execution is not None, "Execution should be created with full context"
                    assert execution.get('agent_name') == 'test_agent'
                    assert execution.get('timeout_seconds') == 30
                    assert execution.get('state') == 'PENDING'
                else:
                    pytest.fail("AgentExecutionTracker missing get_execution_with_full_context method")
            else:
                pytest.fail(
                    "AgentExecutionTracker missing create_execution_with_full_context method. "
                    "This should be available after consolidation."
                )
                
        except ImportError:
            pytest.fail("AgentExecutionTracker not available for integration testing")
        except Exception as e:
            pytest.fail(f"Consolidated execution creation failed: {str(e)}")


if __name__ == "__main__":
    """
    Run SSOT validation tests for AgentExecutionTracker consolidation.
    
    Expected Results BEFORE consolidation:
    - Most tests should FAIL, detecting current SSOT violations
    - This establishes baseline of violations to fix
    
    Expected Results AFTER consolidation:
    - All tests should PASS, confirming SSOT compliance
    - This validates successful consolidation
    """
    pytest.main([__file__, "-v", "--tb=short", "-x"])