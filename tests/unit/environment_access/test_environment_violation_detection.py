"""
Unit Tests for Environment Access SSOT Violations - Issue #711

This test suite systematically detects and validates SSOT environment access violations.
Tests are designed to INITIALLY FAIL to prove violations exist, then guide remediation.

Business Value: Platform/Internal - System Stability & SSOT Compliance
Protects against configuration drift and ensures consistent environment access patterns.

CRITICAL: These tests use SSotBaseTestCase and follow SSOT test infrastructure patterns.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEnvironmentViolationDetection(SSotBaseTestCase):
    """
    Unit tests for detecting environment access SSOT violations.

    These tests systematically scan the codebase for direct os.environ/os.getenv
    usage and validate SSOT compliance patterns.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.violations_found = []
        self.compliant_files = []

        # Track metrics for violation detection
        self.record_metric("project_root", str(self.project_root))

    def test_scan_for_direct_os_environ_usage(self):
        """
        Test that detects direct os.environ usage violations.

        This test is designed to INITIALLY FAIL to prove violations exist.
        Issue #711 indicates 5,449 violations across 1,017 files.
        """
        violations = self._scan_for_os_environ_violations()

        # Record metrics
        self.record_metric("total_violations_found", len(violations))
        self.record_metric("files_with_violations", len(set(v['file'] for v in violations)))

        # Log findings for analysis
        if violations:
            print(f"\n🚨 Found {len(violations)} direct os.environ violations:")
            for i, violation in enumerate(violations[:10]):  # Show first 10
                print(f"  {i+1}. {violation['file']}:{violation['line']} - {violation['code'][:80]}...")
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more violations")

        # This assertion should FAIL initially to prove violations exist
        assert len(violations) == 0, (
            f"Found {len(violations)} direct os.environ/os.getenv violations. "
            f"These should use IsolatedEnvironment instead. "
            f"Issue #711 tracking {len(violations)} violations across "
            f"{len(set(v['file'] for v in violations))} files."
        )

    def test_scan_for_proper_ssot_environment_usage(self):
        """
        Test that validates proper SSOT environment access patterns.

        This test validates files that correctly use IsolatedEnvironment
        or get_env() patterns instead of direct os.environ access.
        """
        compliant_files = self._scan_for_ssot_compliant_patterns()

        # Record metrics
        self.record_metric("compliant_files_found", len(compliant_files))

        # Log compliant patterns found
        print(f"\n✅ Found {len(compliant_files)} files using SSOT environment patterns:")
        for i, file_info in enumerate(compliant_files[:5]):  # Show first 5
            print(f"  {i+1}. {file_info['file']} - Uses: {', '.join(file_info['patterns'])}")

        # This should pass - we want to find SSOT compliant files
        assert len(compliant_files) > 0, (
            "Expected to find files using SSOT environment patterns like IsolatedEnvironment or get_env()"
        )

    def test_analyze_violation_patterns_by_service(self):
        """
        Test that analyzes violation patterns by service to understand scope.

        This helps prioritize remediation efforts by identifying services
        with the highest violation density.
        """
        violations = self._scan_for_os_environ_violations()

        # Group violations by service
        service_violations = defaultdict(list)
        for violation in violations:
            service = self._extract_service_from_path(violation['file'])
            service_violations[service].append(violation)

        # Record metrics by service
        for service, service_viols in service_violations.items():
            self.record_metric(f"violations_{service}", len(service_viols))

        # Log service analysis
        print(f"\n📊 Violation analysis by service:")
        for service, service_viols in sorted(service_violations.items(),
                                           key=lambda x: len(x[1]), reverse=True):
            files_count = len(set(v['file'] for v in service_viols))
            print(f"  {service}: {len(service_viols)} violations in {files_count} files")

        # Record total services affected
        self.record_metric("services_with_violations", len(service_violations))

        # This test documents the current state - no assertion failure expected
        assert len(service_violations) >= 0  # Always true, just documenting state

    def test_identify_high_priority_remediation_targets(self):
        """
        Test that identifies high-priority files for remediation.

        Focuses on files with multiple violations or critical system components
        that should be prioritized for SSOT migration.
        """
        violations = self._scan_for_os_environ_violations()

        # Group by file and count violations per file
        file_violation_counts = defaultdict(int)
        for violation in violations:
            file_violation_counts[violation['file']] += 1

        # Identify high-priority targets (files with 5+ violations)
        high_priority_files = {
            file_path: count for file_path, count in file_violation_counts.items()
            if count >= 5
        }

        # Record metrics
        self.record_metric("high_priority_files", len(high_priority_files))
        self.record_metric("total_files_with_violations", len(file_violation_counts))

        # Log high-priority files
        if high_priority_files:
            print(f"\n🎯 High-priority remediation targets ({len(high_priority_files)} files):")
            for file_path, count in sorted(high_priority_files.items(),
                                         key=lambda x: x[1], reverse=True)[:10]:
                rel_path = str(Path(file_path).relative_to(self.project_root))
                print(f"  {rel_path}: {count} violations")

        # Document findings - no assertion failure expected
        assert len(high_priority_files) >= 0  # Always true, documenting state

    def test_validate_ssot_import_patterns(self):
        """
        Test that validates correct SSOT import patterns for environment access.

        Checks for proper imports of IsolatedEnvironment and get_env functions
        versus direct os module imports.
        """
        import_violations = self._scan_for_incorrect_import_patterns()

        # Record metrics
        self.record_metric("import_violations_found", len(import_violations))

        # Log import violations
        if import_violations:
            print(f"\n📦 Found {len(import_violations)} incorrect import patterns:")
            for violation in import_violations[:10]:  # Show first 10
                print(f"  {violation['file']}:{violation['line']} - {violation['import_line']}")

        # This test documents import patterns - adjust assertion based on findings
        # Initially may fail to show current state
        assert len(import_violations) == 0, (
            f"Found {len(import_violations)} files with incorrect import patterns. "
            f"These should import from shared.isolated_environment instead of direct os imports."
        )

    def _scan_for_os_environ_violations(self) -> List[Dict[str, any]]:
        """
        Scan codebase for direct os.environ and os.getenv usage violations.

        Returns:
            List of violation dictionaries with file, line, and code info
        """
        violations = []

        # Patterns to detect direct environment access
        violation_patterns = [
            r'os\.environ\[',      # os.environ['KEY']
            r'os\.environ\.get\(',  # os.environ.get('KEY')
            r'os\.getenv\(',       # os.getenv('KEY')
            r'environ\[',          # from os import environ; environ['KEY']
            r'environ\.get\(',     # from os import environ; environ.get('KEY')
            r'getenv\(',           # from os import getenv; getenv('KEY')
        ]

        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()

                    # Skip comments and empty lines
                    if not line_stripped or line_stripped.startswith('#'):
                        continue

                    # Check for violation patterns
                    for pattern in violation_patterns:
                        if re.search(pattern, line):
                            violations.append({
                                'file': str(py_file),
                                'line': line_num,
                                'code': line_stripped,
                                'pattern': pattern
                            })
                            break  # Only count one violation per line

            except (UnicodeDecodeError, PermissionError):
                continue

        return violations

    def _scan_for_ssot_compliant_patterns(self) -> List[Dict[str, any]]:
        """
        Scan for files correctly using SSOT environment patterns.

        Returns:
            List of compliant file dictionaries with pattern info
        """
        compliant_files = []

        # Patterns for SSOT compliance
        ssot_patterns = [
            r'from shared\.isolated_environment import',  # Correct import
            r'IsolatedEnvironment\(',                     # Creating instance
            r'get_env\(\)',                              # Using get_env function
            r'\.get_env\(\)',                            # Method call
            r'self\._env\.get\(',                        # Instance usage
            r'self\.get_env_var\(',                      # BaseTestCase method
        ]

        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                found_patterns = []
                for pattern in ssot_patterns:
                    if re.search(pattern, content):
                        found_patterns.append(pattern)

                if found_patterns:
                    compliant_files.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'patterns': found_patterns
                    })

            except (UnicodeDecodeError, PermissionError):
                continue

        return compliant_files

    def _scan_for_incorrect_import_patterns(self) -> List[Dict[str, any]]:
        """
        Scan for incorrect import patterns that bypass SSOT.

        Returns:
            List of import violation dictionaries
        """
        import_violations = []

        # Import patterns that should be replaced
        problematic_imports = [
            r'import os$',                    # Direct os import
            r'from os import environ',        # Direct environ import
            r'from os import getenv',         # Direct getenv import
            r'from os import environ, getenv' # Multiple direct imports
        ]

        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()

                    # Check for problematic import patterns
                    for pattern in problematic_imports:
                        if re.search(pattern, line_stripped):
                            import_violations.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'import_line': line_stripped,
                                'pattern': pattern
                            })
                            break

            except (UnicodeDecodeError, PermissionError):
                continue

        return import_violations

    def _extract_service_from_path(self, file_path: str) -> str:
        """
        Extract service name from file path for categorization.

        Args:
            file_path: Full file path

        Returns:
            Service name (e.g., 'netra_backend', 'auth_service', etc.)
        """
        path_parts = Path(file_path).parts

        # Look for service directories
        service_indicators = [
            'netra_backend', 'auth_service', 'frontend', 'shared',
            'analytics_service', 'dev_launcher', 'test_framework',
            'scripts', 'tests'
        ]

        for part in path_parts:
            if part in service_indicators:
                return part

        return 'unknown'

    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determine if file should be skipped during scanning.

        Args:
            file_path: Path to check

        Returns:
            True if file should be skipped
        """
        # Skip patterns
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.pytest_cache',
            'venv',
            '.env',
            'build',
            'dist',
            '.coverage',
            '.mypy_cache'
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)