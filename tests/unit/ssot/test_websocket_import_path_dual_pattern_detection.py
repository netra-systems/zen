#!/usr/bin/env python3
"""
test_websocket_import_path_dual_pattern_detection.py

Issue #1144 WebSocket Factory Dual Pattern Detection - Import Path Analysis

PURPOSE: FAILING TESTS to detect multiple import paths for WebSocket managers
These tests should FAIL initially to prove dual pattern violations exist.

CRITICAL: These tests are designed to FAIL and demonstrate the dual pattern problem.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketImportPathDualPatternDetection(SSotBaseTestCase):
    """Test suite to detect multiple import paths for WebSocket managers (SHOULD FAIL)"""

    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.project_root = Path(__file__).resolve().parents[3]
        self.websocket_import_patterns = []
        self.detected_violations = []

    def scan_for_websocket_imports(self) -> Dict[str, List[str]]:
        """Scan codebase for WebSocket-related imports"""
        websocket_imports = {}

        # Search patterns for WebSocket imports
        search_patterns = [
            'websocket_core.manager',
            'websocket_core',
            'UnifiedWebSocketManager',
            'WebSocketManager',
            'websocket_manager',
            'manager.py',
            'websocket.py'
        ]

        # Scan netra_backend for WebSocket imports
        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in search_patterns:
                        if pattern in content:
                            file_key = str(py_file.relative_to(self.project_root))
                            if file_key not in websocket_imports:
                                websocket_imports[file_key] = []
                            websocket_imports[file_key].append(pattern)

                except (UnicodeDecodeError, PermissionError):
                    continue

        return websocket_imports

    def extract_import_statements(self, file_path: Path) -> List[str]:
        """Extract import statements from a Python file"""
        import_statements = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if 'websocket' in name.name.lower():
                            import_statements.append(f"import {name.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'websocket' in node.module.lower():
                        for name in node.names:
                            import_statements.append(f"from {node.module} import {name.name}")

        except (SyntaxError, UnicodeDecodeError, PermissionError):
            pass

        return import_statements

    def test_single_canonical_websocket_manager_import_path_SHOULD_FAIL(self):
        """
        Test: Single canonical import path for WebSocket manager

        EXPECTED BEHAVIOR: SHOULD FAIL due to multiple import paths
        This test is designed to fail to prove dual pattern violations exist.
        """
        websocket_imports = self.scan_for_websocket_imports()

        # Count unique import patterns
        unique_import_patterns = set()
        for file_imports in websocket_imports.values():
            for import_pattern in file_imports:
                unique_import_patterns.add(import_pattern)

        # This test SHOULD FAIL if we have multiple import patterns
        self.assertEqual(
            len(unique_import_patterns), 1,
            f"DUAL PATTERN DETECTED: Found {len(unique_import_patterns)} different WebSocket import patterns: {unique_import_patterns}. "
            f"SSOT requires exactly 1 canonical import path for WebSocket manager."
        )

    def test_websocket_manager_import_consistency_SHOULD_FAIL(self):
        """
        Test: Consistent WebSocket manager import across codebase

        EXPECTED BEHAVIOR: SHOULD FAIL due to inconsistent imports
        This test is designed to fail to prove import fragmentation exists.
        """
        websocket_imports = self.scan_for_websocket_imports()

        # Check for import consistency
        import_variations = set()
        for file_path, imports in websocket_imports.items():
            for import_pattern in imports:
                if 'manager' in import_pattern.lower():
                    import_variations.add(import_pattern)

        # This test SHOULD FAIL if we have import variations
        self.assertLessEqual(
            len(import_variations), 1,
            f"IMPORT FRAGMENTATION DETECTED: Found {len(import_variations)} different manager import patterns: {import_variations}. "
            f"SSOT requires single consistent import pattern."
        )

    def test_websocket_core_module_single_entry_point_SHOULD_FAIL(self):
        """
        Test: Single entry point for websocket_core module

        EXPECTED BEHAVIOR: SHOULD FAIL due to multiple entry points
        This test is designed to fail to prove multiple access patterns exist.
        """
        # Check for websocket_core access patterns
        websocket_core_patterns = []

        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                try:
                    import_statements = self.extract_import_statements(py_file)
                    for stmt in import_statements:
                        if 'websocket_core' in stmt:
                            websocket_core_patterns.append(stmt)
                except Exception:
                    continue

        # Remove duplicates and count unique patterns
        unique_patterns = set(websocket_core_patterns)

        # This test SHOULD FAIL if we have multiple access patterns
        self.assertLessEqual(
            len(unique_patterns), 1,
            f"MULTIPLE ENTRY POINTS DETECTED: Found {len(unique_patterns)} different websocket_core access patterns: {unique_patterns}. "
            f"SSOT requires single entry point."
        )

    def test_websocket_manager_class_single_definition_SHOULD_FAIL(self):
        """
        Test: Single WebSocket manager class definition

        EXPECTED BEHAVIOR: SHOULD FAIL due to multiple definitions
        This test is designed to fail to prove multiple manager classes exist.
        """
        manager_definitions = []

        # Search for WebSocket manager class definitions
        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Look for class definitions
                    if 'class' in content and 'WebSocketManager' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip().startswith('class') and 'WebSocketManager' in line:
                                manager_definitions.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': i + 1,
                                    'definition': line.strip()
                                })

                except (UnicodeDecodeError, PermissionError):
                    continue

        # This test SHOULD FAIL if we have multiple manager class definitions
        self.assertLessEqual(
            len(manager_definitions), 1,
            f"MULTIPLE MANAGER DEFINITIONS DETECTED: Found {len(manager_definitions)} WebSocket manager class definitions: {manager_definitions}. "
            f"SSOT requires single manager class definition."
        )

    def test_websocket_factory_import_path_uniqueness_SHOULD_FAIL(self):
        """
        Test: Unique WebSocket factory import path

        EXPECTED BEHAVIOR: SHOULD FAIL due to multiple factory patterns
        This test is designed to fail to prove factory fragmentation exists.
        """
        factory_imports = []

        # Search for factory-related imports
        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                try:
                    import_statements = self.extract_import_statements(py_file)
                    for stmt in import_statements:
                        if 'factory' in stmt.lower() and 'websocket' in stmt.lower():
                            factory_imports.append(stmt)
                except Exception:
                    continue

        # Remove duplicates
        unique_factory_imports = set(factory_imports)

        # This test SHOULD FAIL if we have multiple factory import patterns
        self.assertLessEqual(
            len(unique_factory_imports), 1,
            f"FACTORY IMPORT FRAGMENTATION DETECTED: Found {len(unique_factory_imports)} different factory import patterns: {unique_factory_imports}. "
            f"SSOT requires single factory import pattern."
        )

    def test_websocket_initialization_pattern_consistency_SHOULD_FAIL(self):
        """
        Test: Consistent WebSocket initialization patterns

        EXPECTED BEHAVIOR: SHOULD FAIL due to inconsistent initialization
        This test is designed to fail to prove initialization fragmentation exists.
        """
        initialization_patterns = []

        # Search for WebSocket initialization patterns
        backend_path = self.project_root / "netra_backend"
        if backend_path.exists():
            for py_file in backend_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Look for initialization patterns
                    lines = content.split('\n')
                    for line in lines:
                        if ('WebSocketManager(' in line or
                            'websocket_manager' in line or
                            'manager =' in line and 'websocket' in line.lower()):
                            initialization_patterns.append(line.strip())

                except (UnicodeDecodeError, PermissionError):
                    continue

        # Remove duplicates and analyze patterns
        unique_patterns = set(initialization_patterns)

        # This test SHOULD FAIL if we have multiple initialization patterns
        self.assertLessEqual(
            len(unique_patterns), 1,
            f"INITIALIZATION PATTERN FRAGMENTATION DETECTED: Found {len(unique_patterns)} different initialization patterns: {unique_patterns}. "
            f"SSOT requires consistent initialization pattern."
        )

    def test_dual_pattern_impact_on_import_clarity_SHOULD_FAIL(self):
        """
        Test: Dual pattern impact on import clarity

        EXPECTED BEHAVIOR: SHOULD FAIL due to import confusion
        This test is designed to fail to prove import clarity issues exist.
        """
        websocket_imports = self.scan_for_websocket_imports()

        # Calculate import complexity score
        total_files_with_websocket_imports = len(websocket_imports)
        total_import_variations = sum(len(imports) for imports in websocket_imports.values())

        if total_files_with_websocket_imports > 0:
            complexity_score = total_import_variations / total_files_with_websocket_imports
        else:
            complexity_score = 0

        # This test SHOULD FAIL if complexity score is high (indicates dual pattern)
        self.assertLessEqual(
            complexity_score, 1.1,
            f"HIGH IMPORT COMPLEXITY DETECTED: Complexity score {complexity_score:.2f} indicates dual pattern. "
            f"Found {total_import_variations} import variations across {total_files_with_websocket_imports} files. "
            f"SSOT requires low complexity (score ≤ 1.1)."
        )

    def tearDown(self):
        """Clean up test environment"""
        # Document detected violations for analysis
        if hasattr(self, 'detected_violations') and self.detected_violations:
            violation_summary = f"WebSocket Import Path Dual Pattern Violations Detected: {len(self.detected_violations)}"
            print(f"\nTEST SUMMARY: {violation_summary}")
            for violation in self.detected_violations[:5]:  # Show first 5 violations
                print(f"  - {violation}")

        super().tearDown()


if __name__ == '__main__':
    import unittest
    unittest.main()