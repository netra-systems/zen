"""
Targeted test for agent_execution_core import validation bug reproduction (FIXED VERSION).

PURPOSE: Reproduce the specific `get_agent_state_tracker` import error identified in issue #276.

EXPECTED BEHAVIOR:
- Test should FAIL with ImportError or AttributeError
- Demonstrates that agent_execution_core module is missing the expected function
- Shows the exact import path that is broken

BUG TO REPRODUCE:
- Code tries to import `get_agent_state_tracker` from `netra_backend.app.agents.supervisor.agent_execution_core`
- This function/factory doesn't exist in the module
- Results in ImportError when agent execution code tries to access state tracking
"""

import pytest
from unittest.mock import Mock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAgentExecutionCoreImportValidation(SSotBaseTestCase):
    """Test to reproduce the agent_execution_core import validation bug."""
    
    def test_get_agent_state_tracker_import_should_fail(self):
        """
        Test that reproduces the missing get_agent_state_tracker import bug.
        
        EXPECTED RESULT: This test should FAIL with ImportError or AttributeError.
        This demonstrates the missing function that code is trying to import.
        """
        # BUG REPRODUCTION: Try to import the function that should exist but doesn't
        with self.expect_exception((ImportError, AttributeError), "get_agent_state_tracker"):
            from netra_backend.app.agents.supervisor.agent_execution_core import get_agent_state_tracker
            
            # If we reach here without exception, try to call it to see if it exists
            try:
                tracker = get_agent_state_tracker()
                assert False, (
                    "UNEXPECTED: get_agent_state_tracker was imported successfully. "
                    "This suggests the import issue may have been fixed or the "
                    "function exists but has other problems."
                )
            except Exception as e:
                # Expected - function doesn't work properly
                self.record_metric("function_call_error", str(e))
                raise
    
    def test_available_imports_in_agent_execution_core(self):
        """
        Test what imports are actually available in agent_execution_core module.
        
        This helps identify what exists vs what's missing.
        """
        try:
            import netra_backend.app.agents.supervisor.agent_execution_core as core_module
            
            # Get all available attributes in the module
            available_attributes = [attr for attr in dir(core_module) if not attr.startswith('_')]
            
            self.record_metric("available_attributes_count", len(available_attributes))
            self.record_metric("available_attributes", available_attributes)
            
            # Check for expected imports that should exist
            expected_functions = [
                'get_agent_state_tracker',
                'AgentExecutionCore',
                'get_execution_tracker',
                'create_agent_execution_context'
            ]
            
            missing_functions = []
            for func_name in expected_functions:
                if not hasattr(core_module, func_name):
                    missing_functions.append(func_name)
            
            if missing_functions:
                assert False, (
                    f"BUG REPRODUCED: agent_execution_core module is missing expected functions: {missing_functions}. "
                    f"Available attributes: {available_attributes}. "
                    "This causes ImportError when other modules try to import these functions."
                )
                
        except ImportError as e:
            assert False, f"CRITICAL: Cannot import agent_execution_core module at all: {e}"
    
    def test_import_path_consistency_check(self):
        """
        Test import path consistency across related modules.
        
        This checks if there are inconsistencies in how modules reference each other.
        """
        # Map of expected imports and where they should come from
        import_expectations = {
            'get_execution_tracker': 'netra_backend.app.core.agent_execution_tracker',
            'ExecutionState': 'netra_backend.app.core.agent_execution_tracker', 
            'AgentExecutionCore': 'netra_backend.app.agents.supervisor.agent_execution_core',
            'get_agent_state_tracker': 'netra_backend.app.agents.supervisor.agent_execution_core'  # This should fail
        }
        
        import_results = {}
        
        for import_name, expected_module in import_expectations.items():
            try:
                module = __import__(expected_module, fromlist=[import_name])
                if hasattr(module, import_name):
                    import_results[import_name] = "AVAILABLE"
                else:
                    import_results[import_name] = "NOT_FOUND_IN_MODULE"
            except ImportError:
                import_results[import_name] = "MODULE_IMPORT_ERROR"
        
        self.record_metric("import_results", import_results)
        
        # Check for the specific bug
        if import_results.get('get_agent_state_tracker') == "NOT_FOUND_IN_MODULE":
            assert False, (
                "BUG REPRODUCED: get_agent_state_tracker is expected to be in "
                "netra_backend.app.agents.supervisor.agent_execution_core but is not found. "
                f"Full import results: {import_results}"
            )
        elif import_results.get('get_agent_state_tracker') == "MODULE_IMPORT_ERROR":
            assert False, (
                "BUG REPRODUCED: Cannot import agent_execution_core module that should contain get_agent_state_tracker. "
                f"Full import results: {import_results}"
            )


if __name__ == "__main__":
    # Run this test to reproduce the import validation bug
    pytest.main([__file__, "-v", "-s"])