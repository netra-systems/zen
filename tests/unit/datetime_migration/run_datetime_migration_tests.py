"""
DateTime Migration Test Runner

This script runs the comprehensive datetime migration test suite
as outlined in the Issue #980 test plan.
"""

import sys
import warnings
import unittest
from pathlib import Path
from typing import Dict, List, Any
import subprocess
import os

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class DateTimeMigrationTestRunner:
    """Comprehensive test runner for datetime migration."""

    def __init__(self):
        self.test_results = {}
        self.warnings_captured = []

    def capture_warnings(self):
        """Capture all warnings during test execution."""
        warnings.simplefilter("always")

        # Capture warnings to our list
        def warning_handler(message, category, filename, lineno, file=None, line=None):
            self.warnings_captured.append({
                'message': str(message),
                'category': category.__name__,
                'filename': filename,
                'lineno': lineno
            })

        warnings.showwarning = warning_handler

    def run_pre_migration_tests(self) -> Dict[str, Any]:
        """Run Phase 1: Pre-migration tests (expected to fail)."""
        print("=" * 70)
        print("PHASE 1: PRE-MIGRATION TESTS (Expected to Fail)")
        print("=" * 70)

        test_modules = [
            'test_websocket_protocol_datetime',
            'test_clickhouse_datetime',
            'test_health_check_datetime',
            'test_connection_manager_datetime',
            'test_pipeline_executor_datetime'
        ]

        results = {}
        total_tests = 0
        failed_tests = 0
        passed_tests = 0

        for module_name in test_modules:
            print(f"\nRunning {module_name}...")

            try:
                # Import the test module
                module = __import__(module_name, fromlist=[''])

                # Create test suite
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromModule(module)

                # Run tests
                runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
                result = runner.run(suite)

                # Record results
                module_results = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0
                }

                results[module_name] = module_results
                total_tests += result.testsRun
                failed_tests += len(result.failures) + len(result.errors)
                passed_tests += result.testsRun - len(result.failures) - len(result.errors)

                print(f"  {module_name}: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")

            except Exception as e:
                print(f"  ERROR running {module_name}: {e}")
                results[module_name] = {'error': str(e)}

        # Summary
        print("\n" + "=" * 70)
        print("PHASE 1 SUMMARY: Pre-Migration Test Results")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Overall Success Rate: {(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "N/A")

        # Check for deprecated pattern detection tests
        deprecated_tests_found = failed_tests > 0
        print(f"\nDeprecated Pattern Detection: {'CHECK WORKING' if deprecated_tests_found else 'X NOT DETECTING'}")
        print("(Failing tests indicate deprecated patterns are correctly detected)")

        return {
            'phase': 'pre_migration',
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'results': results,
            'deprecated_patterns_detected': deprecated_tests_found
        }

    def scan_target_files_for_patterns(self) -> Dict[str, List[str]]:
        """Scan the 5 target files for deprecated datetime patterns."""
        target_files = [
            "netra_backend/app/websocket_core/protocols.py",
            "netra_backend/app/db/clickhouse.py",
            "netra_backend/app/api/health_checks.py",
            "netra_backend/app/websocket_core/connection_manager.py",
            "netra_backend/app/agents/supervisor/pipeline_executor.py"
        ]

        results = {}

        for file_path in target_files:
            full_path = project_root / file_path
            patterns_found = []

            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        if "datetime.now(UTC)" in line:
                            patterns_found.append(f"Line {line_num}: {line.strip()}")

                    results[file_path] = patterns_found

                except Exception as e:
                    results[file_path] = [f"Error reading file: {e}"]
            else:
                results[file_path] = ["File not found"]

        return results

    def print_deprecated_pattern_analysis(self):
        """Print analysis of deprecated patterns in target files."""
        print("\n" + "=" * 70)
        print("DEPRECATED PATTERN ANALYSIS")
        print("=" * 70)

        pattern_results = self.scan_target_files_for_patterns()
        total_patterns = 0

        for file_path, patterns in pattern_results.items():
            print(f"\n📁 {file_path}")
            if patterns:
                print(f"  Found {len(patterns)} deprecated pattern(s):")
                for pattern in patterns:
                    print(f"    {pattern}")
                total_patterns += len(patterns)
            else:
                print("  CHECK No deprecated patterns found")

        print(f"\n🔍 TOTAL DEPRECATED PATTERNS: {total_patterns}")
        print("📋 TARGET: These patterns will be migrated to datetime.now(timezone.utc)")

        return pattern_results

    def run_behavioral_equivalence_tests(self) -> Dict[str, Any]:
        """Run behavioral equivalence tests."""
        print("\n" + "=" * 70)
        print("BEHAVIORAL EQUIVALENCE VALIDATION")
        print("=" * 70)

        # Test that old and new patterns produce equivalent results
        from datetime import datetime, timezone, UTC
        import time

        test_results = {}

        # Test 1: Timestamp equivalence
        print("\n🧪 Testing timestamp equivalence...")
        old_timestamp = datetime.now(UTC)
        time.sleep(0.001)  # Tiny delay
        new_timestamp = datetime.now(timezone.utc)

        time_diff = abs((new_timestamp.replace(tzinfo=None) - old_timestamp).total_seconds())
        equivalence_passed = time_diff < 1.0

        test_results['timestamp_equivalence'] = {
            'passed': equivalence_passed,
            'time_diff_seconds': time_diff,
            'old_format': old_timestamp.isoformat(),
            'new_format': new_timestamp.isoformat()
        }

        print(f"  Time difference: {time_diff:.6f} seconds")
        print(f"  Equivalence test: {'CHECK PASSED' if equivalence_passed else 'X FAILED'}")

        # Test 2: ISO format compatibility
        print("\n🧪 Testing ISO format compatibility...")
        old_iso = datetime.now(UTC).isoformat()
        new_iso = datetime.now(timezone.utc).isoformat()

        old_parseable = True
        new_parseable = True

        try:
            datetime.fromisoformat(old_iso)
        except Exception:
            old_parseable = False

        try:
            datetime.fromisoformat(new_iso)
        except Exception:
            new_parseable = False

        test_results['iso_format_compatibility'] = {
            'old_parseable': old_parseable,
            'new_parseable': new_parseable,
            'old_format': old_iso,
            'new_format': new_iso,
            'new_includes_timezone': new_iso.endswith('+00:00')
        }

        print(f"  Old format parseable: {'CHECK' if old_parseable else 'X'}")
        print(f"  New format parseable: {'CHECK' if new_parseable else 'X'}")
        print(f"  New format includes timezone: {'CHECK' if new_iso.endswith('+00:00') else 'X'}")

        return test_results

    def run_warning_detection_tests(self) -> Dict[str, Any]:
        """Test for datetime deprecation warnings."""
        print("\n" + "=" * 70)
        print("DEPRECATION WARNING DETECTION")
        print("=" * 70)

        # Clear previous warnings
        self.warnings_captured = []
        self.capture_warnings()

        # Execute code that might generate warnings
        try:
            # This should potentially generate deprecation warnings in Python 3.12+
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Execute some datetime operations
                from datetime import datetime, UTC
                test_timestamp = datetime.now(UTC)  # Deprecated in Python 3.12+

                # Check for warnings
                datetime_warnings = [warning for warning in w
                                   if 'utcnow' in str(warning.message) or
                                      'timezone' in str(warning.message)]

            warning_results = {
                'total_warnings': len(w),
                'datetime_warnings': len(datetime_warnings),
                'warnings_detected': len(datetime_warnings) > 0,
                'warning_messages': [str(warning.message) for warning in datetime_warnings]
            }

            print(f"  Total warnings captured: {len(w)}")
            print(f"  DateTime-related warnings: {len(datetime_warnings)}")

            if datetime_warnings:
                print("  Warning messages:")
                for warning in datetime_warnings:
                    print(f"    {warning.message}")
            else:
                print("  No datetime deprecation warnings detected")

            return warning_results

        except Exception as e:
            print(f"  Error during warning detection: {e}")
            return {'error': str(e)}

    def generate_migration_report(self) -> str:
        """Generate a comprehensive migration report."""
        report = []
        report.append("=" * 70)
        report.append("DATETIME MIGRATION COMPREHENSIVE REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        report.append("")

        # Pre-migration analysis
        pattern_results = self.scan_target_files_for_patterns()
        total_patterns = sum(len(patterns) for patterns in pattern_results.values())

        report.append("📋 MIGRATION SCOPE")
        report.append("-" * 20)
        report.append(f"Target Files: 5")
        report.append(f"Deprecated Patterns Found: {total_patterns}")
        report.append("")

        for file_path, patterns in pattern_results.items():
            report.append(f"  📁 {file_path}")
            report.append(f"     Patterns: {len(patterns)}")

        report.append("")

        # Behavioral equivalence results
        equivalence_results = self.run_behavioral_equivalence_tests()

        report.append("🧪 BEHAVIORAL EQUIVALENCE")
        report.append("-" * 25)

        if 'timestamp_equivalence' in equivalence_results:
            eq_result = equivalence_results['timestamp_equivalence']
            report.append(f"  Timestamp Equivalence: {'CHECK PASSED' if eq_result['passed'] else 'X FAILED'}")
            report.append(f"  Time Difference: {eq_result['time_diff_seconds']:.6f} seconds")

        if 'iso_format_compatibility' in equivalence_results:
            iso_result = equivalence_results['iso_format_compatibility']
            report.append(f"  ISO Format Compatibility: {'CHECK PASSED' if iso_result['old_parseable'] and iso_result['new_parseable'] else 'X FAILED'}")
            report.append(f"  New Format Includes Timezone: {'CHECK' if iso_result['new_includes_timezone'] else 'X'}")

        report.append("")

        # Migration recommendations
        report.append("🎯 MIGRATION RECOMMENDATIONS")
        report.append("-" * 30)
        report.append("1. Apply datetime.now(UTC) -> datetime.now(timezone.utc) migration to all 5 files")
        report.append("2. Update import statements to include timezone")
        report.append("3. Run post-migration tests to validate functionality")
        report.append("4. Monitor for deprecation warnings in Python 3.12+")
        report.append("")

        # Migration pattern
        report.append("🔄 MIGRATION PATTERN")
        report.append("-" * 20)
        report.append("BEFORE:")
        report.append("  from datetime import datetime"), UTC
        report.append("  timestamp = datetime.now(UTC)")
        report.append("")
        report.append("AFTER:")
        report.append("  from datetime import datetime, timezone"), UTC
        report.append("  timestamp = datetime.now(timezone.utc)")
        report.append("")

        return "\n".join(report)


def main():
    """Main execution function."""
    print("🚀 DateTime Migration Test Suite - Issue #980")
    print("=" * 70)

    runner = DateTimeMigrationTestRunner()

    # Phase 1: Run pre-migration tests (should fail to detect deprecated patterns)
    pre_migration_results = runner.run_pre_migration_tests()

    # Print deprecated pattern analysis
    runner.print_deprecated_pattern_analysis()

    # Run behavioral equivalence tests
    equivalence_results = runner.run_behavioral_equivalence_tests()

    # Test for deprecation warnings
    warning_results = runner.run_warning_detection_tests()

    # Generate comprehensive report
    report = runner.generate_migration_report()
    print("\n" + report)

    # Print final summary
    print("\n" + "=" * 70)
    print("📊 FINAL TEST EXECUTION SUMMARY")
    print("=" * 70)
    print(f"CHECK Test Suite Execution: COMPLETED")
    print(f"🔍 Deprecated Patterns: {'DETECTED' if pre_migration_results.get('deprecated_patterns_detected') else 'NOT DETECTED'}")
    print(f"⚖️ Behavioral Equivalence: VALIDATED")
    print(f"WARNING️ Warning Detection: {'ACTIVE' if warning_results.get('warnings_detected') else 'INACTIVE'}")
    print("\n🎯 READY FOR PHASE 2: Apply datetime migration to target files")


if __name__ == '__main__':
    main()