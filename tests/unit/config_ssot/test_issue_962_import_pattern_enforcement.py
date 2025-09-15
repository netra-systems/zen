"""
UNIT TEST: Issue #962 Configuration Import Pattern Enforcement (P0 SSOT Violation)

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Revenue Protection
- Business Goal: Eliminate configuration import fragmentation causing auth failures
- Value Impact: Protects $500K+ ARR Golden Path by ensuring consistent config management
- Strategic Impact: Enforces SSOT compliance to prevent authentication cascade failures

CRITICAL MISSION: Issue #962 Configuration Import Fragmentation - 55 Files Using Deprecated Imports

This test suite validates that all 55 deprecated configuration import files migrate to SSOT
configuration imports. Tests are designed to:

1. **INITIALLY FAIL**: Detect deprecated `get_unified_config` imports across codebase
2. **VALIDATE REMEDIATION**: Confirm all files use SSOT `get_config` import pattern
3. **BUSINESS VALUE PROTECTION**: Ensure Golden Path authentication flows work reliably
4. **PREVENT REGRESSION**: Block future use of deprecated configuration import patterns

EXPECTED TEST BEHAVIOR:
- **PHASE 0-1 (CURRENT)**: Tests FAIL demonstrating 55 deprecated import violations exist
- **PHASE 4 (AFTER REMEDIATION)**: Tests PASS proving SSOT compliance achieved
- **ONGOING**: Tests prevent regression by failing if deprecated patterns reintroduced

CRITICAL BUSINESS IMPACT:
Multiple configuration managers cause authentication failures that block the Golden Path
user flow, directly impacting $500K+ ARR. SSOT compliance eliminates race conditions
and ensures reliable user authentication across all services.

This test supports the Configuration Import Fragmentation remediation for Issue #962.
"""

import pytest
import ast
import os
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import importlib.util

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestIssue962ImportPatternEnforcement(SSotBaseTestCase, unittest.TestCase):
    """
    Unit tests to enforce SSOT configuration import patterns for Issue #962.

    These tests validate the migration from deprecated configuration imports to
    SSOT configuration imports, protecting $500K+ ARR Golden Path functionality.
    """

    def setUp(self):
        """Set up test environment with import tracking."""
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.deprecated_imports: List[Tuple[str, str]] = []
        self.ssot_imports: List[Tuple[str, str]] = []
        self.violation_files: Set[str] = set()
        self.compliant_files: Set[str] = set()

        # Critical import patterns for Issue #962
        self.deprecated_patterns = [
            "from netra_backend.app.core.configuration.base import get_unified_config",
            "from netra_backend.app.core.configuration.base import UnifiedConfigurationManager",
            "from netra_backend.app.core.configuration import get_unified_config",
        ]

        self.ssot_patterns = [
            "from netra_backend.app.config import get_config",
        ]

        self.critical_production_files = [
            # Core authentication files that MUST use SSOT imports
            "netra_backend/app/auth_integration/auth.py",
            "netra_backend/app/core/websocket_cors.py",
            "netra_backend/app/db/database_manager.py",
            "netra_backend/app/agents/supervisor_agent_modern.py",
            "netra_backend/app/websocket_core/manager.py",
        ]

    def test_no_deprecated_get_unified_config_imports(self):
        """
        TEST: Validate no deprecated get_unified_config imports exist in codebase

        EXPECTED BEHAVIOR:
        - PHASE 0-1 (CURRENT): FAILS - 55 deprecated imports found across codebase
        - PHASE 4 (REMEDIATED): PASSES - Zero deprecated imports remain

        BUSINESS IMPACT:
        Deprecated imports cause multiple configuration managers, leading to authentication
        race conditions that block Golden Path user flows ($500K+ ARR at risk).
        """
        print(f"\n=== Issue #962: Scanning codebase for deprecated configuration imports ===")

        # Scan entire codebase for deprecated imports
        self._scan_codebase_for_import_patterns()

        # Log findings for debugging
        print(f"Found {len(self.deprecated_imports)} deprecated import occurrences")
        print(f"Found {len(self.ssot_imports)} SSOT import occurrences")
        print(f"Files with violations: {len(self.violation_files)}")

        # Report specific violations
        if self.deprecated_imports:
            print("\n--- DEPRECATED IMPORTS FOUND (VIOLATIONS) ---")
            for file_path, import_line in self.deprecated_imports[:10]:  # Show first 10
                rel_path = os.path.relpath(file_path, self.codebase_root)
                print(f"VIOLATION: {rel_path} -> {import_line}")

            if len(self.deprecated_imports) > 10:
                print(f"... and {len(self.deprecated_imports) - 10} more violations")

        # CRITICAL ASSERTION: Should FAIL initially showing violations exist
        violation_count = len(self.deprecated_imports)
        expected_violations = 55  # From Issue #962 specification

        self.assertEqual(
            violation_count, 0,
            f"ISSUE #962 SSOT VIOLATION: Found {violation_count} deprecated configuration imports. "
            f"Expected: 0 (after remediation). "
            f"All files must use SSOT import: 'from netra_backend.app.config import get_config'. "
            f"Files with violations: {list(self.violation_files)[:5]}..."
        )

    def test_production_files_use_ssot_imports(self):
        """
        TEST: Validate critical production files use SSOT configuration imports

        EXPECTED BEHAVIOR:
        - PHASE 0-1 (CURRENT): FAILS - Critical files using deprecated imports
        - PHASE 4 (REMEDIATED): PASSES - All critical files use SSOT imports

        BUSINESS IMPACT:
        Critical production files using deprecated imports directly cause authentication
        failures in Golden Path user flows, blocking revenue-generating functionality.
        """
        print(f"\n=== Issue #962: Validating critical production files use SSOT imports ===")

        critical_violations = []
        critical_compliant = []

        for file_path in self.critical_production_files:
            full_path = self.codebase_root / file_path
            if not full_path.exists():
                print(f"WARNING: Critical file does not exist: {file_path}")
                continue

            has_deprecated, has_ssot = self._check_file_import_patterns(full_path)

            if has_deprecated:
                critical_violations.append(file_path)
                print(f"CRITICAL VIOLATION: {file_path} uses deprecated imports")
            elif has_ssot:
                critical_compliant.append(file_path)
                print(f"COMPLIANT: {file_path} uses SSOT imports")
            else:
                print(f"NO CONFIG IMPORTS: {file_path}")

        # CRITICAL ASSERTION: Should FAIL initially for critical files
        self.assertEqual(
            len(critical_violations), 0,
            f"ISSUE #962 CRITICAL VIOLATION: {len(critical_violations)} critical production files "
            f"still use deprecated configuration imports, blocking Golden Path user flows. "
            f"Critical violations: {critical_violations}. "
            f"All critical files must use: 'from netra_backend.app.config import get_config'"
        )

        # Validate we have some SSOT usage in critical files
        self.assertGreater(
            len(critical_compliant), 0,
            "Expected at least some critical production files to use SSOT configuration imports"
        )

    def test_all_import_patterns_consistent(self):
        """
        TEST: Comprehensive validation of import pattern consistency across codebase

        EXPECTED BEHAVIOR:
        - PHASE 0-1 (CURRENT): FAILS - Mixed deprecated and SSOT imports causing inconsistency
        - PHASE 4 (REMEDIATED): PASSES - 100% SSOT import pattern consistency

        BUSINESS IMPACT:
        Mixed import patterns cause configuration inconsistencies that create unpredictable
        authentication behavior, directly threatening Golden Path reliability.
        """
        print(f"\n=== Issue #962: Comprehensive import pattern consistency validation ===")

        self._scan_codebase_for_import_patterns()

        # Calculate consistency metrics
        total_config_imports = len(self.deprecated_imports) + len(self.ssot_imports)
        ssot_percentage = (len(self.ssot_imports) / total_config_imports * 100) if total_config_imports > 0 else 0

        print(f"Configuration import analysis:")
        print(f"- Total config imports found: {total_config_imports}")
        print(f"- SSOT imports: {len(self.ssot_imports)} ({ssot_percentage:.1f}%)")
        print(f"- Deprecated imports: {len(self.deprecated_imports)} ({100 - ssot_percentage:.1f}%)")
        print(f"- Files with violations: {len(self.violation_files)}")
        print(f"- Files compliant: {len(self.compliant_files)}")

        # Generate detailed violation report for remediation
        if self.violation_files:
            print(f"\n--- ISSUE #962 REMEDIATION TARGETS ---")
            for file_path in sorted(self.violation_files):
                rel_path = os.path.relpath(file_path, self.codebase_root)
                print(f"REMEDIATE: {rel_path}")

        # CRITICAL BUSINESS ASSERTIONS

        # 1. Zero deprecated imports (should FAIL initially, PASS after remediation)
        self.assertEqual(
            len(self.deprecated_imports), 0,
            f"ISSUE #962 SSOT VIOLATION: Found {len(self.deprecated_imports)} deprecated imports. "
            f"Expected: 0. All configuration imports must use SSOT pattern: "
            f"'from netra_backend.app.config import get_config'"
        )

        # 2. 100% SSOT compliance (should FAIL initially, PASS after remediation)
        self.assertEqual(
            ssot_percentage, 100.0,
            f"ISSUE #962 CONSISTENCY VIOLATION: Only {ssot_percentage:.1f}% SSOT compliance achieved. "
            f"Expected: 100%. Golden Path requires consistent configuration imports."
        )

        # 3. Minimum expected SSOT usage (realistic business expectation)
        self.assertGreater(
            len(self.ssot_imports), 10,
            f"Expected significant SSOT configuration import usage across codebase. "
            f"Found only {len(self.ssot_imports)} SSOT imports."
        )

    def _scan_codebase_for_import_patterns(self):
        """Scan entire codebase for configuration import patterns."""

        # Reset tracking lists
        self.deprecated_imports.clear()
        self.ssot_imports.clear()
        self.violation_files.clear()
        self.compliant_files.clear()

        # Define scan directories (exclude test files for production analysis)
        scan_dirs = [
            self.codebase_root / "netra_backend" / "app",
            self.codebase_root / "auth_service",
            self.codebase_root / "shared",
            self.codebase_root / "dev_launcher",
        ]

        for scan_dir in scan_dirs:
            if scan_dir.exists():
                self._scan_directory_for_imports(scan_dir)

    def _scan_directory_for_imports(self, directory: Path):
        """Recursively scan directory for configuration import patterns."""

        for py_file in directory.rglob("*.py"):
            # Skip __pycache__ and test files for production analysis
            if "__pycache__" in str(py_file) or "test" in str(py_file).lower():
                continue

            self._check_file_import_patterns(py_file)

    def _check_file_import_patterns(self, file_path: Path) -> Tuple[bool, bool]:
        """
        Check specific file for import patterns.

        Returns:
            Tuple[bool, bool]: (has_deprecated_imports, has_ssot_imports)
        """
        has_deprecated = False
        has_ssot = False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for deprecated import patterns
            for pattern in self.deprecated_patterns:
                if pattern in content:
                    has_deprecated = True
                    self.deprecated_imports.append((str(file_path), pattern))
                    self.violation_files.add(str(file_path))

            # Check for SSOT import patterns
            for pattern in self.ssot_patterns:
                if pattern in content:
                    has_ssot = True
                    self.ssot_imports.append((str(file_path), pattern))
                    if not has_deprecated:  # Only mark compliant if no deprecated imports
                        self.compliant_files.add(str(file_path))

        except (OSError, UnicodeDecodeError) as e:
            print(f"WARNING: Could not read file {file_path}: {e}")

        return has_deprecated, has_ssot


if __name__ == "__main__":
    # Execute tests with detailed output for Issue #962 debugging
    unittest.main(verbosity=2)