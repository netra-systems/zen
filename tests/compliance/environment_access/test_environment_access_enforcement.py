"""
Compliance Tests for Environment Access SSOT Enforcement - Issue #711

This test suite enforces SSOT patterns and prevents environment access violations.
Tests are designed to be strict enforcement mechanisms for SSOT compliance.

Business Value: Platform/Internal - Architectural Governance & Code Quality
Prevents regression to non-SSOT patterns and enforces architectural standards.

CRITICAL: These tests use SSotBaseTestCase and serve as enforcement mechanisms.
"""

import ast
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEnvironmentAccessEnforcement(SSotBaseTestCase):
    """
    Compliance tests that enforce SSOT environment access patterns.

    These tests act as gates to prevent non-SSOT patterns from being committed
    and enforce architectural compliance across the codebase.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent

        # SSOT enforcement thresholds
        self.max_allowed_violations_per_service = 50  # Temporary threshold during migration
        self.max_allowed_violations_total = 200      # Total system threshold

        # Critical services that must be 100% compliant
        self.critical_services = [
            'shared',
            'test_framework'
        ]

        # Track enforcement metrics
        self.record_metric("enforcement_thresholds_configured", True)

    def test_enforce_no_new_environment_violations(self):
        """
        Enforce that no new environment access violations are introduced.

        This test acts as a regression prevention mechanism during SSOT migration.
        It allows existing violations but prevents new ones from being added.
        """
        current_violations = self._get_current_violations()
        baseline_violations = self._get_baseline_violation_count()

        # Record metrics
        self.record_metric("current_violations", len(current_violations))
        self.record_metric("baseline_violations", baseline_violations)

        # Calculate violation change
        violation_change = len(current_violations) - baseline_violations

        # Log enforcement results
        print(f"\n🛡️ Environment Access Violation Enforcement:")
        print(f"  📊 Current violations: {len(current_violations)}")
        print(f"  📋 Baseline violations: {baseline_violations}")
        print(f"  📈 Change: {violation_change:+d}")

        if violation_change > 0:
            print(f"  🚨 NEW VIOLATIONS DETECTED:")
            new_violations = current_violations[:violation_change]
            for violation in new_violations[:10]:  # Show first 10
                rel_path = str(Path(violation['file']).relative_to(self.project_root))
                print(f"    • {rel_path}:{violation['line']} - {violation['pattern']}")

        # STRICT ENFORCEMENT: No new violations allowed
        assert violation_change <= 0, (
            f"❌ ENFORCEMENT FAILURE: {violation_change} new environment access violations detected! "
            f"New violations prevent SSOT migration progress. "
            f"Use shared.isolated_environment instead of direct os.environ access. "
            f"Issue #711 requires maintaining or reducing violation count during migration."
        )

    def test_enforce_critical_service_compliance(self):
        """
        Enforce 100% SSOT compliance for critical services.

        Critical services (shared, test_framework) must be completely free
        of environment access violations as they provide SSOT utilities.
        """
        critical_service_violations = {}

        for service_name in self.critical_services:
            service_path = self.project_root / service_name
            if not service_path.exists():
                continue

            violations = self._get_service_violations(service_path)
            critical_service_violations[service_name] = violations

            # Record metrics per critical service
            self.record_metric(f"critical_{service_name}_violations", len(violations))

        # Log critical service compliance
        print(f"\n🔒 Critical Service Compliance Enforcement:")
        for service_name, violations in critical_service_violations.items():
            status = "✅ COMPLIANT" if len(violations) == 0 else "❌ VIOLATIONS"
            print(f"  {service_name}: {status} ({len(violations)} violations)")

            if violations:
                print(f"    🚨 Critical violations:")
                for violation in violations[:5]:  # Show first 5
                    rel_path = str(Path(violation['file']).relative_to(self.project_root))
                    print(f"      • {rel_path}:{violation['line']} - {violation['pattern']}")

        # STRICT ENFORCEMENT: Critical services must be 100% compliant
        total_critical_violations = sum(len(v) for v in critical_service_violations.values())

        assert total_critical_violations == 0, (
            f"❌ CRITICAL SERVICE COMPLIANCE FAILURE: "
            f"Found {total_critical_violations} violations in critical services. "
            f"Critical services must be 100% SSOT compliant as they provide utilities to other services. "
            f"Violations in: {[s for s, v in critical_service_violations.items() if v]}"
        )

    def test_enforce_service_violation_thresholds(self):
        """
        Enforce violation count thresholds per service during migration.

        Services must stay within acceptable violation limits while
        migration is in progress to prevent architectural degradation.
        """
        service_violations = {}
        threshold_violations = []

        # Check each service against thresholds
        services = ['netra_backend', 'auth_service', 'frontend', 'scripts', 'tests']
        for service_name in services:
            service_path = self.project_root / service_name
            if not service_path.exists():
                continue

            violations = self._get_service_violations(service_path)
            service_violations[service_name] = violations

            # Check threshold
            if len(violations) > self.max_allowed_violations_per_service:
                threshold_violations.append({
                    'service': service_name,
                    'violations': len(violations),
                    'threshold': self.max_allowed_violations_per_service
                })

            # Record metrics
            self.record_metric(f"{service_name}_violations", len(violations))

        # Log service threshold enforcement
        print(f"\n📏 Service Violation Threshold Enforcement:")
        print(f"  🎯 Threshold per service: {self.max_allowed_violations_per_service}")

        for service_name, violations in service_violations.items():
            violation_count = len(violations)
            status = "✅ WITHIN" if violation_count <= self.max_allowed_violations_per_service else "❌ EXCEEDS"
            print(f"  {service_name}: {violation_count} violations - {status} threshold")

        if threshold_violations:
            print(f"  🚨 Services exceeding thresholds:")
            for threshold_violation in threshold_violations:
                service = threshold_violation['service']
                count = threshold_violation['violations']
                threshold = threshold_violation['threshold']
                excess = count - threshold
                print(f"    • {service}: {count} violations ({excess} over threshold)")

        # ENFORCEMENT: Services must stay within thresholds
        assert len(threshold_violations) == 0, (
            f"❌ SERVICE THRESHOLD COMPLIANCE FAILURE: "
            f"{len(threshold_violations)} services exceed violation thresholds. "
            f"Services must reduce violations during SSOT migration. "
            f"Exceeding services: {[v['service'] for v in threshold_violations]}"
        )

    def test_enforce_total_system_violation_limit(self):
        """
        Enforce total system violation limit during migration.

        The entire system must stay within acceptable total violation
        limits to ensure migration progress and prevent degradation.
        """
        all_violations = self._get_current_violations()
        total_violations = len(all_violations)

        # Record metrics
        self.record_metric("total_system_violations", total_violations)
        self.record_metric("system_violation_limit", self.max_allowed_violations_total)

        # Calculate violation distribution
        service_distribution = defaultdict(int)
        for violation in all_violations:
            service = self._extract_service_from_path(violation['file'])
            service_distribution[service] += 1

        # Log system-wide enforcement
        print(f"\n🌐 System-Wide Violation Limit Enforcement:")
        print(f"  📊 Total violations: {total_violations}")
        print(f"  🎯 System limit: {self.max_allowed_violations_total}")
        print(f"  📈 Utilization: {total_violations / self.max_allowed_violations_total * 100:.1f}%")

        print(f"  📋 Violation distribution by service:")
        for service, count in sorted(service_distribution.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_violations * 100 if total_violations > 0 else 0
            print(f"    • {service}: {count} violations ({percentage:.1f}%)")

        # ENFORCEMENT: Total system must stay within limits
        assert total_violations <= self.max_allowed_violations_total, (
            f"❌ SYSTEM VIOLATION LIMIT EXCEEDED: "
            f"Total violations ({total_violations}) exceed system limit ({self.max_allowed_violations_total}). "
            f"Immediate remediation required to continue SSOT migration. "
            f"Top violating services: {dict(list(service_distribution.items())[:3])}"
        )

    def test_enforce_ssot_import_patterns(self):
        """
        Enforce proper SSOT import patterns across the codebase.

        All files must use proper imports from shared.isolated_environment
        instead of direct os module imports for environment access.
        """
        import_violations = self._get_import_violations()

        # Categorize import violations
        violation_categories = defaultdict(list)
        for violation in import_violations:
            violation_categories[violation['pattern']].append(violation)

        # Record metrics
        self.record_metric("import_violations_total", len(import_violations))
        for pattern, violations in violation_categories.items():
            clean_pattern = re.sub(r'[^a-zA-Z0-9_]', '_', pattern)
            self.record_metric(f"import_violations_{clean_pattern}", len(violations))

        # Log import pattern enforcement
        print(f"\n📦 SSOT Import Pattern Enforcement:")
        print(f"  📊 Total import violations: {len(import_violations)}")

        if violation_categories:
            print(f"  📋 Violations by pattern:")
            for pattern, violations in violation_categories.items():
                print(f"    • {pattern}: {len(violations)} violations")
                for violation in violations[:3]:  # Show first 3
                    rel_path = str(Path(violation['file']).relative_to(self.project_root))
                    print(f"      - {rel_path}:{violation['line']}")

            print(f"\n  ✅ Correct SSOT import patterns:")
            print(f"    • from shared.isolated_environment import IsolatedEnvironment")
            print(f"    • from shared.isolated_environment import get_env")
            print(f"    • Use self.get_env() in test classes")

        # ENFORCEMENT: No incorrect import patterns allowed
        assert len(import_violations) == 0, (
            f"❌ IMPORT PATTERN ENFORCEMENT FAILURE: "
            f"Found {len(import_violations)} incorrect import patterns. "
            f"All environment access must use SSOT imports from shared.isolated_environment. "
            f"Replace direct 'import os' with proper SSOT imports."
        )

    def test_enforce_test_ssot_compliance(self):
        """
        Enforce SSOT compliance specifically in test files.

        Test files must use SSotBaseTestCase environment utilities
        instead of direct environment access to maintain test isolation.
        """
        test_violations = self._get_test_environment_violations()

        # Categorize test violations
        violation_by_test_type = defaultdict(list)
        for violation in test_violations:
            test_type = self._classify_test_file(violation['file'])
            violation_by_test_type[test_type].append(violation)

        # Record metrics
        self.record_metric("test_violations_total", len(test_violations))
        for test_type, violations in violation_by_test_type.items():
            self.record_metric(f"test_violations_{test_type}", len(violations))

        # Log test SSOT enforcement
        print(f"\n🧪 Test SSOT Compliance Enforcement:")
        print(f"  📊 Total test violations: {len(test_violations)}")

        if violation_by_test_type:
            print(f"  📋 Violations by test type:")
            for test_type, violations in violation_by_test_type.items():
                print(f"    • {test_type}: {len(violations)} violations")
                for violation in violations[:2]:  # Show first 2
                    rel_path = str(Path(violation['file']).relative_to(self.project_root))
                    print(f"      - {rel_path}:{violation['line']} - {violation['code'][:60]}...")

            print(f"\n  ✅ Correct test environment patterns:")
            print(f"    • Use self.get_env_var() instead of os.environ")
            print(f"    • Use self.set_env_var() instead of os.environ assignment")
            print(f"    • Use self.temp_env_vars() context manager")

        # ENFORCEMENT: Tests must use SSOT patterns
        assert len(test_violations) == 0, (
            f"❌ TEST SSOT COMPLIANCE FAILURE: "
            f"Found {len(test_violations)} environment violations in test files. "
            f"Tests must use SSotBaseTestCase environment utilities for proper isolation. "
            f"Replace direct os.environ access with self.get_env_var() and self.set_env_var()."
        )

    def _get_current_violations(self) -> List[Dict[str, any]]:
        """Get current environment access violations in the codebase."""
        violations = []

        # Scan for violations
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                file_violations = self._find_violations_in_content(str(py_file), content)
                violations.extend(file_violations)

            except (UnicodeDecodeError, PermissionError):
                continue

        return violations

    def _get_baseline_violation_count(self) -> int:
        """
        Get baseline violation count for regression prevention.

        In a real implementation, this would read from a baseline file
        or database. For testing purposes, we'll use Issue #711 data.
        """
        # Issue #711 reports 5,449 violations across 1,017 files
        # This is our baseline that should not increase
        return 5449

    def _get_service_violations(self, service_path: Path) -> List[Dict[str, any]]:
        """Get violations for a specific service."""
        violations = []

        for py_file in service_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                file_violations = self._find_violations_in_content(str(py_file), content)
                violations.extend(file_violations)

            except (UnicodeDecodeError, PermissionError):
                continue

        return violations

    def _get_import_violations(self) -> List[Dict[str, any]]:
        """Get import pattern violations."""
        violations = []

        # Problematic import patterns
        import_patterns = [
            (r'^import os$', 'import os'),
            (r'^from os import environ$', 'from os import environ'),
            (r'^from os import getenv$', 'from os import getenv'),
            (r'^from os import environ, getenv$', 'from os import environ, getenv'),
        ]

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()

                    for pattern, description in import_patterns:
                        if re.match(pattern, line_stripped):
                            violations.append({
                                'file': str(py_file),
                                'line': line_num,
                                'pattern': description,
                                'code': line_stripped
                            })

            except (UnicodeDecodeError, PermissionError):
                continue

        return violations

    def _get_test_environment_violations(self) -> List[Dict[str, any]]:
        """Get environment violations specifically in test files."""
        violations = []

        # Find test files
        test_patterns = ['test_*.py', '*_test.py', 'tests/*.py']
        test_files = []

        for pattern in test_patterns:
            test_files.extend(self.project_root.rglob(pattern))

        for test_file in test_files:
            if self._should_skip_file(test_file):
                continue

            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                file_violations = self._find_violations_in_content(str(test_file), content)
                violations.extend(file_violations)

            except (UnicodeDecodeError, PermissionError):
                continue

        return violations

    def _find_violations_in_content(self, file_path: str, content: str) -> List[Dict[str, any]]:
        """Find environment access violations in file content."""
        violations = []
        lines = content.split('\n')

        # Violation patterns
        violation_patterns = [
            (r'os\.environ\[', 'os.environ[]'),
            (r'os\.environ\.get\(', 'os.environ.get()'),
            (r'os\.getenv\(', 'os.getenv()'),
            (r'environ\[', 'environ[]'),
            (r'environ\.get\(', 'environ.get()'),
            (r'getenv\(', 'getenv()'),
        ]

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue

            for pattern, description in violation_patterns:
                if re.search(pattern, line):
                    violations.append({
                        'file': file_path,
                        'line': line_num,
                        'pattern': description,
                        'code': line_stripped
                    })
                    break  # Only one violation per line

        return violations

    def _extract_service_from_path(self, file_path: str) -> str:
        """Extract service name from file path."""
        path_parts = Path(file_path).parts

        service_indicators = [
            'netra_backend', 'auth_service', 'frontend', 'shared',
            'analytics_service', 'dev_launcher', 'test_framework',
            'scripts', 'tests'
        ]

        for part in path_parts:
            if part in service_indicators:
                return part

        return 'unknown'

    def _classify_test_file(self, file_path: str) -> str:
        """Classify test file by type."""
        file_path_lower = file_path.lower()

        if '/unit/' in file_path_lower:
            return 'unit'
        elif '/integration/' in file_path_lower:
            return 'integration'
        elif '/e2e/' in file_path_lower:
            return 'e2e'
        elif '/compliance/' in file_path_lower:
            return 'compliance'
        elif 'test_' in file_path_lower or '_test' in file_path_lower:
            return 'general'
        else:
            return 'unknown'

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.pytest_cache',
            'venv',
            'build',
            'dist',
            '.coverage',
            '.mypy_cache',
            'test_environment_violation',  # Skip our own test files
            'test_environment_access_enforcement',  # Skip this test file
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)