"""
WebSocket Import Path SSOT Consolidation Test

PURPOSE: Validate unified WebSocket import paths across all services
SHOULD FAIL: Because import fragmentation exists across dual directories
SHOULD PASS: When all imports use single SSOT path

Business Impact: $500K+ ARR chat functionality at risk from import confusion
GitHub Issue: #1144 - WebSocket Factory Dual Pattern Blocking Golden Path

This test validates that:
1. All WebSocket imports resolve to single canonical path
2. No circular import dependencies exist
3. Import resolution is deterministic across environments
4. Factory imports follow SSOT pattern consistently
"""

import unittest
import importlib
import importlib.util
import sys
import inspect
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import ast

from test_framework.ssot.base_test_case import SSotBaseTestCase


class WebSocketImportPathSSotConsolidationTest(SSotBaseTestCase):
    """
    Test to validate SSOT consolidation of WebSocket import paths.
    
    This test MUST FAIL with current import fragmentation to prove
    the violation exists. After SSOT remediation, it should PASS.
    """
    
    def setUp(self):
        """Set up test environment for import path analysis."""
        self.backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend"
        self.import_violations = {
            'duplicate_paths': [],
            'circular_imports': [],
            'fragmented_imports': [],
            'non_canonical_imports': []
        }
        
        # Expected canonical paths after SSOT fix
        self.expected_canonical_paths = {
            'websocket_manager': 'netra_backend.app.websocket_core.websocket_manager',
            'connection_manager': 'netra_backend.app.websocket_core.connection_manager', 
            'connection_info': 'netra_backend.app.websocket_core.connection_info',
            'auth_handler': 'netra_backend.app.websocket_core.auth'
        }
    
    def test_websocket_manager_import_path_fragmentation_detection(self):
        """
        CRITICAL: Test detecting fragmented import paths for WebSocket manager.
        
        This test MUST FAIL because:
        - Multiple import paths exist for WebSocket manager functionality
        - /websocket/connection_manager.py vs /websocket_core/manager.py vs /websocket_core/unified_manager.py
        - Import resolution is non-deterministic
        
        After SSOT fix, should PASS with single canonical import path.
        """
        # Discover all possible WebSocket manager import paths
        manager_import_paths = self._discover_manager_import_paths()
        
        print(f"\nDETECTED WEBSOCKET MANAGER IMPORT PATHS: {len(manager_import_paths)}")
        for path_info in manager_import_paths:
            print(f"  - {path_info['import_path']}: {path_info['class_name']}")
            
        # VIOLATION CHECK: Multiple import paths for manager functionality
        # This assertion SHOULD FAIL with current fragmentation
        self.assertLessEqual(
            len(manager_import_paths), 1,
            f"SSOT VIOLATION: Found {len(manager_import_paths)} different import paths for WebSocket manager. "
            f"Expected single canonical path. Detected paths: {[p['import_path'] for p in manager_import_paths]}"
        )
    
    def test_websocket_import_resolution_consistency_violation(self):
        """
        CRITICAL: Test detecting inconsistent import resolution across modules.
        
        This test MUST FAIL because:
        - Different modules import WebSocket functionality from different paths
        - Import resolution depends on import order/timing
        - Compatibility shims create resolution ambiguity
        
        After SSOT fix, should PASS with consistent resolution.
        """
        # Analyze import resolution consistency
        import_inconsistencies = self._analyze_import_resolution_consistency()
        
        print(f"\nDETECTED IMPORT RESOLUTION INCONSISTENCIES: {len(import_inconsistencies)}")
        for inconsistency in import_inconsistencies:
            print(f"  - Functionality: {inconsistency['functionality']}")
            print(f"    Paths: {inconsistency['conflicting_paths']}")
        
        # This assertion SHOULD FAIL with current inconsistencies
        self.assertEqual(
            len(import_inconsistencies), 0,
            f"SSOT VIOLATION: Found {len(import_inconsistencies)} import resolution inconsistencies. "
            f"Inconsistencies: {[i['functionality'] for i in import_inconsistencies]}"
        )
    
    def test_circular_import_dependency_detection(self):
        """
        CRITICAL: Test detecting circular import dependencies in dual pattern.
        
        This test MUST FAIL because:
        - /websocket/ modules import from /websocket_core/
        - /websocket_core/ modules may reference /websocket/ for compatibility
        - Circular dependencies create import ordering issues
        
        After SSOT fix, should PASS with no circular dependencies.
        """
        # Detect circular import dependencies
        circular_dependencies = self._detect_circular_import_dependencies()
        
        print(f"\nDETECTED CIRCULAR IMPORT DEPENDENCIES: {len(circular_dependencies)}")
        for dependency in circular_dependencies:
            print(f"  - {dependency['module_a']} <-> {dependency['module_b']}")
            print(f"    Cycle: {' -> '.join(dependency['cycle_path'])}")
        
        # This assertion SHOULD FAIL with current circular dependencies
        self.assertEqual(
            len(circular_dependencies), 0,
            f"SSOT VIOLATION: Found {len(circular_dependencies)} circular import dependencies. "
            f"Cycles detected: {[d['cycle_path'] for d in circular_dependencies]}"
        )
    
    def test_non_canonical_import_usage_detection(self):
        """
        CRITICAL: Test detecting usage of non-canonical import paths.
        
        This test MUST FAIL because:
        - Code still uses legacy /websocket/ import paths
        - Tests use non-canonical paths for WebSocket functionality
        - Import paths don't follow SSOT conventions
        
        After SSOT fix, should PASS with only canonical imports.
        """
        # Find all non-canonical import usages
        non_canonical_usages = self._find_non_canonical_import_usages()
        
        print(f"\nDETECTED NON-CANONICAL IMPORT USAGES: {len(non_canonical_usages)}")
        for usage in non_canonical_usages:
            print(f"  - {usage['file']}: {usage['import_statement']}")
            print(f"    Should be: {usage['canonical_alternative']}")
        
        # This assertion SHOULD FAIL with current non-canonical usages
        self.assertEqual(
            len(non_canonical_usages), 0,
            f"SSOT VIOLATION: Found {len(non_canonical_usages)} non-canonical import usages. "
            f"Files with violations: {list(set(u['file'] for u in non_canonical_usages))}"
        )
    
    def test_websocket_factory_import_determinism_violation(self):
        """
        CRITICAL: Test detecting non-deterministic factory import behavior.
        
        This test MUST FAIL because:
        - Factory creation depends on import order
        - Different factory instances returned from different imports
        - User isolation compromised by import-dependent factory behavior
        
        After SSOT fix, should PASS with deterministic factory imports.
        """
        # Test factory import determinism
        factory_determinism_violations = self._test_factory_import_determinism()
        
        print(f"\nDETECTED FACTORY IMPORT DETERMINISM VIOLATIONS: {len(factory_determinism_violations)}")
        for violation in factory_determinism_violations:
            print(f"  - {violation['test_scenario']}: {violation['violation_type']}")
            print(f"    Details: {violation['details']}")
        
        # This assertion SHOULD FAIL with current determinism violations
        self.assertEqual(
            len(factory_determinism_violations), 0,
            f"SSOT VIOLATION: Found {len(factory_determinism_violations)} factory import determinism violations. "
            f"Violations: {[v['test_scenario'] for v in factory_determinism_violations]}"
        )
    
    def _discover_manager_import_paths(self) -> List[Dict]:
        """Discover all possible import paths for WebSocket manager functionality."""
        import_paths = []
        
        # Search for WebSocket manager classes and their import paths
        search_patterns = [
            'websocket/connection_manager.py',
            'websocket_core/manager.py',
            'websocket_core/unified_manager.py',
            'websocket_core/websocket_manager.py'
        ]
        
        for pattern in search_patterns:
            file_path = self.backend_root / "app" / pattern
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to find manager classes
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if ('manager' in node.name.lower() and 
                                ('websocket' in node.name.lower() or 
                                 'connection' in node.name.lower())):
                                
                                import_path = f"netra_backend.app.{pattern.replace('.py', '').replace('/', '.')}"
                                import_paths.append({
                                    'import_path': import_path,
                                    'class_name': node.name,
                                    'file': str(file_path.relative_to(self.backend_root))
                                })
                                
                except Exception as e:
                    # Skip files that can't be parsed
                    continue
        
        return import_paths
    
    def _analyze_import_resolution_consistency(self) -> List[Dict]:
        """Analyze consistency of import resolution across modules."""
        inconsistencies = []
        
        # Map functionality to different import paths used
        functionality_imports = {}
        
        # Search all Python files for WebSocket imports
        for py_file in self.backend_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse imports
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        import_info = self._extract_import_info(node)
                        if import_info and 'websocket' in import_info['module'].lower():
                            
                            # Extract functionality being imported
                            functionality = self._extract_functionality(import_info)
                            if functionality:
                                if functionality not in functionality_imports:
                                    functionality_imports[functionality] = set()
                                functionality_imports[functionality].add(import_info['module'])
                                
            except Exception:
                continue
        
        # Find functionalities with multiple import paths
        for functionality, import_paths in functionality_imports.items():
            if len(import_paths) > 1:
                inconsistencies.append({
                    'functionality': functionality,
                    'conflicting_paths': list(import_paths)
                })
        
        return inconsistencies
    
    def _detect_circular_import_dependencies(self) -> List[Dict]:
        """Detect circular import dependencies between WebSocket modules."""
        circular_deps = []
        
        # Build import dependency graph
        import_graph = {}
        websocket_modules = []
        
        # Find all WebSocket modules
        for pattern in ['websocket/**/*.py', 'websocket_core/**/*.py']:
            for py_file in self.backend_root.glob(f"app/{pattern}"):
                if py_file.is_file():
                    module_path = f"netra_backend.app.{py_file.relative_to(self.backend_root / 'app').with_suffix('').as_posix().replace('/', '.')}"
                    websocket_modules.append(module_path)
                    import_graph[module_path] = set()
                    
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Parse imports
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ImportFrom):
                                if node.module and 'websocket' in node.module:
                                    import_graph[module_path].add(node.module)
                                    
                    except Exception:
                        continue
        
        # Detect cycles using DFS
        def has_cycle(start_module, current_module, visited, path):
            if current_module in visited:
                if current_module == start_module:
                    return path + [current_module]
                return None
            
            visited.add(current_module)
            path.append(current_module)
            
            for imported_module in import_graph.get(current_module, []):
                if imported_module in websocket_modules:
                    cycle = has_cycle(start_module, imported_module, visited.copy(), path.copy())
                    if cycle:
                        return cycle
            
            return None
        
        # Check each module for cycles
        for module in websocket_modules:
            cycle = has_cycle(module, module, set(), [])
            if cycle and len(cycle) > 1:
                circular_deps.append({
                    'module_a': cycle[0],
                    'module_b': cycle[-1],
                    'cycle_path': cycle
                })
        
        return circular_deps
    
    def _find_non_canonical_import_usages(self) -> List[Dict]:
        """Find all non-canonical import usages in the codebase."""
        non_canonical_usages = []
        
        # Define non-canonical patterns and their canonical alternatives
        non_canonical_patterns = {
            'netra_backend.app.websocket.connection_manager': 'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket.connection_info': 'netra_backend.app.websocket_core.connection_info',
            r'from.*websocket\.connection_manager': 'from netra_backend.app.websocket_core.websocket_manager',
            r'from.*websocket\.': 'from netra_backend.app.websocket_core.'
        }
        
        # Search all Python files
        for py_file in self.backend_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern, canonical in non_canonical_patterns.items():
                        if pattern in line and 'import' in line:
                            non_canonical_usages.append({
                                'file': str(py_file.relative_to(self.backend_root)),
                                'line': line_num,
                                'import_statement': line.strip(),
                                'canonical_alternative': canonical
                            })
                            
            except Exception:
                continue
        
        return non_canonical_usages
    
    def _test_factory_import_determinism(self) -> List[Dict]:
        """Test determinism of factory imports across different import orders."""
        violations = []
        
        # Test scenarios for import determinism
        test_scenarios = [
            {
                'name': 'legacy_first_import_order',
                'imports': [
                    'netra_backend.app.websocket.connection_manager',
                    'netra_backend.app.websocket_core.manager'
                ]
            },
            {
                'name': 'core_first_import_order', 
                'imports': [
                    'netra_backend.app.websocket_core.manager',
                    'netra_backend.app.websocket.connection_manager'
                ]
            }
        ]
        
        for scenario in test_scenarios:
            try:
                # Clear module cache for clean test
                modules_to_clear = [mod for mod in sys.modules.keys() if 'websocket' in mod]
                for mod in modules_to_clear:
                    if mod in sys.modules:
                        del sys.modules[mod]
                
                # Import modules in specific order
                factory_instances = []
                for import_path in scenario['imports']:
                    try:
                        module = importlib.import_module(import_path)
                        
                        # Try to get manager factory/instance
                        if hasattr(module, 'get_manager'):
                            factory_instances.append(id(module.get_manager))
                        elif hasattr(module, 'ConnectionManager'):
                            factory_instances.append(id(module.ConnectionManager))
                        elif hasattr(module, 'WebSocketManager'):
                            factory_instances.append(id(module.WebSocketManager))
                            
                    except Exception as e:
                        violations.append({
                            'test_scenario': scenario['name'],
                            'violation_type': 'import_failure',
                            'details': f"Failed to import {import_path}: {str(e)}"
                        })
                
                # Check if factory instances are different (violation)
                if len(set(factory_instances)) > 1:
                    violations.append({
                        'test_scenario': scenario['name'],
                        'violation_type': 'non_deterministic_factory',
                        'details': f"Different factory instances: {factory_instances}"
                    })
                    
            except Exception as e:
                violations.append({
                    'test_scenario': scenario['name'],
                    'violation_type': 'test_execution_failure',
                    'details': str(e)
                })
        
        return violations
    
    def _extract_import_info(self, node) -> Dict:
        """Extract import information from AST node."""
        if isinstance(node, ast.ImportFrom):
            return {
                'type': 'from_import',
                'module': node.module or '',
                'names': [alias.name for alias in node.names] if node.names else []
            }
        elif isinstance(node, ast.Import):
            return {
                'type': 'import',
                'module': node.names[0].name if node.names else '',
                'names': [alias.name for alias in node.names] if node.names else []
            }
        return None
    
    def _extract_functionality(self, import_info: Dict) -> str:
        """Extract functionality name from import information."""
        if 'manager' in import_info['module'].lower():
            return 'websocket_manager'
        elif 'connection' in import_info['module'].lower():
            return 'connection_handler'
        elif 'auth' in import_info['module'].lower():
            return 'auth_handler'
        return None


if __name__ == '__main__':
    # Run with verbose output to show violation details
    unittest.main(verbosity=2)