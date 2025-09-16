"""
Unit Tests for Issue #1278: Cross-Service Import Violations

PURPOSE: Detect cross-service import violations that cause WebSocket middleware failures.
EXPECTED RESULT: Should FAIL currently due to Issue #1278 import problems.

These tests validate that services maintain proper import boundaries and detect
violations that lead to middleware setup failures and WebSocket initialization problems.
"""

import pytest
import sys
import importlib
import ast
import os
from pathlib import Path
from typing import Set, List, Dict, Any


class TestCrossServiceImportViolations:
    """Test for cross-service import violations causing Issue #1278 failures"""

    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.services = {
            'netra_backend': self.project_root / 'netra_backend',
            'auth_service': self.project_root / 'auth_service',
            'frontend': self.project_root / 'frontend'
        }

    def test_netra_backend_import_boundaries(self):
        """
        Test that netra_backend doesn't import from other services

        EXPECTED: FAIL - Issue #1278 indicates import boundary violations
        """
        violations = self._scan_import_violations('netra_backend',
                                                  forbidden_imports=['auth_service', 'frontend'])

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(violations) == 0, (
            f"Found {len(violations)} cross-service import violations in netra_backend:\n"
            f"{self._format_violations(violations)}"
        )

    def test_auth_service_import_boundaries(self):
        """
        Test that auth_service doesn't import from other services

        EXPECTED: FAIL - Issue #1278 indicates import boundary violations
        """
        violations = self._scan_import_violations('auth_service',
                                                  forbidden_imports=['netra_backend', 'frontend'])

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(violations) == 0, (
            f"Found {len(violations)} cross-service import violations in auth_service:\n"
            f"{self._format_violations(violations)}"
        )

    def test_websocket_middleware_import_isolation(self):
        """
        Test WebSocket middleware imports don't violate service boundaries

        EXPECTED: FAIL - Issue #1278 specifically affects WebSocket middleware
        """
        websocket_files = list(self.services['netra_backend'].rglob('*websocket*.py'))
        violations = []

        for file_path in websocket_files:
            file_violations = self._analyze_file_imports(
                file_path,
                forbidden_patterns=['auth_service', 'frontend']
            )
            violations.extend(file_violations)

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(violations) == 0, (
            f"Found {len(violations)} WebSocket middleware import violations:\n"
            f"{self._format_violations(violations)}"
        )

    def test_critical_import_cycles(self):
        """
        Test for circular imports that cause startup failures

        EXPECTED: FAIL - Issue #1278 indicates circular import problems
        """
        import_graph = self._build_import_graph()
        cycles = self._detect_cycles(import_graph)

        # Filter for cross-service cycles only
        cross_service_cycles = [
            cycle for cycle in cycles
            if self._is_cross_service_cycle(cycle)
        ]

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(cross_service_cycles) == 0, (
            f"Found {len(cross_service_cycles)} cross-service import cycles:\n"
            f"{self._format_cycles(cross_service_cycles)}"
        )

    def test_middleware_setup_imports(self):
        """
        Test that middleware setup doesn't have problematic imports

        EXPECTED: FAIL - Issue #1278 affects middleware initialization
        """
        middleware_files = [
            self.services['netra_backend'] / 'app' / 'core' / 'middleware.py',
            self.services['netra_backend'] / 'app' / 'core' / 'websocket_cors.py',
            self.services['netra_backend'] / 'app' / 'middleware',
        ]

        violations = []
        for middleware_path in middleware_files:
            if middleware_path.exists():
                if middleware_path.is_file():
                    file_violations = self._analyze_file_imports(
                        middleware_path,
                        forbidden_patterns=['auth_service.auth_core']
                    )
                    violations.extend(file_violations)
                else:
                    # Directory - scan all Python files
                    for py_file in middleware_path.rglob('*.py'):
                        file_violations = self._analyze_file_imports(
                            py_file,
                            forbidden_patterns=['auth_service.auth_core']
                        )
                        violations.extend(file_violations)

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(violations) == 0, (
            f"Found {len(violations)} middleware import violations:\n"
            f"{self._format_violations(violations)}"
        )

    def _scan_import_violations(self, service_name: str, forbidden_imports: List[str]) -> List[Dict[str, Any]]:
        """Scan a service for import violations"""
        violations = []
        service_path = self.services[service_name]

        if not service_path.exists():
            return violations

        for py_file in service_path.rglob('*.py'):
            file_violations = self._analyze_file_imports(py_file, forbidden_imports)
            violations.extend(file_violations)

        return violations

    def _analyze_file_imports(self, file_path: Path, forbidden_patterns: List[str]) -> List[Dict[str, Any]]:
        """Analyze a single file for import violations"""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_info = self._extract_import_info(node)

                    for pattern in forbidden_patterns:
                        if any(pattern in module for module in import_info['modules']):
                            violations.append({
                                'file': str(file_path),
                                'line': node.lineno,
                                'import': import_info,
                                'violation': f"Forbidden import pattern: {pattern}"
                            })

        except Exception as e:
            # Record parsing errors as potential violations
            violations.append({
                'file': str(file_path),
                'line': 0,
                'import': {'modules': [], 'type': 'parse_error'},
                'violation': f"Parse error: {str(e)}"
            })

        return violations

    def _extract_import_info(self, node) -> Dict[str, Any]:
        """Extract import information from AST node"""
        if isinstance(node, ast.Import):
            return {
                'type': 'import',
                'modules': [alias.name for alias in node.names]
            }
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            return {
                'type': 'import_from',
                'modules': [f"{module}.{alias.name}" for alias in node.names],
                'base_module': module
            }
        return {'type': 'unknown', 'modules': []}

    def _build_import_graph(self) -> Dict[str, Set[str]]:
        """Build import dependency graph"""
        graph = {}

        for service_name, service_path in self.services.items():
            if not service_path.exists():
                continue

            for py_file in service_path.rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    tree = ast.parse(content)
                    module_name = self._path_to_module_name(py_file, service_path)

                    imports = set()
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            import_info = self._extract_import_info(node)
                            imports.update(import_info['modules'])

                    graph[module_name] = imports

                except Exception:
                    continue

        return graph

    def _detect_cycles(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect cycles in import graph using DFS"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, set()):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _is_cross_service_cycle(self, cycle: List[str]) -> bool:
        """Check if cycle crosses service boundaries"""
        services_in_cycle = set()

        for module in cycle:
            for service in self.services:
                if module.startswith(service):
                    services_in_cycle.add(service)

        return len(services_in_cycle) > 1

    def _path_to_module_name(self, file_path: Path, service_root: Path) -> str:
        """Convert file path to module name"""
        relative_path = file_path.relative_to(service_root)
        module_parts = list(relative_path.parts[:-1])  # Remove .py file
        if relative_path.stem != '__init__':
            module_parts.append(relative_path.stem)
        return '.'.join(module_parts)

    def _format_violations(self, violations: List[Dict[str, Any]]) -> str:
        """Format violations for error display"""
        formatted = []
        for v in violations[:10]:  # Limit to first 10 for readability
            formatted.append(f"  {v['file']}:{v['line']} - {v['violation']}")
        if len(violations) > 10:
            formatted.append(f"  ... and {len(violations) - 10} more violations")
        return '\n'.join(formatted)

    def _format_cycles(self, cycles: List[List[str]]) -> str:
        """Format cycles for error display"""
        formatted = []
        for cycle in cycles[:5]:  # Limit to first 5 for readability
            formatted.append(f"  {' -> '.join(cycle)}")
        if len(cycles) > 5:
            formatted.append(f"  ... and {len(cycles) - 5} more cycles")
        return '\n'.join(formatted)


if __name__ == "__main__":
    # Allow direct execution for debugging
    pytest.main([__file__, "-v", "--tb=short"])