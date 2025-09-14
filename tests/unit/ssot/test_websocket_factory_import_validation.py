"""
Test suite for Issue #1126: WebSocket Factory SSOT Import Validation

This test suite validates that all WebSocket-related imports follow SSOT patterns
and detects deprecated/fragmented import paths that violate SSOT compliance.

Expected to FAIL initially - demonstrating the import fragmentation issues.
"""

import unittest
import importlib
import sys
import ast
import os
from typing import List, Dict, Set, Tuple
from pathlib import Path

class TestWebSocketFactorySSOTImportValidation(unittest.TestCase):
    """Test WebSocket factory SSOT import compliance."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.deprecated_imports = {
            # These imports should be deprecated in favor of SSOT patterns
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.factory",
            "netra_backend.app.core.websocket_cors",
            "netra_backend.app.websocket_core.auth",
        }

        self.canonical_ssot_imports = {
            # These should be the ONLY allowed WebSocket imports
            "netra_backend.app.websocket_core.ssot_manager",
            "netra_backend.app.websocket_core.ssot_factory",
            "netra_backend.app.websocket_core.ssot_auth",
        }

        self.websocket_files = []
        self.import_violations = []

    def test_detect_deprecated_websocket_imports(self):
        """Test that detects deprecated WebSocket import patterns."""
        violations = self._scan_for_deprecated_imports()

        # This test should FAIL initially, showing deprecated imports exist
        self.assertEqual(len(violations), 0,
                        f"Found {len(violations)} deprecated WebSocket imports that violate SSOT:\n" +
                        "\n".join([f"  {file}: {imp}" for file, imp in violations]))

    def test_websocket_manager_import_fragmentation(self):
        """Test that WebSocket manager imports are fragmented across multiple files."""
        manager_imports = self._find_websocket_manager_imports()

        # Should find multiple different import paths (SSOT violation)
        unique_import_paths = set(imp for _, imp in manager_imports)

        # This test should FAIL initially, showing fragmentation
        self.assertLessEqual(len(unique_import_paths), 1,
                           f"WebSocket manager imported from {len(unique_import_paths)} different paths (SSOT violation):\n" +
                           "\n".join(sorted(unique_import_paths)))

    def test_websocket_factory_pattern_consistency(self):
        """Test that WebSocket factory patterns are consistently used."""
        factory_usage = self._analyze_websocket_factory_usage()

        # Should find consistent factory pattern usage
        inconsistent_patterns = [
            pattern for pattern, count in factory_usage.items()
            if "direct_instantiation" in pattern and count > 0
        ]

        # This test should FAIL initially, showing direct instantiation
        self.assertEqual(len(inconsistent_patterns), 0,
                        f"Found inconsistent WebSocket factory usage patterns:\n" +
                        "\n".join(inconsistent_patterns))

    def test_websocket_cors_import_consolidation(self):
        """Test that WebSocket CORS imports are consolidated."""
        cors_imports = self._find_websocket_cors_imports()

        # Should have single CORS import pattern
        unique_cors_imports = set(imp for _, imp in cors_imports)

        # This test should FAIL initially, showing multiple CORS imports
        self.assertLessEqual(len(unique_cors_imports), 1,
                           f"WebSocket CORS imported from {len(unique_cors_imports)} different locations:\n" +
                           "\n".join(sorted(unique_cors_imports)))

    def test_websocket_auth_ssot_compliance(self):
        """Test that WebSocket auth follows SSOT patterns."""
        auth_imports = self._find_websocket_auth_imports()

        # Should find SSOT-compliant auth imports only
        non_ssot_auth = [
            (file, imp) for file, imp in auth_imports
            if not self._is_ssot_compliant_auth_import(imp)
        ]

        # This test should FAIL initially, showing non-SSOT auth imports
        self.assertEqual(len(non_ssot_auth), 0,
                        f"Found {len(non_ssot_auth)} non-SSOT WebSocket auth imports:\n" +
                        "\n".join([f"  {file}: {imp}" for file, imp in non_ssot_auth]))

    def _scan_for_deprecated_imports(self) -> List[Tuple[str, str]]:
        """Scan for deprecated WebSocket imports."""
        violations = []
        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if any(dep in alias.name for dep in self.deprecated_imports):
                                violations.append((str(file_path), alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and any(dep in node.module for dep in self.deprecated_imports):
                            violations.append((str(file_path), node.module))
            except Exception as e:
                # Skip files that can't be parsed
                pass

        return violations

    def _find_websocket_manager_imports(self) -> List[Tuple[str, str]]:
        """Find all WebSocket manager import patterns."""
        manager_imports = []
        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and "websocket" in node.module and "manager" in node.module:
                            manager_imports.append((str(file_path), node.module))
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if "websocket" in alias.name and "manager" in alias.name:
                                manager_imports.append((str(file_path), alias.name))
            except Exception:
                pass

        return manager_imports

    def _analyze_websocket_factory_usage(self) -> Dict[str, int]:
        """Analyze WebSocket factory usage patterns."""
        factory_patterns = {
            "factory_pattern": 0,
            "direct_instantiation": 0,
            "singleton_pattern": 0
        }

        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for patterns in content
                if "WebSocketManager(" in content:
                    factory_patterns["direct_instantiation"] += 1
                if ".create_websocket_manager" in content:
                    factory_patterns["factory_pattern"] += 1
                if "websocket_manager_instance" in content:
                    factory_patterns["singleton_pattern"] += 1

            except Exception:
                pass

        return factory_patterns

    def _find_websocket_cors_imports(self) -> List[Tuple[str, str]]:
        """Find WebSocket CORS import patterns."""
        cors_imports = []
        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and "websocket" in node.module and "cors" in node.module:
                            cors_imports.append((str(file_path), node.module))
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if "websocket" in alias.name and "cors" in alias.name:
                                cors_imports.append((str(file_path), alias.name))
            except Exception:
                pass

        return cors_imports

    def _find_websocket_auth_imports(self) -> List[Tuple[str, str]]:
        """Find WebSocket auth import patterns."""
        auth_imports = []
        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and "websocket" in node.module and "auth" in node.module:
                            auth_imports.append((str(file_path), node.module))
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if "websocket" in alias.name and "auth" in alias.name:
                                auth_imports.append((str(file_path), alias.name))
            except Exception:
                pass

        return auth_imports

    def _find_websocket_related_files(self) -> List[Path]:
        """Find all files that might contain WebSocket imports."""
        if self.websocket_files:
            return self.websocket_files

        websocket_files = []

        # Search in key directories
        search_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "tests",
            self.project_root / "test_framework"
        ]

        for search_dir in search_dirs:
            if search_dir.exists():
                for py_file in search_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "websocket" in content.lower():
                                websocket_files.append(py_file)
                    except Exception:
                        pass

        self.websocket_files = websocket_files
        return websocket_files

    def _is_ssot_compliant_auth_import(self, import_path: str) -> bool:
        """Check if auth import is SSOT compliant."""
        ssot_auth_patterns = [
            "auth_integration.auth",
            "auth_core.core.jwt_handler",
            "auth_service.auth_core"
        ]

        return any(pattern in import_path for pattern in ssot_auth_patterns)


if __name__ == "__main__":
    unittest.main()