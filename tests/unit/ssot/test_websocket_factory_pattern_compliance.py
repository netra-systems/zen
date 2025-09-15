"""
Test suite for Issue #1126: WebSocket Factory Pattern SSOT Compliance

This test suite validates that WebSocket factory patterns follow SSOT principles
and identifies violations where direct instantiation or singleton patterns are used.

Expected to FAIL initially - demonstrating factory pattern violations.
"""

import pytest
import unittest
import importlib
import inspect
import ast
import os
from typing import List, Dict, Set, Tuple, Any
from pathlib import Path


@pytest.mark.unit
class TestWebSocketFactoryPatternCompliance(unittest.TestCase):
    """Test WebSocket factory pattern SSOT compliance."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.factory_violations = []
        self.singleton_violations = []
        self.direct_instantiation_violations = []

    def test_websocket_manager_factory_pattern_required(self):
        """Test that WebSocket manager uses factory pattern exclusively."""
        violations = self._scan_for_direct_websocket_manager_instantiation()

        # This test should FAIL initially, showing direct instantiation
        self.assertEqual(len(violations), 0,
                        f"Found {len(violations)} direct WebSocket manager instantiations (should use factory):\n" +
                        "\n".join([f"  {file}:{line}: {pattern}" for file, line, pattern in violations]))

    def test_websocket_factory_singleton_violations(self):
        """Test that WebSocket factories don't use singleton patterns."""
        singleton_violations = self._detect_websocket_singleton_patterns()

        # This test should FAIL initially, showing singleton usage
        self.assertEqual(len(singleton_violations), 0,
                        f"Found {len(singleton_violations)} WebSocket singleton pattern violations:\n" +
                        "\n".join([f"  {file}:{line}: {pattern}" for file, line, pattern in singleton_violations]))

    def test_websocket_factory_user_isolation_compliance(self):
        """Test that WebSocket factories properly isolate user contexts."""
        isolation_violations = self._check_user_context_isolation()

        # This test should FAIL initially, showing shared state
        self.assertEqual(len(isolation_violations), 0,
                        f"Found {len(isolation_violations)} user isolation violations in WebSocket factories:\n" +
                        "\n".join([f"  {file}: {violation}" for file, violation in isolation_violations]))

    def test_websocket_factory_instance_creation_patterns(self):
        """Test that WebSocket factory instance creation follows SSOT patterns."""
        creation_violations = self._analyze_instance_creation_patterns()

        # Should find consistent factory-based creation
        non_factory_patterns = [
            violation for violation in creation_violations
            if violation["pattern_type"] != "factory_method"
        ]

        # This test should FAIL initially, showing non-factory patterns
        self.assertEqual(len(non_factory_patterns), 0,
                        f"Found {len(non_factory_patterns)} non-factory WebSocket creation patterns:\n" +
                        "\n".join([f"  {v['file']}:{v['line']}: {v['pattern']}" for v in non_factory_patterns]))

    def test_websocket_manager_dependency_injection_compliance(self):
        """Test that WebSocket managers use proper dependency injection."""
        di_violations = self._check_dependency_injection_patterns()

        # Should find proper dependency injection usage
        hard_coded_dependencies = [
            violation for violation in di_violations
            if violation["type"] == "hard_coded_dependency"
        ]

        # This test should FAIL initially, showing hard-coded dependencies
        self.assertEqual(len(hard_coded_dependencies), 0,
                        f"Found {len(hard_coded_dependencies)} hard-coded dependencies in WebSocket components:\n" +
                        "\n".join([f"  {v['file']}:{v['line']}: {v['dependency']}" for v in hard_coded_dependencies]))

    def test_websocket_factory_interface_consistency(self):
        """Test that WebSocket factory interfaces are consistent across implementations."""
        interface_violations = self._check_factory_interface_consistency()

        # Should find consistent factory interfaces
        inconsistent_interfaces = [
            violation for violation in interface_violations
            if violation["type"] == "interface_mismatch"
        ]

        # This test should FAIL initially, showing interface inconsistencies
        self.assertEqual(len(inconsistent_interfaces), 0,
                        f"Found {len(inconsistent_interfaces)} inconsistent WebSocket factory interfaces:\n" +
                        "\n".join([f"  {v['class']}: {v['issue']}" for v in inconsistent_interfaces]))

    def _scan_for_direct_websocket_manager_instantiation(self) -> List[Tuple[str, int, str]]:
        """Scan for direct WebSocket manager instantiation patterns."""
        violations = []
        websocket_files = self._find_websocket_related_files()

        direct_instantiation_patterns = [
            "WebSocketManager(",
            "UnifiedWebSocketManager(",
            "WebSocketConnectionManager(",
            "WebSocketEventManager(",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in direct_instantiation_patterns:
                        if pattern in line and "def " not in line and "class " not in line:
                            violations.append((str(file_path), line_num, line.strip()))
            except Exception:
                pass

        return violations

    def _detect_websocket_singleton_patterns(self) -> List[Tuple[str, int, str]]:
        """Detect singleton patterns in WebSocket components."""
        violations = []
        websocket_files = self._find_websocket_related_files()

        singleton_patterns = [
            "_instance = None",
            "_websocket_instance",
            "def get_instance(",
            "if not hasattr(cls, '_instance')",
            "cls._instance",
            "_websocket_manager_instance",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in singleton_patterns:
                        if pattern in line:
                            violations.append((str(file_path), line_num, line.strip()))
            except Exception:
                pass

        return violations

    def _check_user_context_isolation(self) -> List[Tuple[str, str]]:
        """Check for user context isolation violations."""
        violations = []
        websocket_files = self._find_websocket_related_files()

        shared_state_patterns = [
            "global websocket_manager",
            "shared_websocket_state",
            "global_websocket_instance",
            "class_variable_websocket",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for shared state patterns
                for pattern in shared_state_patterns:
                    if pattern in content:
                        violations.append((str(file_path), f"Shared state pattern: {pattern}"))

                # Check for class variables that might be shared
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and "websocket" in target.id.lower():
                                        violations.append((str(file_path), f"Potential shared class variable: {target.id}"))

            except Exception:
                pass

        return violations

    def _analyze_instance_creation_patterns(self) -> List[Dict[str, Any]]:
        """Analyze WebSocket instance creation patterns."""
        creation_patterns = []
        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                            if "websocket" in func_name.lower() and "manager" in func_name.lower():
                                pattern_type = self._classify_creation_pattern(func_name, content)
                                creation_patterns.append({
                                    "file": str(file_path),
                                    "line": node.lineno,
                                    "pattern": func_name,
                                    "pattern_type": pattern_type
                                })

            except Exception:
                pass

        return creation_patterns

    def _classify_creation_pattern(self, func_name: str, content: str) -> str:
        """Classify the type of creation pattern."""
        if "factory" in func_name.lower() or "create" in func_name.lower():
            return "factory_method"
        elif "get_instance" in func_name.lower() or "instance" in func_name.lower():
            return "singleton_method"
        else:
            return "direct_instantiation"

    def _check_dependency_injection_patterns(self) -> List[Dict[str, Any]]:
        """Check dependency injection patterns in WebSocket components."""
        violations = []
        websocket_files = self._find_websocket_related_files()

        hard_coded_patterns = [
            "localhost:8000",
            "127.0.0.1",
            "redis://localhost",
            "postgresql://",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in hard_coded_patterns:
                        if pattern in line and "test" not in str(file_path).lower():
                            violations.append({
                                "file": str(file_path),
                                "line": line_num,
                                "type": "hard_coded_dependency",
                                "dependency": pattern
                            })

            except Exception:
                pass

        return violations

    def _check_factory_interface_consistency(self) -> List[Dict[str, Any]]:
        """Check factory interface consistency."""
        violations = []
        factory_classes = self._find_websocket_factory_classes()

        expected_methods = [
            "create_websocket_manager",
            "create_auth_handler",
            "create_cors_handler",
        ]

        for class_info in factory_classes:
            missing_methods = []
            for method in expected_methods:
                if method not in class_info["methods"]:
                    missing_methods.append(method)

            if missing_methods:
                violations.append({
                    "type": "interface_mismatch",
                    "class": class_info["name"],
                    "issue": f"Missing methods: {', '.join(missing_methods)}"
                })

        return violations

    def _find_websocket_factory_classes(self) -> List[Dict[str, Any]]:
        """Find WebSocket factory classes and their methods."""
        factory_classes = []
        websocket_files = self._find_websocket_related_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        if "factory" in class_name.lower() and "websocket" in class_name.lower():
                            methods = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    methods.append(item.name)

                            factory_classes.append({
                                "name": class_name,
                                "file": str(file_path),
                                "methods": methods
                            })

            except Exception:
                pass

        return factory_classes

    def _find_websocket_related_files(self) -> List[Path]:
        """Find all files that might contain WebSocket factory patterns."""
        websocket_files = []

        # Search in key directories
        search_dirs = [
            self.project_root / "netra_backend" / "app" / "websocket_core",
            self.project_root / "netra_backend" / "app" / "routes",
            self.project_root / "netra_backend" / "app" / "core",
            self.project_root / "test_framework" / "ssot",
        ]

        for search_dir in search_dirs:
            if search_dir.exists():
                for py_file in search_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if ("websocket" in content.lower() and
                                ("factory" in content.lower() or "manager" in content.lower() or "create" in content.lower())):
                                websocket_files.append(py_file)
                    except Exception:
                        pass

        return websocket_files


if __name__ == "__main__":
    unittest.main()