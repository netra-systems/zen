"""
SSOT Violation Detection Tests for MessageRouter - Issue #1101

CRITICAL PURPOSE: These tests are designed to FAIL initially to prove the existence of
SSOT violations in the MessageRouter implementation. They validate the current fragmentation
problems that need to be resolved.

Test Strategy:
1. Detect multiple MessageRouter class definitions across modules
2. Find interface inconsistencies (register_handler vs add_handler)
3. Validate import path fragmentation
4. Check for proxy vs canonical implementation conflicts

These tests follow the TDD principle: RED (fail) -> GREEN (fix) -> REFACTOR (improve)
Initially, these tests SHOULD FAIL to prove the SSOT violations exist.

Business Value Justification:
- Segment: Platform/Internal - System Stability & Golden Path Protection
- Business Goal: Eliminate MessageRouter SSOT violations preventing staging failures
- Value Impact: Protects $500K+ ARR chat functionality from routing conflicts
- Strategic Impact: Enables safe SSOT consolidation for enterprise-grade reliability
"""

import pytest
import os
import ast
import importlib
import inspect
import unittest
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class MessageRouterSSOTViolationDetectionTests(SSotBaseTestCase, unittest.TestCase):
    """
    CRITICAL SSOT Violation Detection Tests for MessageRouter

    These tests are designed to FAIL initially to prove SSOT violations exist.
    Success metrics: Tests SHOULD FAIL on first run, proving violations.
    """

    def setUp(self):
        """Set up test environment for SSOT violation detection."""
        super().setUp()
        # Initialize paths properly
        current_file = Path(__file__).absolute()
        self.project_root = current_file.parent.parent.parent.parent
        self.backend_root = self.project_root / "netra_backend"

        # Verify paths exist
        if not self.project_root.exists():
            raise RuntimeError(f"Project root not found: {self.project_root}")
        if not self.backend_root.exists():
            raise RuntimeError(f"Backend root not found: {self.backend_root}")

        self.discovered_classes: List[Dict[str, Any]] = []
        self.interface_inconsistencies: List[Dict[str, Any]] = []
        self.import_paths: Set[str] = set()

    def test_detect_multiple_messagerouter_class_definitions(self):
        """
        TEST: Detect multiple MessageRouter class definitions across modules.

        EXPECTED RESULT: This test SHOULD FAIL initially, proving SSOT violations exist.
        If it passes, it means we only have one MessageRouter class (good SSOT compliance).
        If it fails, it proves multiple definitions exist (SSOT violation).
        """
        # Search for all MessageRouter class definitions
        messagerouter_files = self._find_messagerouter_class_definitions()

        # Log findings for diagnostic purposes
        self.logger.info(f"Found MessageRouter classes in {len(messagerouter_files)} files:")
        for file_info in messagerouter_files:
            self.logger.info(f"  - {file_info['file']}: line {file_info['line_number']}")
            self.logger.info(f"    Class signature: {file_info['class_signature']}")

        # CRITICAL: This assertion SHOULD FAIL initially to prove SSOT violations
        # When we have proper SSOT compliance, only ONE MessageRouter should exist
        self.assertEqual(
            len(messagerouter_files), 1,
            f"SSOT VIOLATION: Found {len(messagerouter_files)} MessageRouter class definitions. "
            f"Expected exactly 1 for SSOT compliance. Violations in: "
            f"{[info['file'] for info in messagerouter_files]}"
        )

        # If we reach here, SSOT compliance is achieved
        self.logger.info("✅ SSOT COMPLIANCE: Only one MessageRouter class definition found")

    def test_detect_interface_inconsistencies_register_vs_add_handler(self):
        """
        TEST: Detect interface inconsistencies between register_handler and add_handler methods.

        EXPECTED RESULT: This test SHOULD FAIL initially due to inconsistent interfaces.
        Different MessageRouter classes use different method names for the same functionality.
        """
        # Search for handler registration method patterns
        handler_methods = self._find_handler_registration_methods()

        # Analyze interface consistency
        method_names = set()
        interface_patterns = {}

        for method_info in handler_methods:
            method_name = method_info['method_name']
            method_names.add(method_name)

            if method_name not in interface_patterns:
                interface_patterns[method_name] = []
            interface_patterns[method_name].append(method_info)

        self.logger.info(f"Found handler registration methods: {method_names}")
        for method_name, usages in interface_patterns.items():
            self.logger.info(f"  {method_name}: {len(usages)} usages")

        # CRITICAL: This assertion SHOULD FAIL initially due to interface inconsistencies
        # Proper SSOT should have only ONE method name for handler registration
        self.assertLessEqual(
            len(method_names), 1,
            f"INTERFACE INCONSISTENCY: Found multiple handler registration method names: {method_names}. "
            f"SSOT compliance requires consistent interface. Patterns found: {interface_patterns}"
        )

        # Additional check for specific known inconsistencies
        has_register_handler = 'register_handler' in method_names
        has_add_handler = 'add_handler' in method_names

        if has_register_handler and has_add_handler:
            self.fail(
                f"CRITICAL INTERFACE VIOLATION: Both 'register_handler' and 'add_handler' methods found. "
                f"This creates API confusion and violates SSOT principles. "
                f"Files with register_handler: {[info['file'] for info in interface_patterns.get('register_handler', [])]}, "
                f"Files with add_handler: {[info['file'] for info in interface_patterns.get('add_handler', [])]}"
            )

    def test_validate_import_path_fragmentation(self):
        """
        TEST: Validate MessageRouter import path fragmentation.

        EXPECTED RESULT: This test SHOULD FAIL initially due to multiple import paths.
        Proper SSOT should have ONE canonical import path for MessageRouter.
        """
        # Find all possible import paths for MessageRouter
        import_paths = self._find_messagerouter_import_paths()

        self.logger.info(f"Found MessageRouter import paths: {len(import_paths)}")
        for path in import_paths:
            self.logger.info(f"  - {path}")

        # CRITICAL: This assertion SHOULD FAIL initially due to import fragmentation
        # Proper SSOT should have exactly ONE canonical import path
        self.assertEqual(
            len(import_paths), 1,
            f"IMPORT PATH FRAGMENTATION: Found {len(import_paths)} different import paths for MessageRouter. "
            f"SSOT compliance requires exactly one canonical path. Paths found: {import_paths}"
        )

        # Verify the canonical path is the expected one
        if len(import_paths) == 1:
            canonical_path = list(import_paths)[0]
            expected_canonical = "netra_backend.app.websocket_core.handlers"

            self.assertEqual(
                canonical_path, expected_canonical,
                f"Import path '{canonical_path}' does not match expected canonical path '{expected_canonical}'"
            )

    def test_check_proxy_vs_canonical_implementation_conflicts(self):
        """
        TEST: Check for proxy vs canonical implementation conflicts.

        EXPECTED RESULT: This test SHOULD FAIL initially if proxy pattern is incorrect.
        Proper proxy pattern should forward to canonical implementation without conflicts.
        """
        # Find proxy and canonical implementations
        proxy_implementations = self._find_proxy_implementations()
        canonical_implementations = self._find_canonical_implementations()

        self.logger.info(f"Found proxy implementations: {len(proxy_implementations)}")
        self.logger.info(f"Found canonical implementations: {len(canonical_implementations)}")

        # CRITICAL: Check for proxy-canonical conflicts
        if len(proxy_implementations) > 0 and len(canonical_implementations) > 0:
            # Validate proxy correctly forwards to canonical
            proxy_forwarding_correct = self._validate_proxy_forwarding(
                proxy_implementations, canonical_implementations
            )

            if not proxy_forwarding_correct:
                self.fail(
                    f"PROXY FORWARDING CONFLICT: Proxy implementation does not correctly forward "
                    f"to canonical implementation. This creates inconsistent behavior and violates SSOT."
                )

        # Check for multiple canonical implementations (SSOT violation)
        self.assertLessEqual(
            len(canonical_implementations), 1,
            f"MULTIPLE CANONICAL IMPLEMENTATIONS: Found {len(canonical_implementations)} canonical "
            f"MessageRouter implementations. SSOT requires exactly one canonical implementation."
        )

        # If we have both proxy and canonical, ensure proper relationship
        if len(proxy_implementations) > 0 and len(canonical_implementations) == 1:
            self.logger.info("✅ PROXY PATTERN: Detected proxy forwarding to single canonical implementation")
        elif len(canonical_implementations) == 1 and len(proxy_implementations) == 0:
            self.logger.info("✅ DIRECT CANONICAL: Single canonical implementation without proxy")
        else:
            self.fail(
                f"IMPLEMENTATION PATTERN VIOLATION: Inconsistent proxy/canonical pattern. "
                f"Proxies: {len(proxy_implementations)}, Canonical: {len(canonical_implementations)}"
            )

    def test_comprehensive_ssot_violation_summary(self):
        """
        TEST: Comprehensive summary of all detected SSOT violations.

        This test aggregates all violation types for a complete picture.
        EXPECTED RESULT: Should FAIL with comprehensive violation report.
        """
        violations = []

        # Collect all violation types
        try:
            self.test_detect_multiple_messagerouter_class_definitions()
        except AssertionError as e:
            violations.append(f"Multiple Class Definitions: {str(e)}")

        try:
            self.test_detect_interface_inconsistencies_register_vs_add_handler()
        except AssertionError as e:
            violations.append(f"Interface Inconsistencies: {str(e)}")

        try:
            self.test_validate_import_path_fragmentation()
        except AssertionError as e:
            violations.append(f"Import Path Fragmentation: {str(e)}")

        try:
            self.test_check_proxy_vs_canonical_implementation_conflicts()
        except AssertionError as e:
            violations.append(f"Proxy/Canonical Conflicts: {str(e)}")

        # Report all violations
        if violations:
            violation_report = "\n".join([f"  {i+1}. {v}" for i, v in enumerate(violations)])
            self.fail(
                f"COMPREHENSIVE SSOT VIOLATION REPORT - {len(violations)} violation types detected:\n"
                f"{violation_report}\n\n"
                f"These violations must be resolved to achieve SSOT compliance for Issue #1101."
            )

        # If no violations, SSOT compliance achieved
        self.logger.info("🎉 NO SSOT VIOLATIONS DETECTED - Full compliance achieved!")

    # Helper methods for violation detection

    def _find_messagerouter_class_definitions(self) -> List[Dict[str, Any]]:
        """Find all MessageRouter class definitions in the codebase."""
        messagerouter_files = []

        # Search in netra_backend directory
        for py_file in self.backend_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name == "MessageRouter":
                            messagerouter_files.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line_number': node.lineno,
                                'class_signature': f"class {node.name}",
                                'bases': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases]
                            })
                except SyntaxError:
                    # Skip files with syntax errors
                    continue

            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        return messagerouter_files

    def _find_handler_registration_methods(self) -> List[Dict[str, Any]]:
        """Find all handler registration method patterns."""
        handler_methods = []

        for py_file in self.backend_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if node.name in ['register_handler', 'add_handler']:
                                handler_methods.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'method_name': node.name,
                                    'line_number': node.lineno,
                                    'args': [arg.arg for arg in node.args.args]
                                })
                except SyntaxError:
                    continue

            except (UnicodeDecodeError, PermissionError):
                continue

        return handler_methods

    def _find_messagerouter_import_paths(self) -> Set[str]:
        """Find all possible import paths for MessageRouter."""
        import_paths = set()

        for py_file in self.backend_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for import statements containing MessageRouter
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if 'MessageRouter' in line and ('import' in line or 'from' in line):
                        # Extract import path
                        if line.startswith('from ') and ' import ' in line:
                            parts = line.split(' import ')
                            if len(parts) == 2 and 'MessageRouter' in parts[1]:
                                module_path = parts[0].replace('from ', '').strip()
                                import_paths.add(module_path)
                        elif line.startswith('import ') and 'MessageRouter' not in line:
                            # Handle direct imports like "import module.MessageRouter"
                            continue

            except (UnicodeDecodeError, PermissionError):
                continue

        return import_paths

    def _find_proxy_implementations(self) -> List[Dict[str, Any]]:
        """Find proxy MessageRouter implementations."""
        proxy_implementations = []

        messagerouter_files = self._find_messagerouter_class_definitions()

        for file_info in messagerouter_files:
            file_path = self.project_root / file_info['file']
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if this is a proxy implementation
                if 'proxy' in content.lower() or 'forward' in content.lower():
                    proxy_implementations.append(file_info)

            except (UnicodeDecodeError, PermissionError):
                continue

        return proxy_implementations

    def _find_canonical_implementations(self) -> List[Dict[str, Any]]:
        """Find canonical MessageRouter implementations."""
        canonical_implementations = []

        messagerouter_files = self._find_messagerouter_class_definitions()

        for file_info in messagerouter_files:
            file_path = self.project_root / file_info['file']
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if this is NOT a proxy (likely canonical)
                if 'proxy' not in content.lower() and 'websocket_core' in file_info['file']:
                    canonical_implementations.append(file_info)

            except (UnicodeDecodeError, PermissionError):
                continue

        return canonical_implementations

    def _validate_proxy_forwarding(self, proxy_implementations: List[Dict], canonical_implementations: List[Dict]) -> bool:
        """Validate that proxy correctly forwards to canonical implementation."""
        # This is a simplified check - in real implementation would verify method forwarding
        if not proxy_implementations or not canonical_implementations:
            return True

        # Check if proxy imports from canonical location
        proxy_file = self.project_root / proxy_implementations[0]['file']
        canonical_module = canonical_implementations[0]['file'].replace('/', '.').replace('.py', '')

        try:
            with open(proxy_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple check for import from canonical location
            return canonical_module in content

        except (UnicodeDecodeError, PermissionError):
            return False


if __name__ == '__main__':
    unittest.main()