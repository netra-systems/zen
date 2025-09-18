"""
WebSocket Factory Elimination Unit Test - Issue #1098 Phase 2 Validation

MISSION: Validate WebSocket factory legacy removal and SSOT compliance.

This test suite scans production code for factory pattern violations and validates
that Phase 2 production remediation (53 -> 16 violations, 69% reduction) is complete.

Business Value: Platform/Internal - System Stability & SSOT Compliance
Ensures clean architecture and prevents factory pattern violations from causing
the 1011 WebSocket errors that impact $500K+ ARR Golden Path.

Test Strategy:
- Unit tests scan netra_backend/app production code (no external dependencies)
- Tests PASS when violations are within acceptable limits (≤16 remaining)
- Tests FAIL when new factory violations are introduced
- Automated tracking of remaining violation counts

Expected Results (Phase 2):
- PASS: Current violation count ≤ 16 (69% reduction achieved)
- FAIL: Any increase above current baseline
- Track: Progress toward zero violations goal
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class FactoryViolation:
    """Represents a factory pattern violation found in code."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    context: str


class TestWebSocketFactoryElimination(SSotBaseTestCase):
    """
    Unit test suite validating WebSocket factory legacy removal.

    Tests production code scanning for factory violations without external dependencies.
    Validates Phase 2 SSOT compliance requirements.
    """

    PRODUCTION_CODE_PATH = "netra_backend/app"
    PHASE_2_VIOLATION_LIMIT = 16  # Current baseline after 69% reduction

    # Factory patterns that should be eliminated
    FACTORY_VIOLATION_PATTERNS = [
        r'WebSocketManagerFactory(?!.*compat)',  # Exclude compat layer
        r'websocket.*factory.*create',
        r'create.*websocket.*factory',
        r'WebSocketFactory(?!.*Protocol)',  # Exclude protocols/interfaces
        r'class.*Factory.*WebSocket',
        r'def.*create.*websocket.*manager.*\(',
        r'from.*factory.*import.*websocket',
        r'import.*websocket.*factory',
    ]

    # Legacy import patterns that should be removed
    LEGACY_IMPORT_PATTERNS = [
        r'from.*websocket_core\.legacy',
        r'from.*deprecated.*websocket',
        r'import.*websocket.*deprecated',
        r'from.*websocket.*old',
    ]

    # Files that are allowed to have factory references (compatibility layer)
    ALLOWED_FACTORY_FILES = {
        'websocket_manager_factory_compat.py',
        'migration_adapter.py',
        'canonical_imports.py',
        'migration_utility.py',
    }

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.violations: List[FactoryViolation] = []
        self.production_path = Path(self.PRODUCTION_CODE_PATH)
        self.assertLog("Starting WebSocket factory elimination validation")

    def test_production_factory_references_within_limit(self):
        """
        Test that production factory references are within Phase 2 limits.

        PASS: ≤16 violations (current baseline)
        FAIL: >16 violations (regression detected)
        """
        violations = self._scan_production_files_for_factory_violations()
        violation_count = len(violations)

        self.assertLog(f"Found {violation_count} factory violations in production code")

        # Phase 2 compliance check
        self.assertLessEqual(
            violation_count,
            self.PHASE_2_VIOLATION_LIMIT,
            f"Factory violations ({violation_count}) exceed Phase 2 limit ({self.PHASE_2_VIOLATION_LIMIT}). "
            f"This indicates regression in SSOT compliance. "
            f"Current violations: {[v.file_path for v in violations]}"
        )

        # Log detailed violation breakdown for tracking
        if violations:
            self._log_violation_details(violations)

        self.assertLog(f"CHECK Phase 2 compliance: {violation_count}/{self.PHASE_2_VIOLATION_LIMIT} violations")

    def test_no_new_websocket_factory_classes(self):
        """
        Test that no new WebSocketFactory classes exist in production.

        Scans for class definitions that implement factory patterns.
        """
        factory_classes = self._scan_for_factory_class_definitions()

        # Filter out allowed compatibility classes
        prohibited_classes = [
            cls for cls in factory_classes
            if not self._is_allowed_factory_file(cls['file_path'])
        ]

        self.assertEqual(
            len(prohibited_classes), 0,
            f"Found prohibited factory classes in production: {prohibited_classes}. "
            f"All factory classes should be eliminated or moved to compatibility layer."
        )

        self.assertLog(f"CHECK No prohibited factory classes found in production code")

    def test_canonical_import_compliance(self):
        """
        Test that code uses canonical import paths from SSOT imports.

        Validates that WebSocket manager access follows SSOT patterns.
        """
        import_violations = self._scan_for_non_canonical_imports()

        # Allow some imports during transition period but track them
        max_allowed_non_canonical = 50  # Generous limit during migration

        self.assertLessEqual(
            len(import_violations),
            max_allowed_non_canonical,
            f"Too many non-canonical imports ({len(import_violations)} > {max_allowed_non_canonical}). "
            f"Files should use canonical imports from websocket_core.canonical_imports"
        )

        if import_violations:
            self.assertLog(f"Non-canonical imports found: {len(import_violations)} files need updates")

        self.assertLog(f"CHECK Import compliance: {len(import_violations)}/{max_allowed_non_canonical} non-canonical imports")

    def test_legacy_pattern_elimination(self):
        """
        Test that legacy patterns are eliminated from production code.

        Scans for deprecated import patterns and usage.
        """
        legacy_violations = self._scan_for_legacy_patterns()

        self.assertEqual(
            len(legacy_violations), 0,
            f"Found legacy pattern usage in production: {[v.file_path for v in legacy_violations]}. "
            f"All legacy patterns should be eliminated in Phase 2."
        )

        self.assertLog(f"CHECK No legacy patterns found in production code")

    def test_factory_method_elimination(self):
        """
        Test that factory methods are eliminated in favor of direct instantiation.

        Scans for factory method patterns that should be removed.
        """
        factory_methods = self._scan_for_factory_methods()

        # Filter out allowed methods in compatibility layer
        prohibited_methods = [
            method for method in factory_methods
            if not self._is_allowed_factory_file(method['file_path'])
        ]

        # Allow some factory methods during transition but limit them
        max_allowed_factory_methods = 25  # Current baseline tracking

        self.assertLessEqual(
            len(prohibited_methods),
            max_allowed_factory_methods,
            f"Too many factory methods ({len(prohibited_methods)} > {max_allowed_factory_methods}) "
            f"found in production code. Factory methods should be eliminated."
        )

        self.assertLog(f"CHECK Factory methods: {len(prohibited_methods)}/{max_allowed_factory_methods} remaining")

    def _scan_production_files_for_factory_violations(self) -> List[FactoryViolation]:
        """
        Scan production files for factory pattern violations.

        Returns:
            List of FactoryViolation objects found in production code.
        """
        violations = []

        for file_path in self._get_python_files():
            if self._is_allowed_factory_file(str(file_path)):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                file_violations = self._scan_file_for_violations(str(file_path), content)
                violations.extend(file_violations)

            except (UnicodeDecodeError, IOError) as e:
                self.assertLog(f"Warning: Could not read {file_path}: {e}")

        return violations

    def _scan_file_for_violations(self, file_path: str, content: str) -> List[FactoryViolation]:
        """
        Scan a single file for factory violations.

        Args:
            file_path: Path to the file being scanned
            content: File content to scan

        Returns:
            List of violations found in the file.
        """
        violations = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()

            for pattern in self.FACTORY_VIOLATION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(FactoryViolation(
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        violation_type="factory_pattern",
                        context=f"Pattern: {pattern}"
                    ))

            for pattern in self.LEGACY_IMPORT_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(FactoryViolation(
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        violation_type="legacy_import",
                        context=f"Legacy pattern: {pattern}"
                    ))

        return violations

    def _scan_for_factory_class_definitions(self) -> List[Dict]:
        """
        Scan for factory class definitions using AST parsing.

        Returns:
            List of factory class definitions found.
        """
        factory_classes = []

        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name.lower()
                        if 'factory' in class_name and 'websocket' in class_name:
                            factory_classes.append({
                                'file_path': str(file_path),
                                'class_name': node.name,
                                'line_number': node.lineno
                            })

            except (SyntaxError, UnicodeDecodeError, IOError):
                # Skip files that can't be parsed
                continue

        return factory_classes

    def _scan_for_non_canonical_imports(self) -> List[Dict]:
        """
        Scan for non-canonical import patterns.

        Returns:
            List of files using non-canonical imports.
        """
        violations = []
        canonical_pattern = r'from.*websocket_core\.canonical_imports'

        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if file imports WebSocket functionality
                has_websocket_imports = re.search(
                    r'import.*websocket|from.*websocket', content, re.IGNORECASE
                )
                has_canonical_import = re.search(canonical_pattern, content)

                if has_websocket_imports and not has_canonical_import:
                    # Check if it's using allowed patterns
                    if not self._is_allowed_factory_file(str(file_path)):
                        violations.append({
                            'file_path': str(file_path),
                            'issue': 'non_canonical_import'
                        })

            except (UnicodeDecodeError, IOError):
                continue

        return violations

    def _scan_for_legacy_patterns(self) -> List[FactoryViolation]:
        """
        Scan for legacy pattern usage.

        Returns:
            List of legacy pattern violations.
        """
        violations = []

        for file_path in self._get_python_files():
            if self._is_allowed_factory_file(str(file_path)):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern in self.LEGACY_IMPORT_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(FactoryViolation(
                                file_path=str(file_path),
                                line_number=line_num,
                                line_content=line.strip(),
                                violation_type="legacy_pattern",
                                context=f"Legacy: {pattern}"
                            ))

            except (UnicodeDecodeError, IOError):
                continue

        return violations

    def _scan_for_factory_methods(self) -> List[Dict]:
        """
        Scan for factory method definitions.

        Returns:
            List of factory methods found.
        """
        factory_methods = []

        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name.lower()
                        if ('create' in func_name and 'websocket' in func_name) or \
                           ('factory' in func_name and 'websocket' in func_name):
                            factory_methods.append({
                                'file_path': str(file_path),
                                'method_name': node.name,
                                'line_number': node.lineno
                            })

            except (SyntaxError, UnicodeDecodeError, IOError):
                continue

        return factory_methods

    def _get_python_files(self) -> List[Path]:
        """
        Get all Python files in production code directory.

        Returns:
            List of Python file paths to scan.
        """
        python_files = []

        if not self.production_path.exists():
            return python_files

        for file_path in self.production_path.rglob("*.py"):
            # Skip test files and __pycache__
            if '__pycache__' in str(file_path) or 'test_' in file_path.name:
                continue
            python_files.append(file_path)

        return python_files

    def _is_allowed_factory_file(self, file_path: str) -> bool:
        """
        Check if file is allowed to have factory references.

        Args:
            file_path: Path to check

        Returns:
            True if file is in allowed compatibility layer.
        """
        file_name = Path(file_path).name
        return file_name in self.ALLOWED_FACTORY_FILES

    def _log_violation_details(self, violations: List[FactoryViolation]):
        """
        Log detailed violation information for tracking.

        Args:
            violations: List of violations to log
        """
        self.assertLog("=== Factory Violation Details ===")

        # Group by violation type
        by_type = {}
        for violation in violations:
            if violation.violation_type not in by_type:
                by_type[violation.violation_type] = []
            by_type[violation.violation_type].append(violation)

        for violation_type, type_violations in by_type.items():
            self.assertLog(f"{violation_type}: {len(type_violations)} violations")
            for v in type_violations[:3]:  # Show first 3 of each type
                self.assertLog(f"  {v.file_path}:{v.line_number} - {v.line_content[:60]}...")

        self.assertLog("=== End Violation Details ===")


if __name__ == "__main__":
    import unittest
    unittest.main()