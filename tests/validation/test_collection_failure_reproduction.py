"""
Reproduction test suite for Issue #1041 pytest collection failures.

Business Value Justification (BVJ):
- Segment: Platform (affects all testing infrastructure)
- Business Goal: Stability (enable comprehensive test coverage validation)
- Value Impact: Prevents test discovery failures that hide regressions
- Strategic Impact: $500K+ ARR protection through reliable testing infrastructure

This test suite demonstrates how Test* class naming interferes with pytest collection,
causing timeouts, incomplete discovery, and unreliable test execution.

CRITICAL REPRODUCTION AREAS:
- Collection timeout demonstration with problematic files
- Test counting confusion caused by Test* classes
- Performance degradation measurement
- Comparison with proper naming patterns
"""
import subprocess
import sys
import time
import os
from test_framework.ssot.base_test_case import SSotBaseTestCase

class CollectionFailureReproductionTests(SSotBaseTestCase):
    """Reproduce pytest collection failures caused by Test* classes."""

    def test_collection_timeout_with_problematic_files(self):
        """Test that files with Test* classes cause collection timeouts."""

        # Files known to have Test* classes that cause collection issues
        problematic_files = [
            "netra_backend/tests/unit/websocket/test_message_queue_resilience.py",
            "netra_backend/tests/unit/websocket/test_websocket_connection_state_machine_comprehensive_unit.py",
            "netra_backend/tests/unit/websocket/test_websocket_id_migration_uuid_exposure.py",
            "netra_backend/tests/unit/websocket/test_websocket_integration_comprehensive_focused.py"
        ]

        collection_results = []

        for file_path in problematic_files:
            if os.path.exists(file_path):
                with self.subTest(file=file_path):
                    start_time = time.time()

                    try:
                        # Run collection on specific file with timeout
                        result = subprocess.run([
                            sys.executable, "-m", "pytest",
                            "--collect-only", "-q", file_path
                        ], capture_output=True, text=True, timeout=30)

                        collection_time = time.time() - start_time
                        collection_results.append({
                            'file': file_path,
                            'time': collection_time,
                            'returncode': result.returncode,
                            'stdout': result.stdout,
                            'stderr': result.stderr
                        })

                        # Collection should either fail or be very slow due to Test* confusion
                        if result.returncode == 0:
                            # If it succeeds, it should show signs of confusion
                            output_lower = result.stdout.lower()

                            # Check for signs of collection confusion
                            confusion_indicators = [
                                "no tests ran",
                                "0 tests collected",
                                "warnings summary"
                            ]

                            has_confusion = any(indicator in output_lower for indicator in confusion_indicators)

                            self.assertTrue(
                                collection_time > 5 or has_confusion,
                                f"Expected collection issues for {file_path}: "
                                f"time={collection_time:.2f}s, confusion={has_confusion}"
                            )
                        else:
                            # Collection failure is also acceptable as demonstration of the issue
                            print(f"Collection failed for {file_path}: {result.stderr}")

                    except subprocess.TimeoutExpired:
                        # Timeout is expected for problematic files
                        collection_time = time.time() - start_time
                        collection_results.append({
                            'file': file_path,
                            'time': collection_time,
                            'timeout': True
                        })
                        print(f"Collection timed out for {file_path} after {collection_time:.2f}s")

        # Log results for analysis
        print(f"\nCollection Results Summary:")
        for result in collection_results:
            print(f"  {result['file']}: {result['time']:.2f}s")

        # At least some files should demonstrate the issue
        slow_collections = [r for r in collection_results if r.get('time', 0) > 5]
        self.assertGreater(
            len(slow_collections), 0,
            "Expected at least some files to demonstrate collection issues"
        )

    def test_collection_confusion_count(self):
        """Test that Test* classes confuse pytest's test counting."""

        test_file = "netra_backend/tests/unit/websocket/test_message_queue_resilience.py"

        if os.path.exists(test_file):
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    "--collect-only", "-v", test_file
                ], capture_output=True, text=True, timeout=30)

                print(f"Collection output for {test_file}:")
                print(f"Return code: {result.returncode}")
                print(f"STDOUT: {result.stdout[:500]}")
                print(f"STDERR: {result.stderr[:500]}")

                if result.returncode == 0:
                    # Check for collection confusion
                    output = result.stdout.lower()

                    # Should show confusion indicators
                    confusion_signs = [
                        "no tests ran",
                        "0 tests collected",
                        "collected 0 items"
                    ]

                    has_confusion = any(sign in output for sign in confusion_signs)

                    if not has_confusion:
                        # If it does collect tests, verify they're actually runnable
                        # Test* classes often get collected but can't run properly
                        import re
                        test_count_match = re.search(r'(\d+) tests? collected', result.stdout)
                        if test_count_match:
                            test_count = int(test_count_match.group(1))
                            print(f"Collected {test_count} tests from Test* classes")

                            # This demonstrates the confusion - collecting non-test classes
                            self.fail(
                                f"Pytest incorrectly collected {test_count} 'tests' from Test* classes "
                                f"in {test_file}. This demonstrates the collection confusion issue."
                            )
                        else:
                            self.assertTrue(
                                "collected" not in output,
                                f"Expected collection confusion for {test_file}"
                            )
                    else:
                        print(f"Demonstrated collection confusion: {has_confusion}")

                else:
                    # Collection failure also demonstrates the issue
                    print(f"Collection failed as expected: {result.stderr}")

            except subprocess.TimeoutExpired:
                print(f"Collection timed out for {test_file} - demonstrates the issue")
        else:
            self.skipTest(f"Test file {test_file} not found")

    def test_problematic_pattern_identification(self):
        """Identify and document all Test* class patterns causing issues."""

        import re

        # Scan for Test* classes in test files
        problematic_patterns = []
        pattern = re.compile(r'^class (Test[A-Z]\w*).*:', re.MULTILINE)

        test_dirs = [
            "netra_backend/tests/unit/websocket",
            "netra_backend/tests/integration",
            "tests/unit",
            "tests/integration"
        ]

        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                for root, dirs, files in os.walk(test_dir):
                    for file in files:
                        if file.startswith('test_') and file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    matches = pattern.findall(content)
                                    if matches:
                                        for match in matches:
                                            problematic_patterns.append({
                                                'file': file_path,
                                                'class': match,
                                                'pattern': f'class {match}'
                                            })
                            except Exception as e:
                                print(f"Error reading {file_path}: {e}")

        # Log findings
        print(f"\nFound {len(problematic_patterns)} Test* class patterns:")
        for i, pattern in enumerate(problematic_patterns[:20]):  # Show first 20
            print(f"  {pattern['file']}: {pattern['class']}")

        if len(problematic_patterns) > 20:
            print(f"  ... and {len(problematic_patterns) - 20} more")

        # Document the scope of the issue
        unique_files = set(p['file'] for p in problematic_patterns)
        print(f"\nIssue scope: {len(unique_files)} files with Test* classes")

        # Issue #1041 mentioned 107+ files
        self.assertGreater(
            len(unique_files), 10,
            f"Expected significant number of problematic files, found {len(unique_files)}"
        )

        return problematic_patterns

    def test_baseline_collection_performance(self):
        """Establish baseline collection performance before fix."""

        # Test collection on a known problematic directory
        test_dir = "netra_backend/tests/unit/websocket"

        if os.path.exists(test_dir):
            start_time = time.time()

            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    "--collect-only", "-q", test_dir
                ], capture_output=True, text=True, timeout=120)

                collection_time = time.time() - start_time

                print(f"Baseline collection performance for {test_dir}:")
                print(f"  Time: {collection_time:.2f} seconds")
                print(f"  Return code: {result.returncode}")
                print(f"  Output length: {len(result.stdout)} chars")

                # Document baseline for comparison after fix
                baseline_data = {
                    'directory': test_dir,
                    'collection_time': collection_time,
                    'success': result.returncode == 0,
                    'output_length': len(result.stdout)
                }

                # Save baseline for later comparison
                with open('collection_baseline.json', 'w') as f:
                    import json
                    json.dump(baseline_data, f, indent=2)

                print(f"Baseline saved to collection_baseline.json")

                # Slow collection indicates the issue
                if collection_time > 30:
                    print(f"Demonstrated slow collection: {collection_time:.2f}s")

            except subprocess.TimeoutExpired:
                collection_time = time.time() - start_time
                print(f"Collection timed out after {collection_time:.2f}s - demonstrates issue")
        else:
            self.skipTest(f"Test directory {test_dir} not found")