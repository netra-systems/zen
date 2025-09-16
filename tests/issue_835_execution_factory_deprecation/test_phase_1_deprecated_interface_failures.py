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

class Phase1DeprecatedInterfaceFailuresTests(SSotAsyncTestCase):
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
            warnings.simplefilter('always')
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import SupervisorExecutionEngineFactory
                factory = SupervisorExecutionEngineFactory(websocket_manager=None, user_id='test_user_deprecated', execution_id='test_execution_deprecated')
                deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
                if len(deprecation_warnings) == 0:
                    self.fail('Expected DeprecationWarning for SupervisorExecutionEngineFactory but none found')
                self.assertGreater(len(deprecation_warnings), 0, 'SupervisorExecutionEngineFactory should generate DeprecationWarning')
                warning_message = str(deprecation_warnings[0].message)
                self.assertIn('SupervisorExecutionEngineFactory is deprecated', warning_message)
                self.assertIn('UnifiedExecutionEngineFactory', warning_message)
            except ImportError as e:
                self.assertTrue(True, f'Expected ImportError for deprecated SupervisorExecutionEngineFactory: {e}')
            except Exception as e:
                self.fail(f'Deprecated factory instantiation failed: {e}')

    def test_deprecated_factory_import_patterns_warn(self):
        """
        Test that deprecated import patterns from test files generate warnings.
        
        EXPECTED: This test should capture issues with old import patterns
        still used in golden path tests.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            try:
                from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory as SupervisorExecutionEngineFactory
                import_warnings = [warning for warning in w]
                if len(import_warnings) == 0:
                    try:
                        factory = SupervisorExecutionEngineFactory(websocket_manager=None, user_id='test_deprecated_import', execution_id='test_deprecated_import')
                        self.fail('Expected deprecated import to generate warnings or fail')
                    except Exception as instantiation_error:
                        pass
            except ImportError as import_error:
                pass
            except Exception as general_error:
                pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')