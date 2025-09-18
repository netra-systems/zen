#!/usr/bin/env python3
"""
Test Suite Corruption Scanner - Issue #817

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Stability - Validate test suite integrity
- Value Impact: Ensure test coverage protection for $500K+ ARR functionality
- Strategic Impact: Maintain deployment confidence through comprehensive validation

This test validates the extent of test suite corruption and measures the impact
on business-critical functionality validation.

CRITICAL REQUIREMENTS:
- NO DOCKER DEPENDENCIES (runs unit-style tests only)
- Real file system analysis (not mocked)
- Quantifies business impact of corruption
- Provides actionable metrics for recovery
"""

import os
import re
import sys
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
class CorruptionAnalysis:
    """Analysis results of test suite corruption."""
    total_test_files: int
    corrupted_files: int
    corruption_percentage: float
    corrupted_lines: int
    total_lines_in_corrupted_files: int
    corruption_pattern_count: Dict[str, int]
    mission_critical_affected: List[str]
    business_impact_files: List[str]


class SuiteCorruptionScanner:
    """Scans and analyzes test suite corruption for Issue #817."""

    CORRUPTION_PATTERNS = {
    'removed_syntax_error': r'^',
    'commented_imports': r'^ import',
    'commented_decorators': r'^ @',
    'commented_functions': r'^ (def |async def )',
    'commented_classes': r'^ class '
    }

    MISSION_CRITICAL_PATTERNS = [
        'mission_critical',
        'websocket',
        'agent_events',
        'staging',
        'golden_path'
    ]

    BUSINESS_IMPACT_PATTERNS = [
        'e2e',
        'integration',
        'auth',
        'database',
        'api'
    ]

    def __init__(self, project_root: str = None):
        """Initialize scanner with project root."""
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..')
        )
        self.test_directory = os.path.join(self.project_root, 'tests')

    def scan_test_files(self) -> List[Path]:
        """Find all Python test files."""
        test_files = []
        for root, dirs, files in os.walk(self.test_directory):
            # Skip .venv and __pycache__ directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.startswith('test') and file.endswith('.py'):
                    test_files.append(Path(root) / file)

        return test_files

    def analyze_file_corruption(self, file_path: Path) -> Dict[str, Any]:
        """Analyze corruption in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, IOError) as e:
            return {
                'error': str(e),
                'total_lines': 0,
                'corrupted_lines': 0,
                'pattern_counts': {},
                'is_corrupted': False
            }

        pattern_counts = {}
        corrupted_lines = 0

        for line in lines:
            for pattern_name, pattern in self.CORRUPTION_PATTERNS.items():
                if re.match(pattern, line):
                    pattern_counts[pattern_name] = pattern_counts.get(pattern_name, 0) + 1
                    corrupted_lines += 1
                    break

        is_corrupted = corrupted_lines > 0

        return {
            'total_lines': len(lines),
            'corrupted_lines': corrupted_lines,
            'pattern_counts': pattern_counts,
            'is_corrupted': is_corrupted,
            'error': None
        }

    def categorize_file(self, file_path: Path) -> Dict[str, bool]:
        """Categorize file by business importance."""
        file_str = str(file_path).lower()

        return {
            'mission_critical': any(pattern in file_str for pattern in self.MISSION_CRITICAL_PATTERNS),
            'business_impact': any(pattern in file_str for pattern in self.BUSINESS_IMPACT_PATTERNS),
            'infrastructure': 'infrastructure' in file_str or 'framework' in file_str,
            'unit_test': '/unit/' in file_str or 'unit_' in file_str,
            'integration_test': '/integration/' in file_str or 'integration_' in file_str,
            'e2e_test': '/e2e/' in file_str or 'e2e_' in file_str
        }

    def analyze_corruption(self) -> CorruptionAnalysis:
        """Perform comprehensive corruption analysis."""
        test_files = self.scan_test_files()

        corrupted_files = []
        total_corrupted_lines = 0
        total_lines_in_corrupted = 0
        overall_pattern_counts = {}
        mission_critical_affected = []
        business_impact_files = []

        for file_path in test_files:
            analysis = self.analyze_file_corruption(file_path)

            if analysis['is_corrupted']:
                corrupted_files.append(str(file_path))
                total_corrupted_lines += analysis['corrupted_lines']
                total_lines_in_corrupted += analysis['total_lines']

                # Aggregate pattern counts
                for pattern, count in analysis['pattern_counts'].items():
                    overall_pattern_counts[pattern] = overall_pattern_counts.get(pattern, 0) + count

                # Categorize file
                categories = self.categorize_file(file_path)
                if categories['mission_critical']:
                    mission_critical_affected.append(str(file_path))
                if categories['business_impact']:
                    business_impact_files.append(str(file_path))

        corruption_percentage = (len(corrupted_files) / len(test_files)) * 100 if test_files else 0

        return CorruptionAnalysis(
            total_test_files=len(test_files),
            corrupted_files=len(corrupted_files),
            corruption_percentage=corruption_percentage,
            corrupted_lines=total_corrupted_lines,
            total_lines_in_corrupted_files=total_lines_in_corrupted,
            corruption_pattern_count=overall_pattern_counts,
            mission_critical_affected=mission_critical_affected,
            business_impact_files=business_impact_files
        )


class CorruptionScannerTests:
    """Test cases for corruption scanner functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.env = IsolatedEnvironment()
        self.scanner = TestSuiteCorruptionScanner()

    @pytest.mark.unit
    def test_scanner_initialization(self):
        """Test scanner initializes correctly."""
        assert self.scanner.project_root is not None
        assert self.scanner.test_directory.endswith('tests')
        assert os.path.exists(self.scanner.test_directory)

    @pytest.mark.unit
    def test_corruption_pattern_detection(self):
        """Test corruption patterns are correctly identified."""
        patterns = self.scanner.CORRUPTION_PATTERNS

        test_lines = [
    " import asyncio",
    " @pytest.mark.asyncio",
    " def test_function():",
    " async def async_test():",
    " class TestClass:",
            "normal import line",
            "regular code"
        ]

        expected_matches = {
            'removed_syntax_error': 5,
            'commented_imports': 1,
            'commented_decorators': 1,
            'commented_functions': 2,
            'commented_classes': 1
        }

        actual_matches = {pattern: 0 for pattern in patterns.keys()}

        for line in test_lines:
            for pattern_name, pattern_regex in patterns.items():
                if re.match(pattern_regex, line):
                    actual_matches[pattern_name] += 1

        assert actual_matches == expected_matches

    @pytest.mark.unit
    def test_scan_finds_test_files(self):
        """Test scanner finds test files."""
        test_files = self.scanner.scan_test_files()

        assert len(test_files) > 0
        assert all(file.name.startswith('test') for file in test_files)
        assert all(file.suffix == '.py' for file in test_files)

    @pytest.mark.unit
    def test_file_categorization(self):
        """Test file categorization logic."""
        test_cases = [
            ('/tests/mission_critical/test_websocket.py', {'mission_critical': True}),
            ('/tests/e2e/test_user_flow.py', {'business_impact': True, 'e2e_test': True}),
            ('/tests/integration/test_auth.py', {'business_impact': True, 'integration_test': True}),
            ('/tests/unit/test_utils.py', {'unit_test': True})
        ]

        for file_path, expected_flags in test_cases:
            categories = self.scanner.categorize_file(Path(file_path))
            for flag, expected in expected_flags.items():
                assert categories[flag] == expected, f"File {file_path} should have {flag}={expected}"

    @pytest.mark.unit
    @pytest.mark.slow
    def test_comprehensive_corruption_analysis(self):
        """Test comprehensive corruption analysis - MAIN TEST."""
        analysis = self.scanner.analyze_corruption()

        # Validate analysis structure
        assert isinstance(analysis.total_test_files, int)
        assert isinstance(analysis.corrupted_files, int)
        assert isinstance(analysis.corruption_percentage, float)
        assert isinstance(analysis.corrupted_lines, int)
        assert isinstance(analysis.corruption_pattern_count, dict)
        assert isinstance(analysis.mission_critical_affected, list)
        assert isinstance(analysis.business_impact_files, list)

        # Business impact assertions
        assert analysis.total_test_files > 0, "Should find test files"

        # Log critical information
        print(f"\n=== CORRUPTION ANALYSIS RESULTS ===")
        print(f"Total test files: {analysis.total_test_files}")
        print(f"Corrupted files: {analysis.corrupted_files}")
        print(f"Corruption percentage: {analysis.corruption_percentage:.1f}%")
        print(f"Corrupted lines: {analysis.corrupted_lines:,}")
        print(f"Total lines in corrupted files: {analysis.total_lines_in_corrupted_files:,}")
        print(f"Mission critical files affected: {len(analysis.mission_critical_affected)}")
        print(f"Business impact files affected: {len(analysis.business_impact_files)}")

        if analysis.corruption_pattern_count:
            print("\nCorruption patterns found:")
            for pattern, count in analysis.corruption_pattern_count.items():
                print(f"  {pattern}: {count:,} occurrences")

        if analysis.mission_critical_affected:
            print(f"\nFirst 5 mission critical files affected:")
            for file_path in analysis.mission_critical_affected[:5]:
                print(f"  {file_path}")

        # CRITICAL BUSINESS IMPACT ASSERTIONS
        if analysis.corruption_percentage > 10:
            pytest.fail(
                f"CRITICAL: {analysis.corruption_percentage:.1f}% of test files corrupted! "
                f"This represents significant loss of validation coverage for $500K+ ARR functionality."
            )

        if analysis.mission_critical_affected:
            pytest.fail(
                f"CRITICAL: {len(analysis.mission_critical_affected)} mission-critical test files affected! "
                f"This compromises validation of core business functionality."
            )

    @pytest.mark.unit
    def test_calculate_business_impact_metrics(self):
        """Calculate and validate business impact metrics."""
        analysis = self.scanner.analyze_corruption()

        # Calculate business impact
        total_files = analysis.total_test_files
        corrupted_files = analysis.corrupted_files
        mission_critical_impact = len(analysis.mission_critical_affected)
        business_impact = len(analysis.business_impact_files)

        # Business risk calculations
        validation_coverage_loss = (corrupted_files / total_files) * 100 if total_files > 0 else 0
        critical_functionality_risk = mission_critical_impact > 0

        print(f"\n=== BUSINESS IMPACT METRICS ===")
        print(f"Validation coverage loss: {validation_coverage_loss:.1f}%")
        print(f"Critical functionality at risk: {critical_functionality_risk}")
        print(f"Mission critical files affected: {mission_critical_impact}")
        print(f"Business impact files affected: {business_impact}")

        # Store metrics for reporting
        self.business_impact_metrics = {
            'validation_coverage_loss_percent': validation_coverage_loss,
            'critical_functionality_at_risk': critical_functionality_risk,
            'mission_critical_files_affected': mission_critical_impact,
            'business_impact_files_affected': business_impact,
            'total_corrupted_files': corrupted_files,
            'total_test_files': total_files
        }

        # Critical thresholds
        assert validation_coverage_loss < 50, (
            f"Unacceptable validation coverage loss: {validation_coverage_loss:.1f}% "
            f"(exceeds 50% threshold)"
        )


if __name__ == "__main__":
    """Run corruption analysis directly."""
    scanner = TestSuiteCorruptionScanner()
    analysis = scanner.analyze_corruption()

    print("=== ISSUE #817 CORRUPTION ANALYSIS ===")
    print(f"Total test files: {analysis.total_test_files:,}")
    print(f"Corrupted files: {analysis.corrupted_files:,}")
    print(f"Corruption percentage: {analysis.corruption_percentage:.1f}%")
    print(f"Lines affected: {analysis.corrupted_lines:,}")
    print(f"Mission critical affected: {len(analysis.mission_critical_affected)}")
    print(f"Business impact files: {len(analysis.business_impact_files)}")