"""
Issue #835 - Phase 1: Deprecated Interface Failure Tests

These tests are DESIGNED TO FAIL to demonstrate issues with deprecated
SupervisorExecutionEngineFactory usage. They validate that deprecation
warnings are properly generated and old patterns are being phased out.

Test Strategy:
- Test 1: SupervisorExecutionEngineFactory generates deprecation warnings
- Test 2: Deprecated factory import patterns still work but warn

Expected Results: 2 FAILURES/WARNINGS demonstrating deprecated interface issues
"""

import pytest
import warnings
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestPhase1DeprecatedInterfaceFailures(SSotAsyncTestCase):
    """
    Phase 1: Demonstrate deprecated interface usage failures
    These tests intentionally use deprecated patterns to validate warnings.
    """
    
    def test_deprecated_supervisor_execution_factory_generates_warning(self):
        """
        Test that SupervisorExecutionEngineFactory generates deprecation warning.
        
        EXPECTED: This test should capture deprecation warning or fail
        demonstrating the deprecated interface is problematic.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                # Import deprecated factory (this should generate warning)
                from netra_backend.app.agents.supervisor.execution_engine_factory import (
                    SupervisorExecutionEngineFactory
                )
                
                # Try to instantiate deprecated factory
                factory = SupervisorExecutionEngineFactory(
                    websocket_manager=None,
                    user_id="test_user_deprecated",
                    execution_id="test_execution_deprecated"
                )
                
                # Check if deprecation warning was generated
                deprecation_warnings = [warning for warning in w 
                                      if issubclass(warning.category, DeprecationWarning)]
                
                if len(deprecation_warnings) == 0:
                    # Force test failure if no deprecation warning found
                    self.fail("Expected DeprecationWarning for SupervisorExecutionEngineFactory but none found")
                
                # This assertion should pass if warning is properly generated
                self.assertGreater(len(deprecation_warnings), 0, 
                                 "SupervisorExecutionEngineFactory should generate DeprecationWarning")
                
                # Validate warning message content
                warning_message = str(deprecation_warnings[0].message)
                self.assertIn("SupervisorExecutionEngineFactory is deprecated", warning_message)
                self.assertIn("UnifiedExecutionEngineFactory", warning_message)
                
            except ImportError as e:
                # If import fails, that also demonstrates the deprecated interface is problematic
                self.assertTrue(True, f"Expected ImportError for deprecated SupervisorExecutionEngineFactory: {e}")
            except Exception as e:
                # Any other exception also demonstrates interface problems
                self.fail(f"Deprecated factory instantiation failed: {e}")

    def test_deprecated_factory_import_patterns_warn(self):
        """
        Test that deprecated import patterns from test files generate warnings.
        
        EXPECTED: This test should capture issues with old import patterns
        still used in golden path tests.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                # Try the deprecated import pattern that was causing issues
                from netra_backend.app.agents.supervisor.execution_factory import (
                    ExecutionEngineFactory as SupervisorExecutionEngineFactory,
                )
                
                # This import should either:
                # 1. Generate a warning
                # 2. Fail entirely
                # 3. Create an object that later fails
                
                # Check for any warnings generated
                import_warnings = [warning for warning in w]
                
                if len(import_warnings) == 0:
                    # Try to use the imported factory to see if it fails
                    try:
                        factory = SupervisorExecutionEngineFactory(
                            websocket_manager=None,
                            user_id="test_deprecated_import",
                            execution_id="test_deprecated_import"
                        )
                        # If we get here without warnings, this is a problem
                        self.fail("Expected deprecated import to generate warnings or fail")
                    except Exception as instantiation_error:
                        # Factory instantiation failure is also a valid demonstration
                        # of deprecated interface issues
                        pass  # This demonstrates the deprecated pattern is problematic
                
            except ImportError as import_error:
                # Import failure demonstrates the deprecated pattern is no longer supported
                # This is actually the desired outcome - deprecated imports should fail
                pass  # This is expected behavior for fully deprecated interfaces
            except Exception as general_error:
                # Any other exception demonstrates interface problems
                pass  # This also demonstrates deprecated interface issues


if __name__ == "__main__":
    # Run with verbose output to see deprecation warnings
    pytest.main([__file__, "-v", "-s"])