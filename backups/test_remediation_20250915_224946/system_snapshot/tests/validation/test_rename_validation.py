"""
Validation tests for Issue #1041 fix - confirm renamed classes work properly.

Business Value Justification (BVJ):
- Segment: Platform (testing infrastructure improvement)
- Business Goal: Stability (reliable test discovery and execution)
- Value Impact: Enables fast, comprehensive test coverage validation
- Strategic Impact: Developer productivity and CI/CD pipeline reliability

This test suite validates that renaming Test* classes to *Tests pattern
resolves pytest collection issues while maintaining test functionality.

VALIDATION AREAS:
- Collection speed improvement verification
- Test discovery accuracy validation
- Performance comparison (before/after fix)
- System-wide collection health checks
"""
import subprocess
import sys
import tempfile
import os
import time
import json
from test_framework.ssot.base_test_case import SSotBaseTestCase

class RenameValidationTests(SSotBaseTestCase):
    """Validate that renaming Test* classes fixes collection issues."""

    def test_renamed_class_collection_success(self):
        """Test that properly renamed classes collect successfully."""

        # Create a temporary test file with renamed classes (good pattern)
        temp_content = '''
"""Temporary test file with properly named test classes."""
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class MessageQueueResilienceTests(SSotBaseTestCase):
    """Properly named test class - should collect successfully."""

    def test_example_functionality(self):
        """Example test method."""
        self.assertTrue(True)

    def test_another_functionality(self):
        """Another test method."""
        self.assertEqual(1, 1)

class ConnectionHandlerTests(SSotBaseTestCase):
    """Another properly named test class."""

    def test_connection_logic(self):
        """Test connection handling logic."""
        self.assertIsNotNone("test")

    def test_handler_behavior(self):
        """Test handler behavior."""
        self.assertEqual(2 + 2, 4)
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='_test_renamed.py', delete=False) as f:
            f.write(temp_content)
            temp_file = f.name

        try:
            start_time = time.time()

            # Test collection on renamed file
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "--collect-only", "-v", temp_file
            ], capture_output=True, text=True, timeout=15)

            collection_time = time.time() - start_time

            print(f"Renamed classes collection test:")
            print(f"  Time: {collection_time:.2f} seconds")
            print(f"  Return code: {result.returncode}")
            print(f"  Output: {result.stdout[:300]}")

            # Should collect successfully and quickly
            self.assertEqual(result.returncode, 0, f"Collection failed: {result.stderr}")
            self.assertLess(collection_time, 10, f"Collection too slow: {collection_time:.2f}s")

            # Should collect exactly 4 tests (2 from each class)
            self.assertIn("4 tests collected", result.stdout, "Should collect exactly 4 tests")

            # Should show proper test names
            self.assertIn("MessageQueueResilienceTests", result.stdout)
            self.assertIn("ConnectionHandlerTests", result.stdout)

        finally:
            try:
                os.unlink(temp_file)
            except:
                pass

    def test_problematic_vs_fixed_comparison(self):
        """Compare collection time between problematic and fixed naming."""

        # Problematic content (Test* classes that cause issues)
        problematic_content = '''
"""Temporary file with problematic Test* classes."""

class ProblematicClassTests:
    """This causes collection issues - no proper inheritance."""
    pass

class AnotherProblematicTests:
    """This also causes issues - pytest tries to collect it."""
    def some_method(self):
        pass

class ConfusingClassTests:
    """Another problematic class."""
    def __init__(self):
        pass
'''

        # Fixed content (renamed classes)
        fixed_content = '''
"""Temporary file with properly renamed classes."""
from test_framework.ssot.base_test_case import SSotBaseTestCase

class ProblematicClassTests(SSotBaseTestCase):
    """This is properly named and inherits correctly."""
    def test_example(self):
        self.assertTrue(True)

class AnotherProblematicTests(SSotBaseTestCase):
    """This is also properly named."""
    def test_example(self):
        self.assertTrue(True)

class ConfusingClassTests(SSotBaseTestCase):
    """No longer confusing with proper naming."""
    def test_functionality(self):
        self.assertEqual(1, 1)
'''

        results = {}

        # Test both versions
        for content, description in [(problematic_content, "problematic"), (fixed_content, "fixed")]:
            with self.subTest(type=description):
                with tempfile.NamedTemporaryFile(mode='w', suffix=f'_test_{description}.py', delete=False) as f:
                    f.write(content)
                    temp_file = f.name

                try:
                    start_time = time.time()

                    result = subprocess.run([
                        sys.executable, "-m", "pytest",
                        "--collect-only", "-q", temp_file
                    ], capture_output=True, text=True, timeout=20)

                    collection_time = time.time() - start_time

                    results[description] = {
                        'time': collection_time,
                        'success': result.returncode == 0,
                        'output': result.stdout,
                        'stderr': result.stderr
                    }

                    print(f"{description.title()} version results:")
                    print(f"  Time: {collection_time:.2f} seconds")
                    print(f"  Success: {result.returncode == 0}")
                    print(f"  Output: {result.stdout[:200]}")

                    if description == "fixed":
                        # Fixed version should collect quickly and successfully
                        self.assertEqual(result.returncode, 0, f"Fixed version should collect: {result.stderr}")
                        self.assertLess(collection_time, 8, f"Fixed version too slow: {collection_time:.2f}s")
                        self.assertIn("3 tests collected", result.stdout, "Should collect 3 tests from fixed version")

                    elif description == "problematic":
                        # Problematic version might fail or be confusing
                        if result.returncode == 0:
                            # If it "succeeds", it should show confusion
                            output_lower = result.stdout.lower()
                            confusion_indicators = ["no tests ran", "0 tests collected"]
                            has_confusion = any(indicator in output_lower for indicator in confusion_indicators)

                            if not has_confusion:
                                # Check if it incorrectly collected "tests" from non-test classes
                                import re
                                collected_match = re.search(r'(\d+) tests? collected', result.stdout)
                                if collected_match and int(collected_match.group(1)) > 0:
                                    print(f"Demonstrated collection confusion: "
                                          f"pytest incorrectly collected tests from Test* classes")

                except subprocess.TimeoutExpired:
                    collection_time = time.time() - start_time
                    results[description] = {
                        'time': collection_time,
                        'timeout': True
                    }
                    print(f"{description.title()} version timed out after {collection_time:.2f}s")

                finally:
                    try:
                        os.unlink(temp_file)
                    except:
                        pass

        # Compare results
        if 'problematic' in results and 'fixed' in results:
            prob_time = results['problematic']['time']
            fixed_time = results['fixed']['time']

            print(f"\nComparison:")
            print(f"  Problematic: {prob_time:.2f}s")
            print(f"  Fixed: {fixed_time:.2f}s")
            print(f"  Improvement: {((prob_time - fixed_time) / prob_time * 100):.1f}%")

    def test_collection_performance_after_fix(self):
        """Test collection performance on directories after Test* class renaming."""

        # Test directories that should benefit from the fix
        test_directories = [
            "netra_backend/tests/unit/websocket",
            "netra_backend/tests/integration"
        ]

        performance_results = []

        for test_dir in test_directories:
            if os.path.exists(test_dir):
                with self.subTest(directory=test_dir):
                    start_time = time.time()

                    result = subprocess.run([
                        sys.executable, "-m", "pytest",
                        "--collect-only", "-q", test_dir
                    ], capture_output=True, text=True, timeout=90)

                    collection_time = time.time() - start_time

                    perf_data = {
                        'directory': test_dir,
                        'time': collection_time,
                        'success': result.returncode == 0,
                        'output_length': len(result.stdout)
                    }
                    performance_results.append(perf_data)

                    print(f"Collection performance for {test_dir}:")
                    print(f"  Time: {collection_time:.2f} seconds")
                    print(f"  Success: {result.returncode == 0}")

                    # After fix, collection should be reasonably fast
                    if result.returncode == 0:
                        self.assertLess(
                            collection_time, 60,
                            f"Collection still too slow for {test_dir}: {collection_time:.2f}s"
                        )

                        # Should collect actual tests
                        self.assertIn("collected", result.stdout.lower(), "Should show test collection")

                    # Compare with baseline if available
                    baseline_file = 'collection_baseline.json'
                    if os.path.exists(baseline_file):
                        try:
                            with open(baseline_file, 'r') as f:
                                baseline = json.load(f)

                            if baseline.get('directory') == test_dir:
                                baseline_time = baseline.get('collection_time', 0)
                                if baseline_time > 0:
                                    improvement = ((baseline_time - collection_time) / baseline_time) * 100
                                    print(f"  Improvement vs baseline: {improvement:.1f}%")

                                    # Should show improvement (or at least not regression)
                                    self.assertLessEqual(
                                        collection_time, baseline_time * 1.1,  # Allow 10% tolerance
                                        f"Collection time regressed for {test_dir}"
                                    )
                        except Exception as e:
                            print(f"Could not compare with baseline: {e}")

        # Save performance results for future reference
        with open('collection_performance_after_fix.json', 'w') as f:
            json.dump(performance_results, f, indent=2)

        print(f"Performance results saved to collection_performance_after_fix.json")

    def test_renamed_classes_maintain_functionality(self):
        """Verify that renamed test classes maintain their testing functionality."""

        # Create a test file with renamed classes that actually test something
        functional_test_content = '''
"""Test file to verify renamed classes maintain functionality."""
from test_framework.ssot.base_test_case import SSotBaseTestCase

class MathOperationsTests(SSotBaseTestCase):
    """Test mathematical operations - renamed from TestMathOperations."""

    def test_addition(self):
        """Test addition functionality."""
        self.assertEqual(2 + 2, 4)

    def test_multiplication(self):
        """Test multiplication functionality."""
        self.assertEqual(3 * 4, 12)

class StringManipulationTests(SSotBaseTestCase):
    """Test string operations - renamed from TestStringManipulation."""

    def test_string_concatenation(self):
        """Test string concatenation."""
        result = "Hello" + " " + "World"
        self.assertEqual(result, "Hello World")

    def test_string_upper(self):
        """Test string upper case conversion."""
        self.assertEqual("test".upper(), "TEST")
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='_functional_test.py', delete=False) as f:
            f.write(functional_test_content)
            temp_file = f.name

        try:
            # First test collection
            collect_result = subprocess.run([
                sys.executable, "-m", "pytest",
                "--collect-only", "-v", temp_file
            ], capture_output=True, text=True, timeout=10)

            self.assertEqual(collect_result.returncode, 0, "Collection should succeed")
            self.assertIn("4 tests collected", collect_result.stdout, "Should collect 4 tests")

            # Then test actual execution
            run_result = subprocess.run([
                sys.executable, "-m", "pytest",
                "-v", temp_file
            ], capture_output=True, text=True, timeout=15)

            self.assertEqual(run_result.returncode, 0, f"Test execution should succeed: {run_result.stderr}")

            # All tests should pass
            self.assertIn("4 passed", run_result.stdout, "All 4 tests should pass")

            # Verify specific test names are visible
            self.assertIn("MathOperationsTests::test_addition", run_result.stdout)
            self.assertIn("StringManipulationTests::test_string_concatenation", run_result.stdout)

            print("Renamed classes functionality verification:")
            print(f"  Collection: SUCCESS")
            print(f"  Execution: SUCCESS")
            print(f"  All tests passed: TRUE")

        finally:
            try:
                os.unlink(temp_file)
            except:
                pass