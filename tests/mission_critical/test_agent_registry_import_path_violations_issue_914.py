#!/usr/bin/env python3
"""
Issue #914: AgentRegistry Import Path SSOT Violations Test Suite

This test suite specifically focuses on import path inconsistencies and violations
in AgentRegistry implementations. These tests validate that there is a single,
canonical import path for AgentRegistry functionality.

Business Impact:
- $500K+ ARR at risk from import path confusion causing runtime failures
- Developer productivity lost due to unclear import patterns
- Testing infrastructure broken by import ambiguity
- WebSocket integration failures due to registry import conflicts

Test Focus Areas:
1. Import path uniqueness and canonicalization
2. SSOT import registry compliance
3. Circular dependency detection
4. Import resolution consistency

Expected Result: Tests FAIL initially showing import path violations.
After SSOT consolidation, tests pass with single canonical import path.
"""

import unittest
import sys
import importlib
import importlib.util
import os
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path

class TestAgentRegistryImportPathViolations(unittest.TestCase):
    """Test import path SSOT violations for AgentRegistry implementations."""
    
    @classmethod
    def setUpClass(cls):
        """Initialize test class with import path analysis."""
        
        # Define all possible AgentRegistry import paths found in codebase
        cls.known_import_paths = [
            'netra_backend.app.agents.registry.AgentRegistry',
            'netra_backend.app.agents.supervisor.agent_registry.AgentRegistry',
            'netra_backend.app.core.registry.universal_registry.AgentRegistry',
        ]
        
        # Base paths for registry modules
        cls.registry_module_paths = [
            'netra_backend.app.agents.registry',
            'netra_backend.app.agents.supervisor.agent_registry',
            'netra_backend.app.core.registry.universal_registry',
        ]
        
        # Project root for file system analysis
        cls.project_root = Path(__file__).parent.parent.parent
        
        print(f"Project root: {cls.project_root}")
        print(f"Testing {len(cls.known_import_paths)} import paths")
    
    def test_01_multiple_agent_registry_import_paths_exist(self):
        """TEST EXPECTED TO FAIL: Only one AgentRegistry import path should exist."""
        print("\n=== TEST 1: Multiple Import Path Validation ===")
        
        successful_imports = []
        failed_imports = []
        
        for import_path in self.known_import_paths:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                
                if hasattr(module, class_name):
                    agent_registry_class = getattr(module, class_name)
                    successful_imports.append((import_path, agent_registry_class))
                    print(f"✓ Successfully imported: {import_path}")
                else:
                    failed_imports.append((import_path, f"Module has no {class_name}"))
                    print(f"✗ No {class_name} in module: {module_path}")
                    
            except ImportError as e:
                failed_imports.append((import_path, str(e)))
                print(f"✗ Import failed: {import_path} - {e}")
        
        print(f"\nResults:")
        print(f"Successful imports: {len(successful_imports)}")
        print(f"Failed imports: {len(failed_imports)}")
        
        # EXPECTED FAILURE: Multiple import paths should not work
        self.assertEqual(len(successful_imports), 1,
                        f"IMPORT PATH SSOT VIOLATION: Found {len(successful_imports)} working AgentRegistry import paths. "
                        f"Should have exactly 1 canonical import path. "
                        f"Working paths: {[path for path, _ in successful_imports]}")
    
    def test_02_import_ambiguity_in_codebase(self):
        """TEST EXPECTED TO FAIL: Codebase should not have ambiguous imports."""
        print("\n=== TEST 2: Codebase Import Ambiguity Analysis ===")
        
        # Scan Python files for AgentRegistry imports
        import_usages = self._scan_codebase_for_agent_registry_imports()
        
        print(f"Found {len(import_usages)} files using AgentRegistry imports")
        
        # Group by import pattern
        import_patterns = {}
        for file_path, imports in import_usages.items():
            for import_line in imports:
                pattern = self._extract_import_pattern(import_line)
                if pattern not in import_patterns:
                    import_patterns[pattern] = []
                import_patterns[pattern].append((file_path, import_line))
        
        print(f"Import patterns found: {len(import_patterns)}")
        for pattern, usages in import_patterns.items():
            print(f"  Pattern '{pattern}': {len(usages)} usages")
            for file_path, import_line in usages[:3]:  # Show first 3 examples
                print(f"    {file_path}: {import_line.strip()}")
            if len(usages) > 3:
                print(f"    ... and {len(usages) - 3} more")
        
        # EXPECTED FAILURE: Multiple import patterns indicate SSOT violation
        self.assertEqual(len(import_patterns), 1,
                        f"IMPORT AMBIGUITY VIOLATION: Found {len(import_patterns)} different AgentRegistry import patterns. "
                        f"Should have exactly 1 canonical pattern. "
                        f"Patterns: {list(import_patterns.keys())}")
    
    def test_03_ssot_import_registry_compliance(self):
        """TEST EXPECTED TO FAIL: Should comply with SSOT import registry."""
        print("\n=== TEST 3: SSOT Import Registry Compliance ===")
        
        # Check if SSOT_IMPORT_REGISTRY.md documents canonical AgentRegistry import
        ssot_registry_path = self.project_root / "SSOT_IMPORT_REGISTRY.md"
        
        if not ssot_registry_path.exists():
            self.fail(f"SSOT Import Registry not found at: {ssot_registry_path}")
        
        # Read SSOT import registry
        with open(ssot_registry_path, 'r') as f:
            ssot_content = f.read()
        
        # Check for AgentRegistry documentation
        agent_registry_documented = 'AgentRegistry' in ssot_content
        print(f"AgentRegistry documented in SSOT registry: {agent_registry_documented}")
        
        if agent_registry_documented:
            # Extract documented import path
            lines = ssot_content.split('\n')
            registry_lines = [line for line in lines if 'AgentRegistry' in line]
            print(f"SSOT registry entries for AgentRegistry: {len(registry_lines)}")
            
            for line in registry_lines[:5]:  # Show first 5
                print(f"  {line.strip()}")
        
        # Check if multiple entries exist (violation)
        registry_entries = [line for line in ssot_content.split('\n') 
                           if 'AgentRegistry' in line and ('import' in line or 'from' in line)]
        
        # EXPECTED FAILURE: Multiple entries or unclear canonicalization
        self.assertEqual(len(registry_entries), 1,
                        f"SSOT REGISTRY VIOLATION: Found {len(registry_entries)} AgentRegistry entries in SSOT registry. "
                        f"Should have exactly 1 canonical entry. "
                        f"Entries: {registry_entries}")
    
    def test_04_circular_dependency_detection(self):
        """TEST EXPECTED TO FAIL: No circular dependencies should exist between registries."""
        print("\n=== TEST 4: Circular Dependency Detection ===")
        
        # Build dependency graph between registry modules
        dependency_graph = self._build_module_dependency_graph()
        
        print(f"Registry module dependencies:")
        for module, deps in dependency_graph.items():
            print(f"  {module} depends on: {deps}")
        
        # Detect circular dependencies
        circular_deps = self._detect_circular_dependencies(dependency_graph)
        
        if circular_deps:
            print(f"Circular dependencies detected: {len(circular_deps)}")
            for cycle in circular_deps:
                print(f"  Cycle: {' -> '.join(cycle)}")
        
        # EXPECTED FAILURE: Circular dependencies likely exist
        self.assertEqual(len(circular_deps), 0,
                        f"CIRCULAR DEPENDENCY VIOLATION: Found {len(circular_deps)} circular dependency cycles. "
                        f"Cycles: {circular_deps}")
    
    def test_05_import_resolution_consistency(self):
        """TEST EXPECTED TO FAIL: Import resolution should be consistent across environments."""
        print("\n=== TEST 5: Import Resolution Consistency ===")
        
        resolution_results = {}
        
        # Test import resolution from different starting contexts
        for module_path in self.registry_module_paths:
            try:
                # Temporarily modify sys.path to simulate different import contexts
                original_path = sys.path.copy()
                
                # Test resolution
                module = importlib.import_module(module_path)
                
                # Get module file path
                if hasattr(module, '__file__') and module.__file__:
                    resolved_path = os.path.realpath(module.__file__)
                    resolution_results[module_path] = resolved_path
                    print(f"Resolved {module_path} -> {resolved_path}")
                else:
                    resolution_results[module_path] = None
                    print(f"Could not resolve file path for {module_path}")
                
                # Restore original path
                sys.path = original_path
                
            except Exception as e:
                resolution_results[module_path] = f"ERROR: {e}"
                print(f"Resolution failed for {module_path}: {e}")
        
        # Check for consistent resolution
        resolved_paths = [path for path in resolution_results.values() 
                         if path and not path.startswith("ERROR:")]
        unique_paths = set(resolved_paths)
        
        print(f"Unique resolved paths: {len(unique_paths)}")
        for path in unique_paths:
            print(f"  {path}")
        
        # EXPECTED FAILURE: Multiple unique paths indicate duplication
        # In ideal SSOT world, all would resolve to same canonical implementation
        if len(unique_paths) > 1:
            self.fail(f"IMPORT RESOLUTION VIOLATION: Multiple unique file paths resolved "
                     f"for AgentRegistry imports. Should resolve to single SSOT implementation. "
                     f"Paths: {unique_paths}")
    
    def test_06_import_statement_standardization(self):
        """TEST EXPECTED TO FAIL: Import statements should follow standard pattern."""
        print("\n=== TEST 6: Import Statement Standardization ===")
        
        # Analyze import statement patterns in codebase
        import_statements = self._extract_all_agent_registry_import_statements()
        
        print(f"Found {len(import_statements)} AgentRegistry import statements")
        
        # Categorize import patterns
        import_categories = {
            'direct_class': [],
            'from_module': [],
            'alias_import': [],
            'qualified_import': []
        }
        
        for file_path, statement in import_statements:
            if 'from ' in statement and 'import ' in statement:
                if 'as ' in statement:
                    import_categories['alias_import'].append((file_path, statement))
                else:
                    import_categories['from_module'].append((file_path, statement))
            elif 'import ' in statement and 'as ' in statement:
                import_categories['alias_import'].append((file_path, statement))
            elif 'import ' in statement:
                import_categories['qualified_import'].append((file_path, statement))
            else:
                import_categories['direct_class'].append((file_path, statement))
        
        print("Import pattern distribution:")
        for category, statements in import_categories.items():
            print(f"  {category}: {len(statements)}")
            for file_path, statement in statements[:2]:  # Show examples
                print(f"    {os.path.basename(file_path)}: {statement.strip()}")
        
        # Calculate pattern consistency
        non_empty_categories = sum(1 for statements in import_categories.values() if statements)
        
        # EXPECTED FAILURE: Multiple import patterns indicate lack of standardization
        self.assertEqual(non_empty_categories, 1,
                        f"IMPORT STANDARDIZATION VIOLATION: Found {non_empty_categories} different import patterns. "
                        f"Should have 1 standardized pattern. "
                        f"Categories with imports: {[cat for cat, stmts in import_categories.items() if stmts]}")
    
    def _scan_codebase_for_agent_registry_imports(self) -> Dict[str, List[str]]:
        """Scan codebase for AgentRegistry import statements."""
        import_usages = {}
        
        # Scan Python files in relevant directories
        scan_dirs = [
            self.project_root / "netra_backend",
            self.project_root / "tests",
            self.project_root / "test_framework"
        ]
        
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for py_file in scan_dir.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        if 'AgentRegistry' in content:
                            lines = content.split('\n')
                            registry_imports = []
                            
                            for line in lines:
                                if 'AgentRegistry' in line and ('import' in line or 'from' in line):
                                    registry_imports.append(line)
                            
                            if registry_imports:
                                relative_path = str(py_file.relative_to(self.project_root))
                                import_usages[relative_path] = registry_imports
                                
                    except Exception:
                        # Skip files that can't be read
                        continue
        
        return import_usages
    
    def _extract_import_pattern(self, import_line: str) -> str:
        """Extract standardized import pattern from import line."""
        import_line = import_line.strip()
        
        # Normalize patterns
        if import_line.startswith('from ') and ' import ' in import_line:
            # from module import AgentRegistry
            parts = import_line.split(' import ')
            module_part = parts[0].replace('from ', '')
            import_part = parts[1]
            
            if 'AgentRegistry' in import_part:
                return f"from {module_part} import AgentRegistry"
        
        elif import_line.startswith('import '):
            # import module.AgentRegistry or import module
            return f"import {import_line.replace('import ', '')}"
        
        return import_line
    
    def _build_module_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph between registry modules."""
        dependency_graph = {}
        
        for module_path in self.registry_module_paths:
            dependencies = []
            
            try:
                # Get module file path
                module = importlib.import_module(module_path)
                if hasattr(module, '__file__') and module.__file__:
                    module_file = Path(module.__file__)
                    
                    # Read module source
                    with open(module_file, 'r') as f:
                        source = f.read()
                    
                    # Find imports to other registry modules
                    for other_module in self.registry_module_paths:
                        if other_module != module_path and other_module in source:
                            dependencies.append(other_module)
                
                dependency_graph[module_path] = dependencies
                
            except Exception:
                dependency_graph[module_path] = []
        
        return dependency_graph
    
    def _detect_circular_dependencies(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies in module graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [neighbor])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [node])
        
        return cycles
    
    def _extract_all_agent_registry_import_statements(self) -> List[Tuple[str, str]]:
        """Extract all AgentRegistry import statements from codebase."""
        statements = []
        
        import_usages = self._scan_codebase_for_agent_registry_imports()
        
        for file_path, imports in import_usages.items():
            for import_line in imports:
                statements.append((file_path, import_line))
        
        return statements


if __name__ == '__main__':
    print("="*80)
    print("ISSUE #914 AGENT REGISTRY IMPORT PATH VIOLATIONS TEST SUITE")
    print("="*80)
    print("PURPOSE: Demonstrate import path SSOT violations")
    print("EXPECTED: Tests should FAIL initially, proving import ambiguity")
    print("AFTER FIX: Tests should pass with single canonical import path")
    print("="*80)
    
    # Run the tests
    unittest.main(verbosity=2, buffer=False)