"""
Test suite for Issue #1126: WebSocket SSOT Comprehensive Validation

This test suite provides comprehensive validation of WebSocket SSOT compliance,
identifying violations across multiple dimensions of the architecture.

Expected to FAIL initially - demonstrating comprehensive SSOT violations.
"""

import unittest
import importlib
import inspect
import ast
import os
import sys
from typing import List, Dict, Set, Tuple, Any, Optional
from pathlib import Path
from collections import defaultdict


class TestWebSocketSSOTComprehensiveValidation(unittest.TestCase):
    """Comprehensive WebSocket SSOT compliance validation."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.ssot_registry = self._build_ssot_registry()
        self.violation_summary = defaultdict(list)

    def test_websocket_import_path_consolidation(self):
        """Test that WebSocket imports are consolidated to single paths."""
        import_analysis = self._analyze_websocket_import_paths()

        # Should find single canonical import path for each component
        fragmented_components = {
            component: paths for component, paths in import_analysis.items()
            if len(paths) > 1
        }

        # This test should FAIL initially, showing import fragmentation
        self.assertEqual(len(fragmented_components), 0,
                        f"Found {len(fragmented_components)} components with fragmented import paths:\n" +
                        "\n".join([
                            f"  {comp}: {len(paths)} different paths: {list(paths)}"
                            for comp, paths in fragmented_components.items()
                        ]))

    def test_websocket_class_definition_uniqueness(self):
        """Test that WebSocket classes are defined only once (SSOT principle)."""
        class_definitions = self._find_websocket_class_definitions()

        # Should find each class defined only once
        duplicate_classes = {
            class_name: locations for class_name, locations in class_definitions.items()
            if len(locations) > 1
        }

        # This test should FAIL initially, showing duplicate class definitions
        self.assertEqual(len(duplicate_classes), 0,
                        f"Found {len(duplicate_classes)} WebSocket classes defined multiple times:\n" +
                        "\n".join([
                            f"  {cls}: {len(locs)} definitions in: {[loc['file'] for loc in locs]}"
                            for cls, locs in duplicate_classes.items()
                        ]))

    def test_websocket_interface_contract_consistency(self):
        """Test that WebSocket interfaces maintain consistent contracts."""
        interface_violations = self._validate_websocket_interface_contracts()

        # Should find consistent interface contracts
        contract_violations = [
            violation for violation in interface_violations
            if violation["severity"] == "high"
        ]

        # This test should FAIL initially, showing interface inconsistencies
        self.assertEqual(len(contract_violations), 0,
                        f"Found {len(contract_violations)} high-severity interface contract violations:\n" +
                        "\n".join([
                            f"  {v['interface']}: {v['violation']} in {v['file']}"
                            for v in contract_violations
                        ]))

    def test_websocket_dependency_graph_cycles(self):
        """Test that WebSocket dependencies don't contain cycles."""
        dependency_graph = self._build_websocket_dependency_graph()
        cycles = self._detect_dependency_cycles(dependency_graph)

        # Should find no dependency cycles
        self.assertEqual(len(cycles), 0,
                        f"Found {len(cycles)} dependency cycles in WebSocket components:\n" +
                        "\n".join([f"  Cycle: {' -> '.join(cycle)}" for cycle in cycles]))

    def test_websocket_configuration_consolidation(self):
        """Test that WebSocket configuration is consolidated."""
        config_violations = self._analyze_websocket_configuration_patterns()

        # Should find consolidated configuration patterns
        scattered_configs = [
            violation for violation in config_violations
            if violation["type"] == "scattered_configuration"
        ]

        # This test should FAIL initially, showing scattered configuration
        self.assertEqual(len(scattered_configs), 0,
                        f"Found {len(scattered_configs)} scattered WebSocket configuration patterns:\n" +
                        "\n".join([
                            f"  {v['file']}: {v['config_type']}"
                            for v in scattered_configs
                        ]))

    def test_websocket_event_handling_consistency(self):
        """Test that WebSocket event handling is consistent across components."""
        event_handling_analysis = self._analyze_websocket_event_handling()

        # Should find consistent event handling patterns
        inconsistent_handlers = [
            handler for handler in event_handling_analysis
            if handler["consistency_score"] < 0.8
        ]

        # This test should FAIL initially, showing inconsistent event handling
        self.assertEqual(len(inconsistent_handlers), 0,
                        f"Found {len(inconsistent_handlers)} inconsistent WebSocket event handlers:\n" +
                        "\n".join([
                            f"  {h['event_type']} in {h['file']}: score {h['consistency_score']:.2f}"
                            for h in inconsistent_handlers
                        ]))

    def test_websocket_error_handling_standardization(self):
        """Test that WebSocket error handling follows standard patterns."""
        error_handling_violations = self._validate_websocket_error_handling()

        # Should find standardized error handling
        non_standard_handlers = [
            violation for violation in error_handling_violations
            if violation["type"] == "non_standard_error_handling"
        ]

        # This test should FAIL initially, showing non-standard error handling
        self.assertEqual(len(non_standard_handlers), 0,
                        f"Found {len(non_standard_handlers)} non-standard WebSocket error handlers:\n" +
                        "\n".join([
                            f"  {v['file']}:{v['line']}: {v['pattern']}"
                            for v in non_standard_handlers
                        ]))

    def _build_ssot_registry(self) -> Dict[str, Any]:
        """Build registry of SSOT WebSocket components."""
        return {
            "canonical_imports": {
                "websocket_manager": "netra_backend.app.websocket_core.ssot_manager",
                "websocket_factory": "netra_backend.app.websocket_core.ssot_factory",
                "websocket_auth": "netra_backend.app.websocket_core.ssot_auth",
                "websocket_cors": "netra_backend.app.core.ssot_websocket_cors",
            },
            "allowed_classes": [
                "SSOTWebSocketManager",
                "SSOTWebSocketFactory",
                "SSOTWebSocketAuth",
                "SSOTWebSocketCORS",
            ],
            "forbidden_patterns": [
                "global websocket_manager",
                "_websocket_instance",
                "singleton_websocket",
            ]
        }

    def _analyze_websocket_import_paths(self) -> Dict[str, Set[str]]:
        """Analyze WebSocket import path fragmentation."""
        import_paths = defaultdict(set)
        websocket_files = self._find_all_websocket_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if "websocket" in node.module:
                            component = self._extract_component_name(node.module)
                            if component:
                                import_paths[component].add(node.module)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if "websocket" in alias.name:
                                component = self._extract_component_name(alias.name)
                                if component:
                                    import_paths[component].add(alias.name)

            except Exception:
                pass

        return dict(import_paths)

    def _extract_component_name(self, import_path: str) -> Optional[str]:
        """Extract component name from import path."""
        if "manager" in import_path:
            return "websocket_manager"
        elif "factory" in import_path:
            return "websocket_factory"
        elif "auth" in import_path:
            return "websocket_auth"
        elif "cors" in import_path:
            return "websocket_cors"
        return None

    def _find_websocket_class_definitions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Find all WebSocket class definitions."""
        class_definitions = defaultdict(list)
        websocket_files = self._find_all_websocket_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        if "websocket" in class_name.lower():
                            class_definitions[class_name].append({
                                "file": str(file_path),
                                "line": node.lineno,
                                "methods": [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
                            })

            except Exception:
                pass

        return dict(class_definitions)

    def _validate_websocket_interface_contracts(self) -> List[Dict[str, Any]]:
        """Validate WebSocket interface contracts."""
        violations = []
        websocket_files = self._find_all_websocket_files()

        expected_manager_methods = [
            "send_event",
            "handle_connection",
            "handle_disconnection",
            "broadcast_event",
        ]

        expected_factory_methods = [
            "create_manager",
            "create_auth_handler",
            "create_cors_handler",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        if "websocketmanager" in class_name.lower():
                            violations.extend(self._check_manager_interface(node, file_path, expected_manager_methods))
                        elif "websocketfactory" in class_name.lower():
                            violations.extend(self._check_factory_interface(node, file_path, expected_factory_methods))

            except Exception:
                pass

        return violations

    def _check_manager_interface(self, node: ast.ClassDef, file_path: Path, expected_methods: List[str]) -> List[Dict[str, Any]]:
        """Check WebSocket manager interface compliance."""
        violations = []
        class_methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]

        for expected_method in expected_methods:
            if expected_method not in class_methods:
                violations.append({
                    "interface": "WebSocketManager",
                    "violation": f"Missing method: {expected_method}",
                    "file": str(file_path),
                    "class": node.name,
                    "severity": "high"
                })

        return violations

    def _check_factory_interface(self, node: ast.ClassDef, file_path: Path, expected_methods: List[str]) -> List[Dict[str, Any]]:
        """Check WebSocket factory interface compliance."""
        violations = []
        class_methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]

        for expected_method in expected_methods:
            if expected_method not in class_methods:
                violations.append({
                    "interface": "WebSocketFactory",
                    "violation": f"Missing method: {expected_method}",
                    "file": str(file_path),
                    "class": node.name,
                    "severity": "high"
                })

        return violations

    def _build_websocket_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build WebSocket component dependency graph."""
        dependency_graph = defaultdict(set)
        websocket_files = self._find_all_websocket_files()

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                file_component = self._get_file_component_name(file_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if "websocket" in node.module:
                            imported_component = self._extract_component_name(node.module)
                            if imported_component and imported_component != file_component:
                                dependency_graph[file_component].add(imported_component)

            except Exception:
                pass

        return dict(dependency_graph)

    def _get_file_component_name(self, file_path: Path) -> str:
        """Get component name from file path."""
        file_name = file_path.name.lower()
        if "manager" in file_name:
            return "websocket_manager"
        elif "factory" in file_name:
            return "websocket_factory"
        elif "auth" in file_name:
            return "websocket_auth"
        elif "cors" in file_name:
            return "websocket_cors"
        else:
            return str(file_path.stem)

    def _detect_dependency_cycles(self, dependency_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect cycles in dependency graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependency_graph.get(node, set()):
                dfs(neighbor, path + [neighbor])

            rec_stack.remove(node)

        for node in dependency_graph:
            if node not in visited:
                dfs(node, [node])

        return cycles

    def _analyze_websocket_configuration_patterns(self) -> List[Dict[str, Any]]:
        """Analyze WebSocket configuration patterns."""
        violations = []
        websocket_files = self._find_all_websocket_files()

        config_patterns = [
            "websocket_host",
            "websocket_port",
            "websocket_timeout",
            "cors_origins",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in config_patterns:
                    if pattern in content and "config" not in str(file_path).lower():
                        violations.append({
                            "type": "scattered_configuration",
                            "file": str(file_path),
                            "config_type": pattern
                        })

            except Exception:
                pass

        return violations

    def _analyze_websocket_event_handling(self) -> List[Dict[str, Any]]:
        """Analyze WebSocket event handling consistency."""
        event_handlers = []
        websocket_files = self._find_all_websocket_files()

        event_types = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed",
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for event_type in event_types:
                    if event_type in content:
                        consistency_score = self._calculate_event_consistency_score(content, event_type)
                        event_handlers.append({
                            "event_type": event_type,
                            "file": str(file_path),
                            "consistency_score": consistency_score
                        })

            except Exception:
                pass

        return event_handlers

    def _calculate_event_consistency_score(self, content: str, event_type: str) -> float:
        """Calculate consistency score for event handling."""
        # Simple scoring based on presence of standard patterns
        patterns = [
            f"send_event('{event_type}'",
            f'send_event("{event_type}"',
            "user_id",
            "event_data",
            "timestamp",
        ]

        score = 0.0
        for pattern in patterns:
            if pattern in content:
                score += 0.2

        return min(score, 1.0)

    def _validate_websocket_error_handling(self) -> List[Dict[str, Any]]:
        """Validate WebSocket error handling patterns."""
        violations = []
        websocket_files = self._find_all_websocket_files()

        non_standard_patterns = [
            "except:",  # Bare except
            "pass  # ignore error",
            "print(",  # Print for errors instead of logging
        ]

        for file_path in websocket_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in non_standard_patterns:
                        if pattern in line:
                            violations.append({
                                "type": "non_standard_error_handling",
                                "file": str(file_path),
                                "line": line_num,
                                "pattern": pattern.strip()
                            })

            except Exception:
                pass

        return violations

    def _find_all_websocket_files(self) -> List[Path]:
        """Find all WebSocket-related files."""
        websocket_files = []

        search_dirs = [
            self.project_root / "netra_backend" / "app" / "websocket_core",
            self.project_root / "netra_backend" / "app" / "routes",
            self.project_root / "netra_backend" / "app" / "core",
            self.project_root / "test_framework" / "ssot",
            self.project_root / "tests",
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

        return websocket_files


if __name__ == "__main__":
    unittest.main()