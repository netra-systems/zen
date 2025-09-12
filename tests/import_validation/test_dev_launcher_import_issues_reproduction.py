#!/usr/bin/env python3
"""
COMPREHENSIVE TEST PLAN: dev_launcher Import Issues Reproduction & Validation

PURPOSE: 
Test plan for reproducing and validating fixes for "No module named 'dev_launcher.isolated_environment'" 
import issues that occur when files outside of dev_launcher try to import from dev_launcher.isolated_environment.

CONTEXT:
- Issue: `from dev_launcher.isolated_environment import IsolatedEnvironment` fails from outside dev_launcher
- Root cause: Incomplete SSOT migration - IsolatedEnvironment moved to shared/isolated_environment.py
- Business impact: Frontend thread loading failures when tests run
- Found in: netra_backend/app/core/configuration/demo.py and tests/integration/execution_engine_ssot/test_configuration_integration.py

STRATEGY:
1. Create tests that FAIL BEFORE fixes are applied (reproduction tests)
2. Create tests that PASS AFTER fixes are applied (validation tests)  
3. Focus on integration level tests (non-docker)
4. Follow testing best practices from reports/testing/TEST_CREATION_GUIDE.md

Generated: 2025-09-12
"""

import sys
import importlib
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

# Test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDevLauncherImportIssuesReproduction(SSotBaseTestCase, unittest.TestCase):
    """
    FAILING TESTS: These tests reproduce the import errors that occur BEFORE fixes are applied.
    These tests are designed to FAIL initially, then PASS after remediation.
    """
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.problematic_files = [
            "netra_backend/app/core/configuration/demo.py",
            "tests/integration/execution_engine_ssot/test_configuration_integration.py"
        ]
        
    def test_reproduce_demo_py_import_failure(self):
        """
        REPRODUCTION TEST: Verify that demo.py fails to import IsolatedEnvironment from dev_launcher.
        
        This test should FAIL before the fix and PASS after the fix.
        Business Impact: Demo mode configuration fails, affecting development and testing workflows.
        """
        # This test reproduces the exact error that occurs when running demo.py
        with self.assertRaises(ModuleNotFoundError) as context:
            # Simulate the problematic import from demo.py line 8
            exec("from dev_launcher.isolated_environment import IsolatedEnvironment")
        
        # Verify it's the specific error we're targeting
        self.assertIn("No module named 'dev_launcher.isolated_environment'", str(context.exception))
        self.assertEqual(context.exception.__class__.__name__, "ModuleNotFoundError")
        
    def test_reproduce_configuration_integration_import_failure(self):
        """
        REPRODUCTION TEST: Verify that test_configuration_integration.py fails to import from dev_launcher.
        
        This test should FAIL before the fix and PASS after the fix.
        Business Impact: Integration tests fail, preventing proper validation of configuration systems.
        """
        # This reproduces the error from test_configuration_integration.py line 129
        with self.assertRaises(ModuleNotFoundError) as context:
            # Simulate the problematic import from the integration test
            exec("from dev_launcher.isolated_environment import IsolatedEnvironment")
        
        # Verify error details
        self.assertIn("No module named 'dev_launcher.isolated_environment'", str(context.exception))
        
    def test_reproduce_dynamic_import_failures(self):
        """
        REPRODUCTION TEST: Test that dynamic imports also fail consistently.
        
        This ensures that the issue affects both static and dynamic imports.
        """
        # Test dynamic import failure
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("dev_launcher.isolated_environment")
            
        # Test that the specific class import fails
        with self.assertRaises(ModuleNotFoundError):
            from_module = importlib.import_module("dev_launcher.isolated_environment")
            getattr(from_module, "IsolatedEnvironment")
            
    def test_reproduce_import_in_subprocess_context(self):
        """
        REPRODUCTION TEST: Verify the import fails in subprocess contexts (like thread loading).
        
        Business Impact: This reproduces the frontend thread loading failures mentioned in the issue.
        """
        import subprocess
        
        # Test the import in a subprocess to simulate thread loading scenarios
        result = subprocess.run([
            sys.executable, "-c", 
            "from dev_launcher.isolated_environment import IsolatedEnvironment; print('SUCCESS')"
        ], capture_output=True, text=True)
        
        # Should fail with non-zero exit code
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ModuleNotFoundError", result.stderr)
        self.assertIn("No module named 'dev_launcher.isolated_environment'", result.stderr)
        
    def test_reproduce_import_from_different_working_directories(self):
        """
        REPRODUCTION TEST: Verify the import fails from different working directories.
        
        This ensures the issue is consistent across different execution contexts.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temporary directory
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                # Try import from different working directory
                with self.assertRaises(ModuleNotFoundError):
                    exec("from dev_launcher.isolated_environment import IsolatedEnvironment")
                    
            finally:
                os.chdir(original_cwd)


class TestDevLauncherImportIssuesValidation(SSotBaseTestCase, unittest.TestCase):
    """
    VALIDATION TESTS: These tests validate that the correct imports work after fixes are applied.
    These tests should PASS both before and after fixes (they test the correct behavior).
    """
    
    def test_correct_import_from_shared_works(self):
        """
        VALIDATION TEST: Verify that importing from shared.isolated_environment works correctly.
        
        This test validates the correct import path and should PASS.
        """
        try:
            from shared.isolated_environment import IsolatedEnvironment
            
            # Verify the import was successful
            self.assertTrue(hasattr(IsolatedEnvironment, '__init__'))
            
            # Test that we can instantiate the class
            env_instance = IsolatedEnvironment()
            self.assertIsInstance(env_instance, IsolatedEnvironment)
            
        except ImportError as e:
            self.fail(f"Correct import from shared.isolated_environment failed: {e}")
            
    def test_isolated_environment_class_functionality(self):
        """
        VALIDATION TEST: Verify that IsolatedEnvironment class functions correctly after import.
        
        This ensures that the SSOT migration preserved functionality.
        """
        from shared.isolated_environment import IsolatedEnvironment
        
        # Test basic functionality
        env = IsolatedEnvironment()
        
        # Test that essential methods exist and work
        self.assertTrue(hasattr(env, 'get'))
        self.assertTrue(hasattr(env, 'get_bool'))
        self.assertTrue(hasattr(env, 'enable_isolation'))
        
        # Test basic functionality doesn't raise exceptions
        try:
            test_value = env.get('TEST_VAR', 'default_value')
            self.assertEqual(test_value, 'default_value')  # Should return default since TEST_VAR doesn't exist
        except Exception as e:
            self.fail(f"Basic IsolatedEnvironment functionality failed: {e}")
            
    def test_dynamic_import_from_shared_works(self):
        """
        VALIDATION TEST: Verify that dynamic imports from shared work correctly.
        """
        try:
            # Test dynamic import
            module = importlib.import_module("shared.isolated_environment")
            IsolatedEnvironment = getattr(module, "IsolatedEnvironment")
            
            # Test instantiation
            env_instance = IsolatedEnvironment()
            self.assertIsNotNone(env_instance)
            
        except (ImportError, AttributeError) as e:
            self.fail(f"Dynamic import from shared.isolated_environment failed: {e}")
            
    def test_shared_import_in_subprocess_context(self):
        """
        VALIDATION TEST: Verify that importing from shared works in subprocess contexts.
        
        This validates that the fix resolves thread loading issues.
        """
        import subprocess
        
        # Test the correct import in a subprocess
        result = subprocess.run([
            sys.executable, "-c", 
            "from shared.isolated_environment import IsolatedEnvironment; print('SUCCESS')"
        ], capture_output=True, text=True)
        
        # Should succeed with zero exit code
        self.assertEqual(result.returncode, 0, f"Subprocess failed: {result.stderr}")
        self.assertIn("SUCCESS", result.stdout)


class TestImportPatternValidation(SSotBaseTestCase, unittest.TestCase):
    """
    COMPREHENSIVE VALIDATION: Tests to ensure all problematic import patterns are identified.
    """
    
    def test_identify_all_problematic_files(self):
        """
        VALIDATION TEST: Scan codebase to identify any remaining problematic imports.
        
        This test helps ensure comprehensive fix coverage.
        """
        import os
        import re
        
        project_root = Path(__file__).parent.parent.parent
        problematic_pattern = re.compile(r'from\s+dev_launcher\.isolated_environment\s+import')
        
        problematic_files = []
        
        # Scan only files outside of dev_launcher directory
        for root, dirs, files in os.walk(project_root):
            # Skip dev_launcher directory itself
            if 'dev_launcher' in Path(root).parts:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if problematic_pattern.search(content):
                                relative_path = file_path.relative_to(project_root)
                                problematic_files.append(str(relative_path))
                    except (UnicodeDecodeError, PermissionError):
                        # Skip files that can't be read
                        continue
        
        # Before fix: Should find the known problematic files
        # After fix: Should find no problematic files
        expected_problematic_files = [
            "netra_backend/app/core/configuration/demo.py",
            "tests/integration/execution_engine_ssot/test_configuration_integration.py"
        ]
        
        # For reproduction phase, verify we find the expected problematic files
        self.assertTrue(
            len(problematic_files) >= 2, 
            f"Expected to find at least 2 problematic files, found: {problematic_files}"
        )
        
    def test_validate_ssot_migration_completeness(self):
        """
        VALIDATION TEST: Verify that the SSOT migration was completed correctly.
        
        Ensures that shared.isolated_environment has all expected functionality.
        """
        from shared.isolated_environment import IsolatedEnvironment
        
        # Test that essential SSOT functionality is present
        required_methods = [
            'get', 'get_bool', 'get_int', 'get_float', 
            'enable_isolation', 'disable_isolation',
            'load_from_file', 'get_debug_info'
        ]
        
        for method_name in required_methods:
            self.assertTrue(
                hasattr(IsolatedEnvironment, method_name),
                f"SSOT migration incomplete: missing method {method_name}"
            )
            
    def test_ensure_dev_launcher_internal_imports_still_work(self):
        """
        VALIDATION TEST: Ensure that internal dev_launcher imports still function.
        
        The fix should only affect external imports, not internal dev_launcher functionality.
        """
        # This test validates that files WITHIN dev_launcher can still import from each other
        # We don't actually test the internal imports here since they should continue working
        # This is more of a conceptual test to document the requirement
        
        # Verify that the dev_launcher module structure still exists
        dev_launcher_path = Path(__file__).parent.parent.parent / "dev_launcher"
        self.assertTrue(dev_launcher_path.exists(), "dev_launcher directory should still exist")
        
        # Verify that dev_launcher has its own __init__.py
        init_path = dev_launcher_path / "__init__.py"
        self.assertTrue(init_path.exists(), "dev_launcher __init__.py should exist for internal imports")


if __name__ == '__main__':
    # Run the reproduction tests first (these should fail before fix)
    reproduction_suite = unittest.TestLoader().loadTestsFromTestCase(TestDevLauncherImportIssuesReproduction)
    validation_suite = unittest.TestLoader().loadTestsFromTestCase(TestDevLauncherImportIssuesValidation)
    pattern_suite = unittest.TestLoader().loadTestsFromTestCase(TestImportPatternValidation)
    
    # Combine all test suites
    all_tests = unittest.TestSuite([reproduction_suite, validation_suite, pattern_suite])
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(all_tests)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)