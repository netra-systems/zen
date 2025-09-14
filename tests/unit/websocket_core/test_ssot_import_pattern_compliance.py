#!/usr/bin/env python
"""SSOT Import Pattern Compliance Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Golden Path Infrastructure
- Business Goal: $500K+ ARR protection through import standardization
- Value Impact: Eliminate import confusion and circular dependencies
- Revenue Impact: Ensures consistent WebSocket behavior across all services

Test Strategy: This test MUST FAIL before SSOT consolidation and PASS after
- FAIL: Currently fragmented imports from multiple sources exist
- PASS: After SSOT consolidation, all imports use single authoritative path

Issue #1033: WebSocket Manager SSOT Consolidation
This test validates that all WebSocket imports use SSOT canonical paths to prevent
import fragmentation, circular dependencies, and inconsistent behavior.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import re
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.logging.unified_logging_ssot import get_logger
from test_framework.base_test_case import BaseTestCase

logger = get_logger(__name__)


class TestSSoTImportPatternCompliance(BaseTestCase):
    """Test SSOT compliance for WebSocket import patterns.
    
    This test suite validates that all WebSocket imports follow SSOT patterns
    and use canonical import paths to prevent fragmentation.
    """

    def test_websocket_imports_use_canonical_paths(self):
        """Test that all WebSocket imports use the canonical SSOT path.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently imports use multiple different paths (SSOT violation)
        - PASS: After SSOT consolidation, all imports use canonical path
        
        This test scans all Python files to find WebSocket manager imports and
        validates they all use the single canonical SSOT import path.
        """
        logger.info("🔍 Scanning codebase for WebSocket manager import patterns...")
        
        # Define canonical SSOT import pattern
        canonical_import = "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager"
        
        websocket_imports = self._find_all_websocket_imports()
        
        logger.info(f"Found {len(websocket_imports)} WebSocket import statements:")
        
        # Group imports by pattern to identify violations
        import_patterns = defaultdict(list)
        for import_info in websocket_imports:
            pattern = import_info['import_statement']
            import_patterns[pattern].append(import_info)
        
        for pattern, occurrences in import_patterns.items():
            logger.info(f"  Pattern: {pattern} ({len(occurrences)} files)")
            if len(occurrences) <= 3:  # Show files for common patterns
                for occurrence in occurrences:
                    logger.info(f"    - {occurrence['file']}:{occurrence['line']}")
        
        # SSOT VIOLATION CHECK: Should only use canonical import pattern
        deprecated_patterns = [
            "from netra_backend.app.websocket_core.websocket_manager_factory import",
            "from netra_backend.app.websocket_core.unified_manager import",
            "from netra_backend.app.websocket_core import WebSocketManager",
            "from netra_backend.app.websocket_core import create_websocket_manager"
        ]
        
        violations = []
        for pattern, occurrences in import_patterns.items():
            for deprecated in deprecated_patterns:
                if deprecated in pattern:
                    violations.extend(occurrences)
                    break
        
        if violations:
            logger.error("SSOT VIOLATIONS: Found deprecated WebSocket import patterns:")
            for violation in violations[:10]:  # Show first 10 violations
                logger.error(f"  {violation['file']}:{violation['line']} - {violation['import_statement']}")
            
            if len(violations) > 10:
                logger.error(f"  ... and {len(violations) - 10} more violations")
        
        # This assertion WILL FAIL until import consolidation is complete
        assert len(violations) == 0, (
            f"SSOT VIOLATION: Found {len(violations)} files using deprecated WebSocket import patterns. "
            f"All imports should use canonical SSOT path: '{canonical_import}'"
        )

    def test_no_circular_import_dependencies(self):
        """Test that WebSocket imports don't create circular dependencies.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently circular imports exist (SSOT violation)
        - PASS: After SSOT consolidation, no circular dependencies
        
        This test analyzes import graphs to detect circular dependency chains
        that could cause import errors or initialization failures.
        """
        logger.info("🔍 Analyzing WebSocket import dependencies for circular chains...")
        
        import_graph = self._build_websocket_import_graph()
        circular_chains = self._detect_circular_dependencies(import_graph)
        
        if circular_chains:
            logger.error("SSOT VIOLATIONS: Found circular import dependencies:")
            for i, chain in enumerate(circular_chains, 1):
                logger.error(f"  Chain {i}: {' -> '.join(chain)} -> {chain[0]}")
        
        # SSOT VIOLATION CHECK: No circular dependencies should exist
        # This assertion WILL FAIL until circular imports are resolved
        assert len(circular_chains) == 0, (
            f"SSOT VIOLATION: Found {len(circular_chains)} circular import dependency chains. "
            f"Circular dependencies prevent reliable SSOT consolidation."
        )

    def test_websocket_factory_deprecation_compliance(self):
        """Test that deprecated WebSocket factory imports are eliminated.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently factory imports still exist (SSOT violation)
        - PASS: After SSOT consolidation, no factory imports remain
        
        This test specifically checks for usage of deprecated factory patterns
        that should be replaced with direct SSOT imports.
        """
        logger.info("🔍 Checking for deprecated WebSocket factory usage...")
        
        factory_imports = self._find_factory_imports()
        factory_usages = self._find_factory_function_calls()
        
        logger.info(f"Found {len(factory_imports)} factory import statements")
        logger.info(f"Found {len(factory_usages)} factory function calls")
        
        all_factory_violations = factory_imports + factory_usages
        
        if all_factory_violations:
            logger.error("SSOT VIOLATIONS: Found deprecated WebSocket factory usage:")
            for violation in all_factory_violations[:10]:  # Show first 10
                logger.error(f"  {violation['file']}:{violation['line']} - {violation['code']}")
            
            if len(all_factory_violations) > 10:
                logger.error(f"  ... and {len(all_factory_violations) - 10} more violations")
        
        # SSOT VIOLATION CHECK: No factory usage should remain
        # This assertion WILL FAIL until factory deprecation is complete
        assert len(all_factory_violations) == 0, (
            f"SSOT VIOLATION: Found {len(all_factory_violations)} deprecated factory usages. "
            f"All factory patterns should be replaced with direct SSOT WebSocket manager usage."
        )

    def test_import_consistency_across_services(self):
        """Test that WebSocket imports are consistent across all services.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently different services use different import patterns
        - PASS: After SSOT consolidation, all services use same imports
        
        This test validates that auth service, backend, and other components
        all use consistent WebSocket import patterns.
        """
        logger.info("🔍 Checking import consistency across services...")
        
        service_imports = self._find_websocket_imports_by_service()
        
        # Check for import pattern consistency
        inconsistencies = []
        canonical_pattern = None
        
        for service, imports in service_imports.items():
            if not imports:
                continue
                
            # Get unique import patterns for this service
            patterns = set(imp['import_statement'] for imp in imports)
            
            logger.info(f"Service '{service}' uses {len(patterns)} different import patterns:")
            for pattern in patterns:
                logger.info(f"  - {pattern}")
            
            # If this is the first service with imports, set as canonical
            if canonical_pattern is None and patterns:
                canonical_pattern = list(patterns)[0]
            
            # Check for deviations from canonical pattern
            for pattern in patterns:
                if pattern != canonical_pattern:
                    inconsistencies.append({
                        'service': service,
                        'expected': canonical_pattern,
                        'actual': pattern,
                        'files': [imp['file'] for imp in imports if imp['import_statement'] == pattern]
                    })
        
        if inconsistencies:
            logger.error("SSOT VIOLATIONS: Found import pattern inconsistencies between services:")
            for inconsistency in inconsistencies:
                logger.error(f"  Service '{inconsistency['service']}' uses: {inconsistency['actual']}")
                logger.error(f"    Expected: {inconsistency['expected']}")
                logger.error(f"    Files: {inconsistency['files'][:3]}")  # Show first 3 files
        
        # SSOT VIOLATION CHECK: All services should use same import pattern
        # This assertion WILL FAIL until import standardization is complete
        assert len(inconsistencies) == 0, (
            f"SSOT VIOLATION: Found {len(inconsistencies)} import pattern inconsistencies "
            f"across services. All services should use the same canonical import pattern."
        )

    def _find_all_websocket_imports(self) -> List[Dict[str, Any]]:
        """Find all WebSocket-related import statements in the codebase."""
        websocket_imports = []
        
        # Search patterns for WebSocket imports
        websocket_patterns = [
            r'from\s+.*websocket.*\s+import',
            r'import\s+.*websocket.*',
            r'from\s+.*WebSocket.*\s+import',
            r'import\s+.*WebSocket.*'
        ]
        
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in websocket_patterns]
        
        # Search in main directories
        search_paths = [
            Path(project_root) / "netra_backend",
            Path(project_root) / "auth_service",
            Path(project_root) / "tests",
            Path(project_root) / "test_framework"
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        for pattern in compiled_patterns:
                            if pattern.search(line_stripped):
                                websocket_imports.append({
                                    'file': str(py_file.relative_to(Path(project_root))),
                                    'line': line_num,
                                    'import_statement': line_stripped
                                })
                                break
                                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return websocket_imports

    def _build_websocket_import_graph(self) -> Dict[str, Set[str]]:
        """Build a graph of WebSocket-related import dependencies."""
        import_graph = defaultdict(set)
        
        # Focus on WebSocket core modules
        websocket_modules = [
            "netra_backend.app.websocket_core.websocket_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory", 
            "netra_backend.app.websocket_core.unified_manager"
        ]
        
        for module_name in websocket_modules:
            try:
                module_path = Path(project_root) / module_name.replace('.', '/') + '.py'
                if not module_path.exists():
                    continue
                    
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse imports using AST
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module and 'websocket' in node.module.lower():
                                import_graph[module_name].add(node.module)
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                if 'websocket' in alias.name.lower():
                                    import_graph[module_name].add(alias.name)
                except SyntaxError:
                    continue
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return dict(import_graph)

    def _detect_circular_dependencies(self, import_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect circular dependency chains in the import graph."""
        def find_cycles(graph, start, path, visited, cycles):
            if start in path:
                # Found a cycle
                cycle_start_idx = path.index(start)
                cycle = path[cycle_start_idx:]
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            
            if start in visited:
                return
                
            visited.add(start)
            path.append(start)
            
            for neighbor in graph.get(start, set()):
                find_cycles(graph, neighbor, path, visited, cycles)
                
            path.pop()
        
        cycles = []
        visited = set()
        
        for node in import_graph:
            if node not in visited:
                find_cycles(import_graph, node, [], visited, cycles)
        
        return cycles

    def _find_factory_imports(self) -> List[Dict[str, Any]]:
        """Find deprecated WebSocket factory import statements."""
        factory_patterns = [
            r'from\s+.*websocket_manager_factory\s+import',
            r'import\s+.*websocket_manager_factory',
            r'from\s+.*\s+import\s+.*create_websocket_manager',
            r'from\s+.*\s+import\s+.*get_websocket_manager_factory'
        ]
        
        return self._search_patterns_in_files(factory_patterns)

    def _find_factory_function_calls(self) -> List[Dict[str, Any]]:
        """Find deprecated WebSocket factory function calls."""
        factory_call_patterns = [
            r'create_websocket_manager\s*\(',
            r'get_websocket_manager_factory\s*\(',
            r'websocket_manager_factory\.',
            r'factory\.create\s*\('
        ]
        
        return self._search_patterns_in_files(factory_call_patterns)

    def _find_websocket_imports_by_service(self) -> Dict[str, List[Dict[str, Any]]]:
        """Find WebSocket imports organized by service."""
        service_imports = {
            'backend': [],
            'auth_service': [],
            'tests': [],
            'test_framework': []
        }
        
        all_imports = self._find_all_websocket_imports()
        
        for import_info in all_imports:
            file_path = import_info['file']
            
            if file_path.startswith('netra_backend/'):
                service_imports['backend'].append(import_info)
            elif file_path.startswith('auth_service/'):
                service_imports['auth_service'].append(import_info)
            elif file_path.startswith('tests/'):
                service_imports['tests'].append(import_info)
            elif file_path.startswith('test_framework/'):
                service_imports['test_framework'].append(import_info)
        
        return service_imports

    def _search_patterns_in_files(self, patterns: List[str]) -> List[Dict[str, Any]]:
        """Search for regex patterns in Python files."""
        matches = []
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        search_paths = [
            Path(project_root) / "netra_backend",
            Path(project_root) / "auth_service", 
            Path(project_root) / "tests",
            Path(project_root) / "test_framework"
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in compiled_patterns:
                            if pattern.search(line):
                                matches.append({
                                    'file': str(py_file.relative_to(Path(project_root))),
                                    'line': line_num,
                                    'code': line.strip()
                                })
                                break
                                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return matches


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])