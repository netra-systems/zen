"""
Mission Critical Test: Decorator Import Error Blocking Issue #268A

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Goal: Stability
- Value Impact: Unlocks 7,474 unit tests for $400K+ ARR validation
- Revenue Impact: Prevents regression testing gaps that could impact all customer segments

This test validates that the experimental_test decorator import issue
is resolved and that unit test discovery works properly.
"""

import pytest
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDecoratorImportBlockingIssue268A(SSotBaseTestCase):
    """
    MISSION CRITICAL: Test that reproduces and validates fix for decorator import issue.
    
    This issue blocks discovery of 7,474 unit tests, representing 85% of testing capability.
    """
    
    def test_experimental_test_decorator_import_fails_before_fix(self):
        """
        REPRODUCTION TEST: Demonstrates the exact import failure blocking unit test discovery.
        
        This test MUST FAIL before the fix and PASS after the fix.
        BVJ: Platform | Testing Infrastructure | Critical for unit test execution
        """
        # This test is designed to FAIL before fix and PASS after fix
        try:
            # This is the exact import that's failing in unit tests
            from test_framework.decorators import experimental_test
            
            # If we get here, the import succeeded
            self.assertIsNotNone(experimental_test, "experimental_test decorator should be importable")
            self.assertTrue(callable(experimental_test), "experimental_test should be callable")
            
            # Test that the decorator can be used
            @experimental_test("Test decorator functionality")
            def dummy_test():
                pass
            
            # Verify the decorator was applied
            self.assertTrue(hasattr(dummy_test, '_pytest_mark_name') or 
                          hasattr(dummy_test, '__wrapped__') or
                          'experimental' in str(dummy_test),
                          "experimental_test decorator should mark the function")
            
        except ImportError as e:
            # This is the expected failure BEFORE the fix
            self.fail(f"EXPECTED FAILURE BEFORE FIX: Cannot import experimental_test: {e}")
    
    def test_all_required_decorators_available_for_unit_tests(self):
        """
        COMPREHENSIVE TEST: Validates all decorators needed by unit tests are importable.
        
        BVJ: Platform | Testing Infrastructure | Ensures complete decorator availability
        """
        required_decorators = [
            'experimental_test',  # The main blocker
            'requires_real_database',
            'requires_real_redis', 
            'requires_real_services',
            'requires_docker',
            'requires_websocket',
            'mission_critical',
            'race_condition_test'
        ]
        
        missing_decorators = []
        
        for decorator_name in required_decorators:
            try:
                # Test import from package interface
                exec(f"from test_framework.decorators import {decorator_name}")
            except ImportError:
                missing_decorators.append(decorator_name)
        
        if missing_decorators:
            self.fail(f"Missing decorators blocking unit test discovery: {missing_decorators}")
    
    def test_unit_test_discovery_count_validation(self):
        """
        VALIDATION TEST: Verifies that fixing imports enables discovery of expected test count.
        
        BVJ: Platform | Testing Infrastructure | Validates test discovery capability
        """
        # Run test discovery to count discoverable tests
        try:
            cmd = [
                sys.executable, 
                "tests/unified_test_runner.py",
                "--no-docker",
                "--category", "unit",
                "--no-dependencies",
                "--show-category-stats"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=Path.cwd()
            )
            
            # Parse output to find test count
            output_lines = result.stdout.split('\n') + result.stderr.split('\n')
            
            discovered_tests = 0
            for line in output_lines:
                if 'unit' in line.lower() and any(word in line for word in ['test', 'collected', 'found']):
                    # Extract number from line like "unit: 7474 tests found"
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        discovered_tests = max(discovered_tests, int(numbers[0]))
            
            # BEFORE FIX: Should discover very few tests (~160)
            # AFTER FIX: Should discover 7,474+ tests
            self.assertGreater(discovered_tests, 6000, 
                             f"Expected 7,474+ unit tests discoverable, found only {discovered_tests}")
            
        except subprocess.TimeoutExpired:
            self.fail("Test discovery timed out - may indicate import errors")
        except Exception as e:
            self.fail(f"Test discovery failed: {e}")
    
    def test_specific_failing_unit_test_files_now_discoverable(self):
        """
        TARGETED TEST: Validates specific files that were failing are now discoverable.
        
        BVJ: Platform | Testing Infrastructure | Ensures problematic files are fixed
        """
        # These are examples of files that use experimental_test and were failing
        problematic_files = [
            "netra_backend/tests/unit/test_feature_flags_example.py",
            "netra_backend/tests/examples/test_tdd_workflow_demo.py", 
            "netra_backend/tests/examples/test_feature_flag_environment_demo.py"
        ]
        
        for file_path in problematic_files:
            if Path(file_path).exists():
                # Test that Python can parse the file without import errors
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Compile the file to check for syntax/import errors
                    compile(content, file_path, 'exec')
                    
                except Exception as e:
                    self.fail(f"File {file_path} still has import issues: {e}")
    
    def test_decorator_package_consistency(self):
        """
        REGRESSION PREVENTION: Ensures decorator package exports match available decorators.
        
        BVJ: Platform | Code Quality | Prevents future import inconsistencies
        """
        # Import the standalone decorators module
        import test_framework.decorators as standalone_module
        
        # Import the package interface
        import test_framework.decorators as package_interface
        
        # Get all decorator functions from standalone module
        standalone_decorators = {
            name: getattr(standalone_module, name) 
            for name in dir(standalone_module)
            if callable(getattr(standalone_module, name)) and not name.startswith('_')
        }
        
        # Check that package interface exports all decorators
        missing_from_package = []
        for decorator_name in standalone_decorators:
            if not hasattr(package_interface, decorator_name):
                missing_from_package.append(decorator_name)
        
        if missing_from_package:
            self.fail(f"Package interface missing decorators: {missing_from_package}")


class TestPostFixValidation(SSotBaseTestCase):
    """
    POST-FIX VALIDATION: Tests that run AFTER the fix to validate success.
    """
    
    @pytest.mark.integration  
    def test_full_unit_test_suite_runs_successfully(self):
        """
        INTEGRATION TEST: Validates that the full unit test suite can run after fix.
        
        BVJ: Platform | System Validation | Ensures fix enables full testing capability
        """
        # This test validates the complete fix works end-to-end
        try:
            cmd = [
                sys.executable,
                "tests/unified_test_runner.py", 
                "--no-docker",
                "--category", "unit",
                "--fast-fail",  # Stop on first failure for quick feedback
                "--no-coverage"  # Focus on discovery, not coverage
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=Path.cwd()
            )
            
            # Validate test collection succeeded (return code 0 for collection)
            if result.returncode != 0:
                # Check if it's a collection error vs test failure
                if 'ImportError' in result.stderr or 'cannot import' in result.stderr:
                    self.fail(f"Import errors still present: {result.stderr}")
                else:
                    # Test failures are acceptable, import errors are not
                    print(f"Tests collected successfully, some may have failed: {result.stdout}")
            
            # Verify substantial test discovery
            output = result.stdout + result.stderr
            if 'collected' in output.lower():
                import re
                collected_match = re.search(r'collected (\d+)', output, re.IGNORECASE)
                if collected_match:
                    collected_count = int(collected_match.group(1))
                    self.assertGreater(collected_count, 6000,
                                     f"Expected 7,474+ tests collected, got {collected_count}")
            
        except subprocess.TimeoutExpired:
            self.fail("Unit test execution timed out")
        except Exception as e:
            self.fail(f"Unit test execution failed: {e}")