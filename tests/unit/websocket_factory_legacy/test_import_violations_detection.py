"""
Test suite to EXPOSE WebSocket Factory Import Violations - Issue #1098 Phase 2

This test suite systematically scans for factory import violations across the
entire codebase. Based on initial analysis, we expect to find 692+ import
violations across 348+ files, proving the factory migration was never completed.

Expected Results:
- FAIL with 692+ import violations detected
- FAIL across 348+ files with factory imports
- Expose systematic false completion pattern
- Provide concrete violation inventory for remediation

Test Strategy: Systematic scanning to expose the full scope of false completion.
"""

import os
import re
import unittest
from pathlib import Path
from typing import List, Dict, Tuple


class TestWebSocketFactoryImportViolationsDetection(unittest.TestCase):
    """
    Tests to detect and expose WebSocket factory import violations.

    CRITICAL: These tests are DESIGNED TO FAIL initially with specific violation counts.
    They provide systematic evidence of the false completion pattern.
    """

    def setUp(self):
        """Set up test environment with scanning configuration."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.factory_import_patterns = [
            r"from.*websocket.*factory",
            r"import.*websocket.*factory",
            r"from.*\.factory.*websocket",
            r"import.*\.factory.*websocket",
            r"from.*websocket_manager_factory",
            r"import.*websocket_manager_factory",
            r"from.*websocket_bridge_factory",
            r"import.*websocket_bridge_factory"
        ]
        self.excluded_directories = {
            ".git", "__pycache__", ".pytest_cache", "node_modules",
            "venv", ".venv", "build", "dist", ".mypy_cache"
        }

    def scan_file_for_factory_imports(self, file_path: Path) -> List[Tuple[int, str]]:
        """
        Scan a single file for factory import violations.

        Returns:
            List of (line_number, line_content) tuples for violations
        """
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line_stripped = line.strip()
                    for pattern in self.factory_import_patterns:
                        if re.search(pattern, line_stripped, re.IGNORECASE):
                            violations.append((line_num, line_stripped))
                            break  # Count each line only once
        except (UnicodeDecodeError, PermissionError):
            # Skip binary files or files we can't read
            pass

        return violations

    def scan_codebase_for_factory_imports(self) -> Dict[str, List[Tuple[int, str]]]:
        """
        Systematically scan entire codebase for factory import violations.

        Returns:
            Dictionary mapping file_path -> list of violations
        """
        violations_by_file = {}

        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excluded_directories]

            for file in files:
                if file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                    file_path = Path(root) / file
                    violations = self.scan_file_for_factory_imports(file_path)

                    if violations:
                        relative_path = str(file_path.relative_to(self.project_root))
                        violations_by_file[relative_path] = violations

        return violations_by_file

    def test_no_factory_import_violations_exist(self):
        """
        Test that NO factory import violations exist in the codebase.

        EXPECTED: FAIL with 692+ violations across 348+ files
        EVIDENCE: Systematic proof of false completion
        """
        violations_by_file = self.scan_codebase_for_factory_imports()

        total_violations = sum(len(violations) for violations in violations_by_file.values())
        files_with_violations = len(violations_by_file)

        # This assertion will FAIL, exposing the systematic violation pattern
        self.assertEqual(
            total_violations, 0,
            f"SYSTEMATIC VIOLATION: {total_violations} factory import violations found "
            f"across {files_with_violations} files. This proves Issue #1098 false completion. "
            f"Expected: 0 violations. Actual: {total_violations} violations in {files_with_violations} files. "
            f"Files with violations: {list(violations_by_file.keys())[:10]}..."
        )

    def test_specific_violation_thresholds_exceeded(self):
        """
        Test specific violation thresholds to prove systematic false completion.

        EXPECTED: FAIL - Thresholds significantly exceeded
        EVIDENCE: Quantitative proof of incomplete migration
        """
        violations_by_file = self.scan_codebase_for_factory_imports()

        total_violations = sum(len(violations) for violations in violations_by_file.values())
        files_with_violations = len(violations_by_file)

        # Test violation count threshold (expecting 692+ based on analysis)
        self.assertLess(
            total_violations, 100,
            f"VIOLATION THRESHOLD EXCEEDED: {total_violations} factory import violations found. "
            f"This far exceeds acceptable limits and proves systematic false completion. "
            f"Expected: < 100 violations. Actual: {total_violations} violations."
        )

        # Test file count threshold (expecting 348+ based on analysis)
        self.assertLess(
            files_with_violations, 20,
            f"FILE THRESHOLD EXCEEDED: {files_with_violations} files contain factory imports. "
            f"This proves widespread incomplete migration across the codebase. "
            f"Expected: < 20 files. Actual: {files_with_violations} files with violations."
        )

    def test_critical_files_have_no_factory_imports(self):
        """
        Test that critical production files have no factory imports.

        EXPECTED: FAIL - Critical files still have factory imports
        EVIDENCE: Proves business-critical violations
        """
        critical_files = [
            "netra_backend/app/dependencies.py",
            "netra_backend/app/routes/websocket.py",
            "netra_backend/app/websocket_core/manager.py"
        ]

        violations_in_critical_files = {}

        for critical_file in critical_files:
            file_path = self.project_root / critical_file
            if file_path.exists():
                violations = self.scan_file_for_factory_imports(file_path)
                if violations:
                    violations_in_critical_files[critical_file] = violations

        # This assertion will FAIL for critical files with violations
        self.assertEqual(
            len(violations_in_critical_files), 0,
            f"CRITICAL FILE VIOLATIONS: {len(violations_in_critical_files)} critical files "
            f"contain factory imports. This proves business-critical false completion. "
            f"Files: {list(violations_in_critical_files.keys())}. "
            f"Expected: 0 critical violations. Actual: {len(violations_in_critical_files)} critical violations."
        )

    def test_test_files_have_no_factory_imports(self):
        """
        Test that test files have no factory imports (except this test suite).

        EXPECTED: FAIL - Many test files still import factories
        EVIDENCE: Proves test infrastructure not migrated
        """
        violations_by_file = self.scan_codebase_for_factory_imports()

        # Filter for test files (excluding this test suite which is intentionally scanning)
        test_file_violations = {}
        current_test_file = str(Path(__file__).relative_to(self.project_root))

        for file_path, violations in violations_by_file.items():
            if ("test_" in file_path or "/tests/" in file_path) and file_path != current_test_file:
                # Exclude our own test files that are designed to scan for violations
                if "websocket_factory_legacy" not in file_path:
                    test_file_violations[file_path] = violations

        test_violations_count = sum(len(violations) for violations in test_file_violations.values())

        # This assertion will FAIL, proving test infrastructure not migrated
        self.assertEqual(
            test_violations_count, 0,
            f"TEST INFRASTRUCTURE VIOLATIONS: {test_violations_count} factory import violations "
            f"found in {len(test_file_violations)} test files. This proves test infrastructure "
            f"not migrated to SSOT patterns. Files: {list(test_file_violations.keys())[:5]}... "
            f"Expected: 0 test violations. Actual: {test_violations_count} test violations."
        )

    def test_detailed_violation_inventory_for_remediation(self):
        """
        Generate detailed violation inventory for remediation planning.

        EXPECTED: FAIL with comprehensive violation breakdown
        EVIDENCE: Complete roadmap for actual remediation
        """
        violations_by_file = self.scan_codebase_for_factory_imports()

        # Categorize violations by directory/component
        violation_categories = {}
        for file_path, violations in violations_by_file.items():
            # Extract top-level directory as category
            category = file_path.split('/')[0] if '/' in file_path else 'root'
            if category not in violation_categories:
                violation_categories[category] = {'files': 0, 'violations': 0}
            violation_categories[category]['files'] += 1
            violation_categories[category]['violations'] += len(violations)

        total_violations = sum(len(violations) for violations in violations_by_file.values())

        # Create detailed breakdown for remediation
        breakdown = []
        for category, stats in violation_categories.items():
            breakdown.append(f"{category}: {stats['violations']} violations in {stats['files']} files")

        # This assertion will FAIL, providing comprehensive remediation roadmap
        self.assertEqual(
            total_violations, 0,
            f"COMPREHENSIVE VIOLATION INVENTORY: {total_violations} total violations "
            f"across {len(violation_categories)} components. "
            f"Breakdown: {'; '.join(breakdown)}. "
            f"This provides complete roadmap for actual Issue #1098 remediation. "
            f"Expected: 0 violations. Actual: {total_violations} violations requiring remediation."
        )

    def test_specific_import_patterns_detected(self):
        """
        Test detection of specific factory import patterns.

        EXPECTED: FAIL with specific pattern counts
        EVIDENCE: Granular violation analysis for targeted remediation
        """
        violations_by_file = self.scan_codebase_for_factory_imports()

        # Count violations by pattern type
        pattern_counts = {pattern: 0 for pattern in self.factory_import_patterns}

        for file_violations in violations_by_file.values():
            for line_num, line_content in file_violations:
                for pattern in self.factory_import_patterns:
                    if re.search(pattern, line_content, re.IGNORECASE):
                        pattern_counts[pattern] += 1

        total_pattern_violations = sum(pattern_counts.values())

        # Create pattern breakdown
        pattern_breakdown = [f"{pattern}: {count}" for pattern, count in pattern_counts.items() if count > 0]

        # This assertion will FAIL, providing pattern-specific remediation guidance
        self.assertEqual(
            total_pattern_violations, 0,
            f"PATTERN-SPECIFIC VIOLATIONS: {total_pattern_violations} violations by pattern. "
            f"Breakdown: {'; '.join(pattern_breakdown)}. "
            f"This provides targeted remediation guidance for each import pattern. "
            f"Expected: 0 pattern violations. Actual: {total_pattern_violations} pattern violations."
        )


if __name__ == "__main__":
    print("=" * 80)
    print("WEBSOCKET FACTORY IMPORT VIOLATIONS DETECTION - ISSUE #1098 PHASE 2")
    print("=" * 80)
    print("CRITICAL: These tests are DESIGNED TO FAIL with specific violation counts")
    print("PURPOSE: Systematic exposure of factory import violations")
    print("EXPECTED: FAIL with 692+ violations across 348+ files")
    print("OUTCOME: Comprehensive violation inventory for remediation")
    print("=" * 80)

    unittest.main(verbosity=2)