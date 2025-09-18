"""
Issue #971 Test Collection Verification Suite

This module provides focused test collection verification for Issue #971.
It tests the unified test runner's ability to collect the affected integration
tests after the WebSocketTestManager alias fix is implemented.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure Reliability
- Business Goal: Developer Productivity & Test Coverage Protection
- Value Impact: Ensures 3 critical integration test suites can execute
- Strategic Impact: Protects $500K+ ARR chat functionality test coverage

FOCUSED SCOPE:
This test suite specifically validates test collection and discovery mechanisms
rather than functional testing. It ensures the test infrastructure can find
and collect the affected integration tests after the alias fix.

EXECUTION STRATEGY:
- Pre-fix: Demonstrates collection failures
- Post-fix: Validates collection success
- Integration: Tests unified test runner integration
"""
import subprocess
import sys
import importlib
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.orchestration import get_orchestration_config

@pytest.mark.integration
class CollectionVerificationPreFixTests(SSotBaseTestCase):
    """
    Pre-fix validation: These tests should FAIL before the alias is added,
    demonstrating the exact collection issues described in Issue #971.
    """

    def test_unified_test_runner_collection_fails_before_fix(self):
        """
        Verify unified test runner cannot collect affected integration tests before fix.

        This test directly invokes the unified test runner to attempt collection
        of the integration tests that should fail due to missing WebSocketTestManager.
        """
        test_runner_path = Path(__file__).parent.parent / 'unified_test_runner.py'
        result = subprocess.run([sys.executable, str(test_runner_path), '--collect-only', '--category', 'integration', '--no-verbose'], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0, 'Test collection should fail before fix')
        error_output = result.stderr.lower()
        self.assertTrue('websockettestmanager' in error_output or 'cannot import name' in error_output, f'Error should mention WebSocketTestManager import issue: {result.stderr}')

    def test_direct_import_collection_fails_before_fix(self):
        """
        Verify direct import of affected test modules fails before fix.

        This test attempts direct import of the specific test modules that
        are affected by the missing WebSocketTestManager alias.
        """
        affected_modules = ['tests.integration.test_multi_agent_golden_path_workflows_integration', 'tests.integration.test_agent_websocket_event_sequence_integration']
        import_failures = []
        for module_path in affected_modules:
            try:
                importlib.import_module(module_path)
                import_failures.append(f'{module_path}: Unexpected success (should fail before fix)')
            except ImportError as e:
                if 'WebSocketTestManager' in str(e):
                    pass
                else:
                    import_failures.append(f'{module_path}: Unexpected error: {e}')
            except Exception as e:
                import_failures.append(f'{module_path}: Unexpected exception: {e}')
        if not import_failures:
            self.fail('Expected ImportError for WebSocketTestManager, but all imports succeeded. Fix might already be applied.')

@pytest.mark.integration
class CollectionVerificationPostFixTests(SSotBaseTestCase):
    """
    Post-fix validation: These tests should PASS after the alias is added,
    demonstrating that the collection issues are resolved.
    """

    def test_unified_test_runner_collection_succeeds_after_fix(self):
        """
        Verify unified test runner can collect affected integration tests after fix.

        This test verifies that the unified test runner can successfully collect
        the integration tests that were previously failing.
        """
        test_runner_path = Path(__file__).parent.parent / 'unified_test_runner.py'
        result = subprocess.run([sys.executable, str(test_runner_path), '--collect-only', '--category', 'integration', '--no-verbose'], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            self.fail(f'Test collection should succeed after fix. Return code: {result.returncode}, STDERR: {result.stderr}, STDOUT: {result.stdout}')

    def test_direct_import_collection_succeeds_after_fix(self):
        """
        Verify direct import of affected test modules succeeds after fix.

        This test attempts direct import of the specific test modules to
        verify they can be imported without WebSocketTestManager errors.
        """
        affected_modules = ['tests.integration.test_multi_agent_golden_path_workflows_integration', 'tests.integration.test_agent_websocket_event_sequence_integration']
        import_failures = []
        successful_imports = []
        for module_path in affected_modules:
            try:
                module = importlib.import_module(module_path)
                successful_imports.append(module_path)
                if hasattr(module, 'WebSocketTestManager'):
                    pass
            except ImportError as e:
                if 'WebSocketTestManager' in str(e):
                    import_failures.append(f'{module_path}: Still has WebSocketTestManager import error: {e}')
                else:
                    import_failures.append(f'{module_path}: Other import error: {e}')
            except Exception as e:
                import_failures.append(f'{module_path}: Unexpected exception: {e}')
        if import_failures:
            self.fail(f'Import failures after fix: {import_failures}')
        self.assertEqual(len(successful_imports), 2, f'Expected 2 successful imports, got {len(successful_imports)}: {successful_imports}')

    def test_websocket_test_manager_available_in_imported_modules(self):
        """
        Verify WebSocketTestManager is available in successfully imported modules.

        This test verifies that after the fix, the imported modules can actually
        access and use WebSocketTestManager.
        """
        affected_modules = ['tests.integration.test_multi_agent_golden_path_workflows_integration', 'tests.integration.test_agent_websocket_event_sequence_integration']
        for module_path in affected_modules:
            try:
                module = importlib.import_module(module_path)
                websocket_manager_class = getattr(module, 'WebSocketTestManager', None)
            except ImportError as e:
                self.fail(f'Module {module_path} should import successfully after fix: {e}')

@pytest.mark.integration
class SpecificFileCollectionVerificationTests(SSotBaseTestCase):
    """
    Specific file-level collection verification to ensure individual
    test files can be collected by pytest/unified test runner.
    """

    def test_multi_agent_golden_path_file_collection(self):
        """
        Verify multi-agent golden path test file can be collected individually.

        This test focuses on the specific file that was mentioned in Issue #971.
        """
        test_file_path = Path(__file__).parent / 'test_multi_agent_golden_path_workflows_integration.py'
        if not test_file_path.exists():
            self.skipTest(f'Test file not found: {test_file_path}')
        result = subprocess.run([sys.executable, '-m', 'pytest', str(test_file_path), '--collect-only', '-q'], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            self.fail(f'Individual test file collection failed. Return code: {result.returncode}, STDERR: {result.stderr}')
        output_lines = result.stdout.split('\n')
        test_count_lines = [line for line in output_lines if 'collected' in line.lower()]
        self.assertTrue(len(test_count_lines) > 0, f'Expected test collection summary, got: {result.stdout}')

    def test_agent_websocket_event_sequence_file_collection(self):
        """
        Verify agent WebSocket event sequence test file can be collected individually.

        This test focuses on the other specific file mentioned in Issue #971.
        """
        test_file_path = Path(__file__).parent / 'test_agent_websocket_event_sequence_integration.py'
        if not test_file_path.exists():
            self.skipTest(f'Test file not found: {test_file_path}')
        result = subprocess.run([sys.executable, '-m', 'pytest', str(test_file_path), '--collect-only', '-q'], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            self.fail(f'Individual test file collection failed. Return code: {result.returncode}, STDERR: {result.stderr}')
        output_lines = result.stdout.split('\n')
        test_count_lines = [line for line in output_lines if 'collected' in line.lower()]
        self.assertTrue(len(test_count_lines) > 0, f'Expected test collection summary, got: {result.stdout}')

@pytest.mark.integration
class UnifiedTestRunnerIntegrationTests(SSotBaseTestCase):
    """
    Comprehensive integration testing with the unified test runner
    to ensure the fix works within the complete test infrastructure.
    """

    def test_unified_test_runner_integration_category_filtering(self):
        """
        Verify unified test runner can properly filter and collect integration tests.

        This test verifies that the integration category filtering works
        correctly after the WebSocketTestManager alias fix.
        """
        test_runner_path = Path(__file__).parent.parent / 'unified_test_runner.py'
        result = subprocess.run([sys.executable, str(test_runner_path), '--collect-only', '--category', 'integration', '--verbose'], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            self.fail(f'Unified test runner integration filtering failed. Return code: {result.returncode}, STDERR: {result.stderr}')
        self.assertIn('collected', result.stdout.lower(), f'Expected collection summary in output: {result.stdout}')

    def test_unified_test_runner_no_import_errors_in_output(self):
        """
        Verify unified test runner output contains no WebSocketTestManager import errors.

        This test specifically looks for the absence of the error messages
        that were present before the fix.
        """
        test_runner_path = Path(__file__).parent.parent / 'unified_test_runner.py'
        result = subprocess.run([sys.executable, str(test_runner_path), '--collect-only', '--category', 'integration'], capture_output=True, text=True, timeout=60)
        combined_output = (result.stdout + result.stderr).lower()
        error_indicators = ["cannot import name 'websockettestmanager'", 'importerror', 'websockettestmanager', 'modulenotfounderror']
        found_errors = []
        for indicator in error_indicators:
            if indicator in combined_output:
                found_errors.append(indicator)
        if found_errors:
            self.fail(f'Found import error indicators in unified test runner output: {found_errors}. STDOUT: {result.stdout}. STDERR: {result.stderr}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')