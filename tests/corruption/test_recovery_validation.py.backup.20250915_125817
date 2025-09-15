#!/usr/bin/env python3
"""
Recovery Validation Test Suite - Issue #817

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Stability - Validate test suite recovery effectiveness
- Value Impact: Ensure restored test coverage protects $500K+ ARR functionality
- Strategic Impact: Validate deployment confidence restoration

This test validates the effectiveness of emergency recovery PR #851 and ensures
that restored test files provide comprehensive business value coverage.

CRITICAL REQUIREMENTS:
- NO DOCKER DEPENDENCIES (unit-style validation only)
- Validates PR #851 recovery effectiveness
- Tests business-critical functionality restoration
- Measures improvement in test collection rates
"""

import os
import re
import sys
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass

import pytest
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@dataclass
class RecoveryValidation:
    """Recovery validation analysis results."""
    pre_recovery_corrupted_files: int
    post_recovery_corrupted_files: int
    files_recovered: int
    recovery_percentage: float
    syntax_valid_files: int
    syntax_invalid_files: int
    collection_ready_files: int
    business_critical_restored: List[str]
    remaining_issues: List[str]


class RecoveryValidator:
    """Validates effectiveness of Issue #817 recovery efforts."""

    BUSINESS_CRITICAL_FILES = [
        'test_staging_websocket_agent_events.py',
        'test_websocket_agent_events_suite.py',
        'test_golden_path',
        'test_mission_critical',
        'test_e2e_user_flow',
        'test_auth_integration',
        'test_agent_execution'
    ]

    def __init__(self, project_root: str = None):
        """Initialize recovery validator."""
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..')
        )
        self.test_directory = os.path.join(self.project_root, 'tests')

    def find_test_files(self) -> List[Path]:
        """Find all Python test files."""
        test_files = []
        for root, dirs, files in os.walk(self.test_directory):
            # Skip .venv and __pycache__ directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.startswith('test') and file.endswith('.py'):
                    test_files.append(Path(root) / file)

        return test_files

    def check_syntax_validity(self, file_path: Path) -> Dict[str, Any]:
        """Check if a Python file has valid syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Try to parse the AST
            ast.parse(source_code)

            return {
                'syntax_valid': True,
                'error': None,
                'has_removed_syntax_error': 'REMOVED_SYNTAX_ERROR' in source_code
            }

        except SyntaxError as e:
            return {
                'syntax_valid': False,
                'error': f"SyntaxError: {e}",
                'has_removed_syntax_error': None
            }
        except Exception as e:
            return {
                'syntax_valid': False,
                'error': f"Error: {e}",
                'has_removed_syntax_error': None
            }

    def check_test_collection(self, file_path: Path) -> Dict[str, Any]:
        """Check if a test file can be collected by pytest."""
        try:
            # Run pytest --collect-only on this specific file
            cmd = [
                sys.executable, '-m', 'pytest',
                '--collect-only', '-q',
                str(file_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )

            collection_successful = result.returncode == 0
            test_count = 0

            if collection_successful:
                # Count tests in output
                for line in result.stdout.split('\n'):
                    if '::test_' in line or '<Function test_' in line:
                        test_count += 1

            return {
                'collection_successful': collection_successful,
                'test_count': test_count,
                'error': result.stderr if not collection_successful else None,
                'stdout': result.stdout
            }

        except subprocess.TimeoutExpired:
            return {
                'collection_successful': False,
                'test_count': 0,
                'error': "Collection timeout",
                'stdout': ""
            }
        except Exception as e:
            return {
                'collection_successful': False,
                'test_count': 0,
                'error': str(e),
                'stdout': ""
            }

    def check_business_critical_files(self) -> Dict[str, Any]:
        """Check status of business-critical test files."""
        results = {}

        for pattern in self.BUSINESS_CRITICAL_FILES:
            matching_files = []

            # Find files matching the pattern
            for test_file in self.find_test_files():
                if pattern in str(test_file).lower():
                    matching_files.append(test_file)

            results[pattern] = {
                'matching_files': matching_files,
                'status': []
            }

            # Check status of each matching file
            for file_path in matching_files:
                syntax_check = self.check_syntax_validity(file_path)
                collection_check = self.check_test_collection(file_path)

                file_status = {
                    'file_path': str(file_path),
                    'syntax_valid': syntax_check['syntax_valid'],
                    'collection_successful': collection_check['collection_successful'],
                    'test_count': collection_check['test_count'],
                    'has_corruption': syntax_check.get('has_removed_syntax_error', False),
                    'errors': []
                }

                if syntax_check['error']:
                    file_status['errors'].append(f"Syntax: {syntax_check['error']}")
                if collection_check['error']:
                    file_status['errors'].append(f"Collection: {collection_check['error']}")

                results[pattern]['status'].append(file_status)

        return results

    def validate_recovery_effectiveness(self) -> RecoveryValidation:
        """Validate overall recovery effectiveness."""
        test_files = self.find_test_files()

        syntax_valid = 0
        syntax_invalid = 0
        collection_ready = 0
        corrupted_files = 0
        business_critical_restored = []
        remaining_issues = []

        # Check each file
        for file_path in test_files:
            syntax_check = self.check_syntax_validity(file_path)

            if syntax_check['syntax_valid']:
                syntax_valid += 1

                # Test collection for valid files
                collection_check = self.check_test_collection(file_path)
                if collection_check['collection_successful']:
                    collection_ready += 1
            else:
                syntax_invalid += 1
                remaining_issues.append(f"{file_path}: {syntax_check['error']}")

            # Check for corruption
            if syntax_check.get('has_removed_syntax_error', False):
                corrupted_files += 1

        # Check business critical files specifically
        business_critical_status = self.check_business_critical_files()
        for pattern, data in business_critical_status.items():
            for status in data['status']:
                if status['syntax_valid'] and status['collection_successful'] and status['test_count'] > 0:
                    business_critical_restored.append(status['file_path'])

        # Calculate recovery metrics
        total_files = len(test_files)
        recovery_percentage = ((total_files - corrupted_files) / total_files) * 100 if total_files > 0 else 0

        return RecoveryValidation(
            pre_recovery_corrupted_files=365,  # From original issue analysis
            post_recovery_corrupted_files=corrupted_files,
            files_recovered=365 - corrupted_files,
            recovery_percentage=recovery_percentage,
            syntax_valid_files=syntax_valid,
            syntax_invalid_files=syntax_invalid,
            collection_ready_files=collection_ready,
            business_critical_restored=business_critical_restored,
            remaining_issues=remaining_issues[:10]  # Limit to first 10 issues
        )


class TestRecoveryValidation:
    """Test cases for recovery validation."""

    def setup_method(self):
        """Set up test environment."""
        self.env = IsolatedEnvironment()
        self.validator = RecoveryValidator()

    @pytest.mark.unit
    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        assert self.validator.project_root is not None
        assert self.validator.test_directory.endswith('tests')
        assert os.path.exists(self.validator.test_directory)

    @pytest.mark.unit
    def test_syntax_validation_functionality(self):
        """Test syntax validation works correctly."""
        # Create a temporary test file with valid syntax
        test_content_valid = """
def test_example():
    assert True
"""

        # Create a temporary test file with invalid syntax
        test_content_invalid = """
# REMOVED_SYNTAX_ERROR: def test_example():
    # REMOVED_SYNTAX_ERROR: assert True
def incomplete_function(
"""

        # Test valid content
        temp_file = Path(self.validator.project_root) / 'temp_valid_test.py'
        try:
            with open(temp_file, 'w') as f:
                f.write(test_content_valid)

            result = self.validator.check_syntax_validity(temp_file)
            assert result['syntax_valid'] is True
            assert result['error'] is None

        finally:
            if temp_file.exists():
                temp_file.unlink()

        # Test invalid content
        temp_file = Path(self.validator.project_root) / 'temp_invalid_test.py'
        try:
            with open(temp_file, 'w') as f:
                f.write(test_content_invalid)

            result = self.validator.check_syntax_validity(temp_file)
            assert result['syntax_valid'] is False
            assert result['error'] is not None

        finally:
            if temp_file.exists():
                temp_file.unlink()

    @pytest.mark.unit
    def test_business_critical_files_check(self):
        """Test business critical files status check."""
        status = self.validator.check_business_critical_files()

        assert isinstance(status, dict)
        assert len(status) > 0

        # Check structure
        for pattern, data in status.items():
            assert 'matching_files' in data
            assert 'status' in data
            assert isinstance(data['matching_files'], list)
            assert isinstance(data['status'], list)

    @pytest.mark.unit
    @pytest.mark.slow
    def test_comprehensive_recovery_validation(self):
        """Test comprehensive recovery validation - MAIN TEST."""
        validation = self.validator.validate_recovery_effectiveness()

        # Validate structure
        assert isinstance(validation.pre_recovery_corrupted_files, int)
        assert isinstance(validation.post_recovery_corrupted_files, int)
        assert isinstance(validation.files_recovered, int)
        assert isinstance(validation.recovery_percentage, float)
        assert isinstance(validation.syntax_valid_files, int)
        assert isinstance(validation.syntax_invalid_files, int)
        assert isinstance(validation.collection_ready_files, int)
        assert isinstance(validation.business_critical_restored, list)
        assert isinstance(validation.remaining_issues, list)

        # Log recovery results
        print(f"\n=== RECOVERY VALIDATION RESULTS ===")
        print(f"Pre-recovery corrupted files: {validation.pre_recovery_corrupted_files}")
        print(f"Post-recovery corrupted files: {validation.post_recovery_corrupted_files}")
        print(f"Files recovered: {validation.files_recovered}")
        print(f"Recovery percentage: {validation.recovery_percentage:.1f}%")
        print(f"Syntax valid files: {validation.syntax_valid_files}")
        print(f"Syntax invalid files: {validation.syntax_invalid_files}")
        print(f"Collection ready files: {validation.collection_ready_files}")
        print(f"Business critical restored: {len(validation.business_critical_restored)}")

        if validation.business_critical_restored:
            print(f"\nBusiness critical files restored:")
            for file_path in validation.business_critical_restored[:5]:
                print(f"  {file_path}")

        if validation.remaining_issues:
            print(f"\nRemaining issues (first 5):")
            for issue in validation.remaining_issues[:5]:
                print(f"  {issue}")

        # CRITICAL SUCCESS ASSERTIONS
        assert validation.recovery_percentage >= 80, (
            f"Recovery insufficient: {validation.recovery_percentage:.1f}% "
            f"(minimum 80% required for business confidence)"
        )

        assert len(validation.business_critical_restored) > 0, (
            "No business-critical test files restored! "
            "This indicates PR #851 may not be effective."
        )

        assert validation.syntax_valid_files > validation.syntax_invalid_files, (
            f"More invalid files than valid: "
            f"{validation.syntax_invalid_files} invalid vs {validation.syntax_valid_files} valid"
        )

    @pytest.mark.unit
    def test_pr_851_impact_simulation(self):
        """Test simulated impact of PR #851 merge."""
        # This test simulates what happens when PR #851 is merged
        # by checking current state vs expected improvements

        current_status = self.validator.validate_recovery_effectiveness()

        print(f"\n=== PR #851 IMPACT SIMULATION ===")
        print(f"Current corrupted files: {current_status.post_recovery_corrupted_files}")
        print(f"Expected after PR merge: <50 files")
        print(f"Current business critical restored: {len(current_status.business_critical_restored)}")
        print(f"Expected after PR merge: >10 files")

        # Simulate expectations for PR #851
        expected_corruption_reduction = current_status.pre_recovery_corrupted_files * 0.9  # 90% reduction
        expected_business_critical_restoration = 10  # At least 10 business critical files

        improvement_potential = {
            'corruption_reduction_potential': expected_corruption_reduction,
            'business_critical_restoration_potential': expected_business_critical_restoration,
            'current_recovery_rate': current_status.recovery_percentage,
            'expected_recovery_rate_after_pr': 95.0
        }

        print(f"\nImprovement potential:")
        for metric, value in improvement_potential.items():
            print(f"  {metric}: {value}")

        # Store for reporting
        self.pr_impact_simulation = improvement_potential

    @pytest.mark.unit
    def test_test_collection_rate_measurement(self):
        """Measure and validate test collection success rates."""
        test_files = self.validator.find_test_files()

        successful_collections = 0
        failed_collections = 0
        total_test_count = 0

        sample_size = min(50, len(test_files))  # Test sample for performance
        sample_files = test_files[:sample_size]

        print(f"\n=== TEST COLLECTION RATE MEASUREMENT ===")
        print(f"Testing collection rate on {sample_size} files...")

        for file_path in sample_files:
            collection_result = self.validator.check_test_collection(file_path)

            if collection_result['collection_successful']:
                successful_collections += 1
                total_test_count += collection_result['test_count']
            else:
                failed_collections += 1

        collection_success_rate = (successful_collections / sample_size) * 100
        avg_tests_per_file = total_test_count / successful_collections if successful_collections > 0 else 0

        print(f"Collection success rate: {collection_success_rate:.1f}%")
        print(f"Successful collections: {successful_collections}")
        print(f"Failed collections: {failed_collections}")
        print(f"Total tests collected: {total_test_count}")
        print(f"Average tests per file: {avg_tests_per_file:.1f}")

        # BUSINESS IMPACT ASSERTIONS
        assert collection_success_rate >= 70, (
            f"Test collection rate too low: {collection_success_rate:.1f}% "
            f"(minimum 70% required for deployment confidence)"
        )

        assert total_test_count > 0, (
            "No tests collected from sample files! "
            "This indicates systemic collection issues."
        )

        # Store metrics
        self.collection_metrics = {
            'collection_success_rate': collection_success_rate,
            'successful_collections': successful_collections,
            'failed_collections': failed_collections,
            'total_test_count': total_test_count,
            'average_tests_per_file': avg_tests_per_file
        }


if __name__ == "__main__":
    """Run recovery validation directly."""
    validator = RecoveryValidator()
    validation = validator.validate_recovery_effectiveness()

    print("=== ISSUE #817 RECOVERY VALIDATION ===")
    print(f"Files recovered: {validation.files_recovered:,}")
    print(f"Recovery percentage: {validation.recovery_percentage:.1f}%")
    print(f"Business critical restored: {len(validation.business_critical_restored)}")
    print(f"Remaining corrupted: {validation.post_recovery_corrupted_files}")