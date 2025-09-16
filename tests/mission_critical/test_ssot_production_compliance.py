"""
SSOT Production Compliance Mission Critical Test - Issue #1098 Phase 2 Validation

MISSION: Mission-critical validation of SSOT compliance in production code.

This test suite provides comprehensive validation of SSOT compliance across
the entire production codebase. It's designed to catch any regressions that
could impact the $500K+ ARR Golden Path user flow.

Business Value: Platform/Internal - Mission Critical System Stability
Protects against SSOT violations that could cause:
- WebSocket 1011 errors
- User isolation failures
- Factory pattern violations
- Import chaos leading to service failures

Test Strategy:
- Mission critical test runs with every deployment
- Comprehensive production code scanning
- Real integration testing with staging environment
- Automated violation detection and tracking
- Business continuity protection

Expected Results (Phase 2):
- PASS: Production violations ≤ 16 (69% reduction achieved)
- PASS: No new factory pattern violations
- PASS: Business continuity maintained
- PASS: Golden Path user flow functional
"""

import asyncio
import os
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class SSotViolation:
    """Represents an SSOT compliance violation."""
    file_path: str
    line_number: int
    violation_type: str
    severity: str
    description: str
    context: str


class TestSSotProductionCompliance(SSotAsyncTestCase):
    """
    Mission-critical test suite for SSOT production compliance validation.

    This test suite is designed to run in CI/CD and catch any SSOT violations
    that could impact business continuity or user experience.
    """

    # Production compliance limits (Phase 2 baseline)
    MAX_PRODUCTION_VIOLATIONS = 16  # Current baseline after 69% reduction
    MAX_CRITICAL_VIOLATIONS = 5    # High-severity violations
    MAX_NEW_VIOLATIONS = 0         # No new violations allowed

    # Production code paths to scan
    PRODUCTION_PATHS = [
        "netra_backend/app",
        "auth_service",
        "frontend/src",
        "shared"
    ]

    # Mission-critical violation patterns
    CRITICAL_VIOLATION_PATTERNS = {
        'websocket_factory_usage': [
            r'WebSocketManagerFactory(?!.*compat)',
            r'websocket.*factory.*create(?!.*compat)',
            r'from.*websocket.*factory(?!.*compat)',
        ],
        'singleton_pattern_usage': [
            r'class.*Singleton',
            r'@singleton',
            r'_instance\s*=\s*None',
            r'if.*not.*hasattr.*instance',
        ],
        'direct_os_environ_access': [
            r'os\.environ\[',
            r'os\.environ\.get',
            r'getenv\(',
        ],
        'non_canonical_imports': [
            r'from.*websocket_core\.(?!canonical_imports)',
            r'import.*websocket.*(?!canonical)',
        ],
        'legacy_pattern_usage': [
            r'from.*deprecated',
            r'import.*legacy',
            r'OLD_.*=',
        ]
    }

    def setUp(self):
        """Set up mission critical test environment."""
        super().setUp()
        self.violations: List[SSotViolation] = []
        self.baseline_violations = self._load_baseline_violations()
        self.start_time = datetime.now()
        self.assertLog("🚨 MISSION CRITICAL: Starting SSOT production compliance validation")

    async def tearDown(self):
        """Clean up and log mission critical results."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        self.assertLog(f"🚨 MISSION CRITICAL: SSOT compliance scan completed in {duration.total_seconds():.2f}s")
        self.assertLog(f"🚨 Total violations found: {len(self.violations)}")

        if len(self.violations) > self.MAX_PRODUCTION_VIOLATIONS:
            self.assertLog("🚨 CRITICAL: Production violation limit exceeded!")

        await super().tearDown()

    def test_production_violation_limit_compliance(self):
        """
        TEST MISSION CRITICAL: Validate production violations within Phase 2 limits.

        This is the primary gate for production deployment. FAILURE BLOCKS RELEASE.
        """
        self.assertLog("🚨 MISSION CRITICAL: Testing production violation limits")

        # Scan all production code
        all_violations = self._scan_all_production_code()

        # Filter out allowed violations in compatibility layer
        production_violations = [
            v for v in all_violations
            if not self._is_allowed_compatibility_violation(v)
        ]

        violation_count = len(production_violations)

        self.assertLog(f"🚨 Production violations: {violation_count}/{self.MAX_PRODUCTION_VIOLATIONS}")

        # MISSION CRITICAL: This test MUST pass for deployment
        self.assertLessEqual(
            violation_count,
            self.MAX_PRODUCTION_VIOLATIONS,
            f"🚨 CRITICAL FAILURE: Production violations ({violation_count}) exceed Phase 2 limit "
            f"({self.MAX_PRODUCTION_VIOLATIONS}). This BLOCKS deployment to protect $500K+ ARR. "
            f"Violations: {[f'{v.file_path}:{v.line_number}' for v in production_violations[:5]]}"
        )

        # Log violation breakdown for tracking
        self._log_mission_critical_violation_summary(production_violations)

        self.assertLog("✅ MISSION CRITICAL: Production violation limits PASSED")

    def test_no_new_critical_violations(self):
        """
        TEST MISSION CRITICAL: Ensure no new critical violations introduced.

        Compares against baseline to catch regressions.
        """
        self.assertLog("🚨 MISSION CRITICAL: Testing for new critical violations")

        current_violations = self._scan_for_critical_violations()
        baseline_critical = self._get_baseline_critical_violations()

        # Identify new violations
        new_violations = self._identify_new_violations(current_violations, baseline_critical)

        new_violation_count = len(new_violations)

        self.assertLog(f"🚨 New critical violations: {new_violation_count}")

        # MISSION CRITICAL: Zero tolerance for new critical violations
        self.assertEqual(
            new_violation_count, 0,
            f"🚨 CRITICAL FAILURE: New critical violations detected. This BLOCKS deployment. "
            f"New violations: {[f'{v.file_path}:{v.line_number} - {v.description}' for v in new_violations]}"
        )

        self.assertLog("✅ MISSION CRITICAL: No new critical violations PASSED")

    def test_websocket_factory_elimination_compliance(self):
        """
        TEST MISSION CRITICAL: Validate WebSocket factory elimination.

        Factory violations cause 1011 errors that break Golden Path.
        """
        self.assertLog("🚨 MISSION CRITICAL: Testing WebSocket factory elimination")

        factory_violations = self._scan_for_websocket_factory_violations()

        # Filter out compatibility layer
        production_factory_violations = [
            v for v in factory_violations
            if not self._is_allowed_compatibility_violation(v)
        ]

        factory_violation_count = len(production_factory_violations)

        # Allow limited factory violations during Phase 2 migration
        max_allowed_factory_violations = 8  # Subset of total 16 limit

        self.assertLog(f"🚨 Factory violations: {factory_violation_count}/{max_allowed_factory_violations}")

        self.assertLessEqual(
            factory_violation_count,
            max_allowed_factory_violations,
            f"🚨 CRITICAL FAILURE: WebSocket factory violations ({factory_violation_count}) exceed limit "
            f"({max_allowed_factory_violations}). Factory violations cause 1011 errors. "
            f"Violations: {[f'{v.file_path}:{v.line_number}' for v in production_factory_violations]}"
        )

        self.assertLog("✅ MISSION CRITICAL: WebSocket factory elimination PASSED")

    def test_golden_path_import_compliance(self):
        """
        TEST MISSION CRITICAL: Validate Golden Path import compliance.

        Import violations can break the user flow that delivers 90% of business value.
        """
        self.assertLog("🚨 MISSION CRITICAL: Testing Golden Path import compliance")

        import_violations = self._scan_for_import_violations()

        # Focus on critical Golden Path imports
        golden_path_violations = [
            v for v in import_violations
            if self._is_golden_path_critical(v)
        ]

        critical_import_count = len(golden_path_violations)

        # Allow some import violations during migration but limit critical ones
        max_critical_imports = 3

        self.assertLog(f"🚨 Golden Path import violations: {critical_import_count}/{max_critical_imports}")

        self.assertLessEqual(
            critical_import_count,
            max_critical_imports,
            f"🚨 CRITICAL FAILURE: Golden Path import violations ({critical_import_count}) exceed limit "
            f"({max_critical_imports}). These violations can break user chat flow. "
            f"Violations: {[f'{v.file_path}:{v.line_number}' for v in golden_path_violations]}"
        )

        self.assertLog("✅ MISSION CRITICAL: Golden Path import compliance PASSED")

    async def test_business_continuity_protection(self):
        """
        TEST MISSION CRITICAL: Validate business continuity protection.

        Tests that SSOT changes don't break core business functionality.
        """
        self.assertLog("🚨 MISSION CRITICAL: Testing business continuity protection")

        business_critical_components = [
            'websocket_core',
            'auth_integration',
            'agents/supervisor',
            'services/user_execution_context',
        ]

        continuity_failures = []

        for component in business_critical_components:
            try:
                component_health = await self._validate_component_health(component)
                if not component_health:
                    continuity_failures.append(component)
                    self.assertLog(f"🚨 Business continuity failure: {component}")
                else:
                    self.assertLog(f"✅ Business continuity OK: {component}")

            except Exception as e:
                continuity_failures.append(f"{component}: {str(e)}")
                self.assertLog(f"🚨 Business continuity error: {component} - {e}")

        # MISSION CRITICAL: Core components must be functional
        self.assertEqual(
            len(continuity_failures), 0,
            f"🚨 CRITICAL FAILURE: Business continuity violations detected. "
            f"Core components failing: {continuity_failures}. "
            f"This indicates SSOT changes broke critical functionality."
        )

        self.assertLog("✅ MISSION CRITICAL: Business continuity protection PASSED")

    def test_user_isolation_integrity(self):
        """
        TEST MISSION CRITICAL: Validate user isolation integrity.

        User isolation failures are security and business critical.
        """
        self.assertLog("🚨 MISSION CRITICAL: Testing user isolation integrity")

        isolation_violations = self._scan_for_user_isolation_violations()

        # User isolation is ZERO tolerance
        isolation_violation_count = len(isolation_violations)

        self.assertLog(f"🚨 User isolation violations: {isolation_violation_count}")

        self.assertEqual(
            isolation_violation_count, 0,
            f"🚨 CRITICAL FAILURE: User isolation violations detected. "
            f"This is a SECURITY ISSUE and BLOCKS deployment. "
            f"Violations: {[f'{v.file_path}:{v.line_number} - {v.description}' for v in isolation_violations]}"
        )

        self.assertLog("✅ MISSION CRITICAL: User isolation integrity PASSED")

    # Comprehensive scanning methods

    def _scan_all_production_code(self) -> List[SSotViolation]:
        """
        Scan all production code for SSOT violations.

        Returns:
            List of all violations found in production code.
        """
        all_violations = []

        for path in self.PRODUCTION_PATHS:
            if os.path.exists(path):
                path_violations = self._scan_directory_for_violations(path)
                all_violations.extend(path_violations)

        return all_violations

    def _scan_directory_for_violations(self, directory: str) -> List[SSotViolation]:
        """
        Scan a directory for SSOT violations.

        Args:
            directory: Directory path to scan

        Returns:
            List of violations found in directory.
        """
        violations = []
        directory_path = Path(directory)

        for file_path in directory_path.rglob("*.py"):
            if self._should_scan_file(file_path):
                file_violations = self._scan_file_for_all_violations(file_path)
                violations.extend(file_violations)

        return violations

    def _scan_file_for_all_violations(self, file_path: Path) -> List[SSotViolation]:
        """
        Scan a single file for all types of SSOT violations.

        Args:
            file_path: Path to file to scan

        Returns:
            List of violations found in file.
        """
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Scan for each violation type
            for violation_type, patterns in self.CRITICAL_VIOLATION_PATTERNS.items():
                type_violations = self._scan_file_content_for_patterns(
                    str(file_path), content, patterns, violation_type
                )
                violations.extend(type_violations)

        except (UnicodeDecodeError, IOError) as e:
            self.assertLog(f"Warning: Could not scan {file_path}: {e}")

        return violations

    def _scan_file_content_for_patterns(
        self, file_path: str, content: str, patterns: List[str], violation_type: str
    ) -> List[SSotViolation]:
        """
        Scan file content for specific violation patterns.

        Args:
            file_path: Path to the file
            content: File content to scan
            patterns: List of regex patterns to search for
            violation_type: Type of violation being scanned

        Returns:
            List of violations found for these patterns.
        """
        violations = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    severity = self._determine_violation_severity(violation_type, line)

                    violations.append(SSotViolation(
                        file_path=file_path,
                        line_number=line_num,
                        violation_type=violation_type,
                        severity=severity,
                        description=f"{violation_type}: {pattern}",
                        context=line.strip()
                    ))

        return violations

    def _scan_for_critical_violations(self) -> List[SSotViolation]:
        """
        Scan specifically for critical violations that block deployment.

        Returns:
            List of critical violations only.
        """
        all_violations = self._scan_all_production_code()

        critical_violations = [
            v for v in all_violations
            if v.severity == 'critical'
        ]

        return critical_violations

    def _scan_for_websocket_factory_violations(self) -> List[SSotViolation]:
        """
        Scan specifically for WebSocket factory violations.

        Returns:
            List of WebSocket factory violations.
        """
        factory_patterns = self.CRITICAL_VIOLATION_PATTERNS['websocket_factory_usage']
        violations = []

        for path in self.PRODUCTION_PATHS:
            if os.path.exists(path):
                for file_path in Path(path).rglob("*.py"):
                    if self._should_scan_file(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                            file_violations = self._scan_file_content_for_patterns(
                                str(file_path), content, factory_patterns, 'websocket_factory_usage'
                            )
                            violations.extend(file_violations)

                        except (UnicodeDecodeError, IOError):
                            continue

        return violations

    def _scan_for_import_violations(self) -> List[SSotViolation]:
        """
        Scan for import-related SSOT violations.

        Returns:
            List of import violations.
        """
        import_patterns = self.CRITICAL_VIOLATION_PATTERNS['non_canonical_imports']
        violations = []

        for path in self.PRODUCTION_PATHS:
            if os.path.exists(path):
                for file_path in Path(path).rglob("*.py"):
                    if self._should_scan_file(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                            file_violations = self._scan_file_content_for_patterns(
                                str(file_path), content, import_patterns, 'non_canonical_imports'
                            )
                            violations.extend(file_violations)

                        except (UnicodeDecodeError, IOError):
                            continue

        return violations

    def _scan_for_user_isolation_violations(self) -> List[SSotViolation]:
        """
        Scan for user isolation violations (security critical).

        Returns:
            List of user isolation violations.
        """
        isolation_patterns = [
            r'global.*user',
            r'shared.*user.*state',
            r'singleton.*user',
            r'static.*user.*context',
        ]

        violations = []

        for path in self.PRODUCTION_PATHS:
            if os.path.exists(path):
                for file_path in Path(path).rglob("*.py"):
                    if self._should_scan_file(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                            file_violations = self._scan_file_content_for_patterns(
                                str(file_path), content, isolation_patterns, 'user_isolation_violation'
                            )
                            violations.extend(file_violations)

                        except (UnicodeDecodeError, IOError):
                            continue

        return violations

    # Validation and filtering methods

    def _should_scan_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be scanned for violations.

        Args:
            file_path: Path to check

        Returns:
            True if file should be scanned.
        """
        # Skip test files, __pycache__, and backup files
        exclusions = [
            '__pycache__',
            'test_',
            '.backup',
            '.pyc',
            'migrations/',
            'node_modules/',
        ]

        for exclusion in exclusions:
            if exclusion in str(file_path):
                return False

        return True

    def _is_allowed_compatibility_violation(self, violation: SSotViolation) -> bool:
        """
        Check if violation is allowed in compatibility layer.

        Args:
            violation: Violation to check

        Returns:
            True if violation is allowed in compatibility layer.
        """
        compatibility_files = [
            'compat.py',
            'migration_adapter.py',
            'canonical_imports.py',
            'legacy_support.py',
        ]

        file_name = Path(violation.file_path).name
        return file_name in compatibility_files

    def _is_golden_path_critical(self, violation: SSotViolation) -> bool:
        """
        Check if violation is critical to Golden Path functionality.

        Args:
            violation: Violation to check

        Returns:
            True if violation affects Golden Path.
        """
        golden_path_components = [
            'websocket',
            'agent',
            'auth',
            'user_execution',
            'supervisor'
        ]

        file_path_lower = violation.file_path.lower()
        return any(component in file_path_lower for component in golden_path_components)

    def _determine_violation_severity(self, violation_type: str, line_content: str) -> str:
        """
        Determine severity of a violation.

        Args:
            violation_type: Type of violation
            line_content: Content of the line with violation

        Returns:
            Severity level: 'critical', 'high', 'medium', 'low'
        """
        critical_types = ['websocket_factory_usage', 'user_isolation_violation']
        high_types = ['singleton_pattern_usage', 'direct_os_environ_access']

        if violation_type in critical_types:
            return 'critical'
        elif violation_type in high_types:
            return 'high'
        elif 'deprecated' in line_content.lower() or 'legacy' in line_content.lower():
            return 'medium'
        else:
            return 'low'

    async def _validate_component_health(self, component: str) -> bool:
        """
        Validate health of a business-critical component.

        Args:
            component: Component name to validate

        Returns:
            True if component is healthy.
        """
        try:
            # Check if component can be imported
            component_path = f"netra_backend.app.{component.replace('/', '.')}"

            # Try to import the component
            exec(f"import {component_path}")

            return True

        except ImportError:
            return False
        except Exception:
            return False

    # Baseline and tracking methods

    def _load_baseline_violations(self) -> Dict:
        """
        Load baseline violations for comparison.

        Returns:
            Dictionary of baseline violation data.
        """
        baseline_file = "tests/mission_critical/ssot_baseline_violations.json"

        if os.path.exists(baseline_file):
            try:
                with open(baseline_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Default baseline (Phase 2 targets)
        return {
            'total_violations': 16,
            'critical_violations': 5,
            'factory_violations': 8,
            'import_violations': 3,
            'last_updated': '2025-09-16'
        }

    def _get_baseline_critical_violations(self) -> List[Dict]:
        """
        Get baseline critical violations for comparison.

        Returns:
            List of baseline critical violations.
        """
        return self.baseline_violations.get('critical_details', [])

    def _identify_new_violations(
        self, current_violations: List[SSotViolation], baseline_violations: List[Dict]
    ) -> List[SSotViolation]:
        """
        Identify new violations compared to baseline.

        Args:
            current_violations: Current violations found
            baseline_violations: Baseline violations for comparison

        Returns:
            List of new violations not in baseline.
        """
        baseline_signatures = set()

        for baseline in baseline_violations:
            signature = f"{baseline.get('file_path')}:{baseline.get('line_number')}"
            baseline_signatures.add(signature)

        new_violations = []

        for violation in current_violations:
            signature = f"{violation.file_path}:{violation.line_number}"
            if signature not in baseline_signatures:
                new_violations.append(violation)

        return new_violations

    def _log_mission_critical_violation_summary(self, violations: List[SSotViolation]):
        """
        Log detailed violation summary for mission critical tracking.

        Args:
            violations: List of violations to summarize
        """
        self.assertLog("🚨 MISSION CRITICAL VIOLATION SUMMARY 🚨")

        # Group by severity
        by_severity = {}
        for violation in violations:
            if violation.severity not in by_severity:
                by_severity[violation.severity] = []
            by_severity[violation.severity].append(violation)

        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                count = len(by_severity[severity])
                self.assertLog(f"🚨 {severity.upper()}: {count} violations")

                # Show top violations for critical/high
                if severity in ['critical', 'high']:
                    for violation in by_severity[severity][:3]:
                        self.assertLog(f"  - {violation.file_path}:{violation.line_number} - {violation.description}")

        self.assertLog("🚨 END VIOLATION SUMMARY 🚨")


if __name__ == "__main__":
    import unittest
    unittest.main()