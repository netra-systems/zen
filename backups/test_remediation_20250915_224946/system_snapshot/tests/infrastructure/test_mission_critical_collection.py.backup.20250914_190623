"""
Test Mission Critical Test Collection Integrity

Business Value Justification (BVJ):
- Segment: Platform (Infrastructure)
- Business Goal: System Stability - Ensure test collection works
- Value Impact: Test discovery must work for Golden Path validation
- Strategic Impact: Deployment confidence through test execution capability

CRITICAL: This test MUST FAIL until mission-critical test collection succeeds.
Expected: Test collection failures due to syntax errors blocking pytest discovery.
"""

import glob
import os
import sys
import pytest
import subprocess
from typing import List, Dict, Tuple

class TestMissionCriticalCollection:
    """Test suite to validate mission-critical test collection integrity."""

    def test_mission_critical_test_collection_succeeds(self):
        """
        CRITICAL TEST: Validate all mission-critical test files can be collected by pytest.

        This test MUST FAIL initially due to syntax errors blocking collection.
        Expected: Collection failures preventing test discovery and execution.

        Business Impact: Without successful test collection, mission-critical tests
        cannot run, blocking validation of $500K+ ARR Golden Path functionality.
        """
        # Get mission-critical test directory
        mission_critical_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "mission_critical"
        )

        # Verify mission-critical directory exists
        assert os.path.exists(mission_critical_dir), f"Mission critical directory not found: {mission_critical_dir}"

        # Attempt to collect tests using pytest
        collection_results = self._collect_tests_with_pytest(mission_critical_dir)

        # Analyze collection results
        total_files = collection_results['total_files']
        collected_files = collection_results['collected_files']
        collection_errors = collection_results['errors']
        collection_warnings = collection_results['warnings']

        # Generate collection report
        collection_success_rate = (collected_files / max(total_files, 1)) * 100

        collection_report = f"""
MISSION CRITICAL TEST COLLECTION REPORT
=======================================

Directory: {mission_critical_dir}
Total Python Files: {total_files}
Successfully Collected Files: {collected_files}
Collection Success Rate: {collection_success_rate:.1f}%
Collection Errors: {len(collection_errors)}
Collection Warnings: {len(collection_warnings)}

COLLECTION ERRORS:
"""

        for error in collection_errors[:10]:  # Show first 10 errors for readability
            collection_report += f"""
{error['type']}: {error['file']}
Error: {error['message'][:200]}...
---"""

        if len(collection_errors) > 10:
            collection_report += f"\n... and {len(collection_errors) - 10} more collection errors."

        collection_report += f"""

COLLECTION WARNINGS:
"""

        for warning in collection_warnings[:5]:  # Show first 5 warnings
            collection_report += f"""
{warning['type']}: {warning['file']}
Warning: {warning['message'][:150]}...
---"""

        if len(collection_warnings) > 5:
            collection_report += f"\n... and {len(collection_warnings) - 5} more collection warnings."

        collection_report += f"""

EXPECTED RESULT: 100% collection success rate after syntax errors are fixed.
BUSINESS IMPACT: {100 - collection_success_rate:.1f}% of mission-critical tests uncollectable.
GOLDEN PATH IMPACT: Cannot validate business functionality with failed test collection.

NEXT ACTION: Fix syntax errors to restore test collection capability.
"""

        # This assertion MUST FAIL initially due to syntax errors
        assert collection_success_rate >= 100.0, collection_report

    def test_pytest_collection_specific_file_validation(self):
        """
        Validate specific mission-critical test files for collection issues.

        Tests individual files to identify specific collection problems beyond syntax errors.
        """
        # Get all mission-critical test files
        mission_critical_pattern = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "mission_critical",
            "**",
            "test_*.py"
        )

        test_files = glob.glob(mission_critical_pattern, recursive=True)

        individual_results = []

        for file_path in test_files:
            # Test individual file collection
            file_result = self._collect_single_file(file_path)
            individual_results.append(file_result)

        # Analyze individual file results
        total_files = len(individual_results)
        successful_files = len([r for r in individual_results if r['success']])
        failed_files = len([r for r in individual_results if not r['success']])

        success_rate = (successful_files / max(total_files, 1)) * 100

        individual_report = f"""
INDIVIDUAL FILE COLLECTION ANALYSIS
===================================

Total Test Files: {total_files}
Successful Collections: {successful_files}
Failed Collections: {failed_files}
Individual Success Rate: {success_rate:.1f}%

FAILED FILE DETAILS:
"""

        failed_results = [r for r in individual_results if not r['success']]
        for result in failed_results[:5]:  # Show first 5 failed files
            individual_report += f"""
File: {result['file']}
Error Type: {result['error_type']}
Error: {result['error_message'][:150]}...
---"""

        if len(failed_results) > 5:
            individual_report += f"\n... and {len(failed_results) - 5} more failed collections."

        individual_report += f"""

ANALYSIS: Individual file collection helps identify specific problematic files.
BUSINESS IMPACT: Failed files cannot contribute to Golden Path validation.
DEBUG VALUE: Individual results help prioritize fix order.

NEXT ACTION: Address individual file issues in order of business criticality.
"""

        # Log detailed results for debugging
        print(individual_report)

        # Fail test if success rate is below acceptable threshold
        assert success_rate >= 95.0, f"Individual file collection success rate too low: {success_rate:.1f}%\n{individual_report}"

    def test_unified_test_runner_mission_critical_category(self):
        """
        Validate that unified test runner can handle mission-critical category.

        Tests integration with the SSOT unified test runner for mission-critical tests.
        """
        # Path to unified test runner
        test_runner_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "unified_test_runner.py"
        )

        # Verify test runner exists
        assert os.path.exists(test_runner_path), f"Unified test runner not found: {test_runner_path}"

        # Test collection through unified test runner (dry run)
        try:
            result = subprocess.run([
                sys.executable, test_runner_path,
                "--category", "mission_critical",
                "--collect-only",
                "--dry-run"
            ], capture_output=True, text=True, timeout=60, cwd=os.path.dirname(test_runner_path))

            runner_success = result.returncode == 0
            stdout_output = result.stdout
            stderr_output = result.stderr

        except subprocess.TimeoutExpired:
            runner_success = False
            stdout_output = ""
            stderr_output = "Test runner collection timed out after 60 seconds"

        except Exception as e:
            runner_success = False
            stdout_output = ""
            stderr_output = f"Test runner execution failed: {str(e)}"

        runner_report = f"""
UNIFIED TEST RUNNER MISSION CRITICAL VALIDATION
==============================================

Test Runner Path: {test_runner_path}
Collection Success: {'✅ SUCCESS' if runner_success else '❌ FAILED'}
Return Code: {result.returncode if 'result' in locals() else 'N/A'}

STDOUT OUTPUT:
{stdout_output[:500]}...

STDERR OUTPUT:
{stderr_output[:500]}...

ANALYSIS: Unified test runner must successfully collect mission-critical tests.
BUSINESS IMPACT: Test runner integration required for automated validation.
SSOT COMPLIANCE: Mission-critical tests must work with SSOT test infrastructure.

NEXT ACTION: Fix issues preventing unified test runner mission-critical collection.
"""

        print(runner_report)

        # Assert test runner can handle mission-critical category
        assert runner_success, f"Unified test runner failed for mission-critical category\n{runner_report}"

    def _collect_tests_with_pytest(self, test_directory: str) -> Dict:
        """Helper method to collect tests using pytest and analyze results."""
        try:
            # Use pytest collection API
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                test_directory,
                "--collect-only",
                "-q"
            ], capture_output=True, text=True, timeout=120)

            # Count files and analyze output
            test_files = glob.glob(os.path.join(test_directory, "**", "*.py"), recursive=True)
            total_files = len(test_files)

            # Parse pytest output for collection results
            stdout_lines = result.stdout.split('\n')
            stderr_lines = result.stderr.split('\n')

            # Count collected items
            collected_items = len([line for line in stdout_lines if '::' in line])
            collected_files = len(set(line.split('::')[0] for line in stdout_lines if '::' in line))

            # Identify errors and warnings
            errors = []
            warnings = []

            for line in stderr_lines:
                if 'ERROR' in line.upper():
                    errors.append({
                        'type': 'COLLECTION_ERROR',
                        'file': 'Unknown',
                        'message': line
                    })
                elif 'WARNING' in line.upper():
                    warnings.append({
                        'type': 'COLLECTION_WARNING',
                        'file': 'Unknown',
                        'message': line
                    })

            return {
                'total_files': total_files,
                'collected_files': collected_files,
                'collected_items': collected_items,
                'errors': errors,
                'warnings': warnings,
                'return_code': result.returncode
            }

        except Exception as e:
            return {
                'total_files': 0,
                'collected_files': 0,
                'collected_items': 0,
                'errors': [{'type': 'EXECUTION_ERROR', 'file': 'pytest', 'message': str(e)}],
                'warnings': [],
                'return_code': -1
            }

    def _collect_single_file(self, file_path: str) -> Dict:
        """Helper method to test collection of a single file."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                file_path,
                "--collect-only",
                "-q"
            ], capture_output=True, text=True, timeout=30)

            success = result.returncode == 0
            collected_items = len([line for line in result.stdout.split('\n') if '::' in line])

            return {
                'file': os.path.relpath(file_path),
                'success': success,
                'collected_items': collected_items,
                'error_type': 'NONE' if success else 'COLLECTION_FAILED',
                'error_message': result.stderr if not success else '',
                'return_code': result.returncode
            }

        except Exception as e:
            return {
                'file': os.path.relpath(file_path),
                'success': False,
                'collected_items': 0,
                'error_type': 'EXECUTION_ERROR',
                'error_message': str(e),
                'return_code': -1
            }


if __name__ == "__main__":
    # SSOT Test Execution: Use unified test runner
    # python tests/unified_test_runner.py --category infrastructure
    pytest.main([__file__, "-v"])