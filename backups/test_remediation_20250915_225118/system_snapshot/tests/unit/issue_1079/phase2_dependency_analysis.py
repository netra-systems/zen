#!/usr/bin/env python3
"""
Issue #1079 Phase 2: Dependency Analysis Test

This test analyzes the dependency chains that lead to import failures:
- Maps import dependencies for problematic modules
- Identifies circular dependency patterns
- Analyzes execution time patterns
- Validates import path resolution
"""

import sys
import time
import unittest
import importlib
import importlib.util
from pathlib import Path
import ast
import traceback

class DependencyAnalysisTest(unittest.TestCase):
    """Phase 2: Analyze dependency chains causing import failures"""

    def setUp(self):
        """Set up dependency analysis"""
        self.dependency_map = {}
        self.import_times = {}
        self.circular_patterns = []
        self.missing_modules = []

        # Core netra_backend path
        self.backend_path = Path("netra_backend")

    def test_analyze_supply_database_manager_dependencies(self):
        """Analyze why supply_database_manager import fails"""
        print("\n=== Phase 2.1: Analyzing supply_database_manager dependencies ===")

        # Check if the file actually exists
        expected_path = self.backend_path / "app" / "db" / "supply_database_manager.py"
        print(f"Checking path: {expected_path}")

        if expected_path.exists():
            print(f"✓ File exists at: {expected_path}")

            # Analyze the file's imports
            try:
                with open(expected_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                imports = self._extract_imports(tree)

                print(f"Found {len(imports)} imports in supply_database_manager:")
                for imp in imports:
                    print(f"  - {imp}")

                self.dependency_map['supply_database_manager'] = imports

            except Exception as e:
                print(f"✗ Failed to analyze file: {e}")

        else:
            print(f"✗ File does not exist: {expected_path}")
            # Check what files do exist in the db directory
            db_dir = self.backend_path / "app" / "db"
            if db_dir.exists():
                print(f"Files in {db_dir}:")
                for file in db_dir.iterdir():
                    if file.is_file():
                        print(f"  - {file.name}")
            else:
                print(f"Directory does not exist: {db_dir}")

            self.missing_modules.append('supply_database_manager')

    def test_analyze_agent_class_dependencies(self):
        """Analyze agent class import chain"""
        print("\n=== Phase 2.2: Analyzing agent class dependencies ===")

        agent_modules = [
            "netra_backend/app/agents/base_agent.py",
            "netra_backend/app/agents/supervisor_agent_modern.py",
            "netra_backend/app/agents/registry.py"
        ]

        for module_path in agent_modules:
            file_path = Path(module_path)
            print(f"\nAnalyzing: {file_path}")

            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    tree = ast.parse(content)
                    imports = self._extract_imports(tree)
                    classes = self._extract_classes(tree)

                    print(f"  Classes defined: {classes}")
                    print(f"  Imports: {len(imports)}")

                    # Check for Agent class specifically
                    if 'Agent' in classes:
                        print(f"  ✓ Agent class found in {file_path}")
                    else:
                        print(f"  ✗ Agent class NOT found in {file_path}")

                    self.dependency_map[file_path.stem] = {
                        'imports': imports,
                        'classes': classes
                    }

                except Exception as e:
                    print(f"  ✗ Failed to analyze {file_path}: {e}")

            else:
                print(f"  ✗ File does not exist: {file_path}")
                self.missing_modules.append(str(file_path))

    def test_analyze_circular_import_patterns(self):
        """Analyze potential circular import patterns"""
        print("\n=== Phase 2.3: Analyzing circular import patterns ===")

        # Build import graph for agent modules
        agent_dir = Path("netra_backend/app/agents")
        if agent_dir.exists():
            agent_files = list(agent_dir.glob("*.py"))
            print(f"Found {len(agent_files)} agent files")

            import_graph = {}

            for file_path in agent_files:
                if file_path.name.startswith('__'):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    tree = ast.parse(content)
                    imports = self._extract_imports(tree)

                    # Filter for internal agent imports
                    agent_imports = [
                        imp for imp in imports
                        if 'netra_backend.app.agents' in imp
                    ]

                    import_graph[file_path.stem] = agent_imports
                    print(f"  {file_path.stem}: {len(agent_imports)} agent imports")

                except Exception as e:
                    print(f"  ✗ Failed to analyze {file_path}: {e}")

            # Detect circular patterns
            self._detect_circular_imports(import_graph)

        else:
            print(f"✗ Agent directory not found: {agent_dir}")

    def test_measure_import_performance(self):
        """Measure import performance for problematic modules"""
        print("\n=== Phase 2.4: Measuring import performance ===")

        test_modules = [
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.agents.supervisor_agent_modern",
            "netra_backend.app.db.database_manager",
            "netra_backend.app.core.configuration.base"
        ]

        for module_name in test_modules:
            print(f"\nTesting import performance: {module_name}")

            # Clear module cache
            if module_name in sys.modules:
                del sys.modules[module_name]

            start_time = time.time()

            try:
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    print(f"  ✗ Module spec not found: {module_name}")
                    continue

                if spec.loader is None:
                    print(f"  ✗ Module loader not found: {module_name}")
                    continue

                # Try to load the module
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module

                load_start = time.time()
                spec.loader.exec_module(module)
                load_time = time.time() - load_start

                total_time = time.time() - start_time

                print(f"  ✓ Import successful:")
                print(f"    Total time: {total_time:.3f}s")
                print(f"    Exec time: {load_time:.3f}s")

                self.import_times[module_name] = {
                    'total': total_time,
                    'exec': load_time,
                    'status': 'success'
                }

                # Check for timeout risk
                if total_time > 5.0:
                    print(f"  ⚠️  SLOW IMPORT: {total_time:.3f}s (timeout risk)")

            except Exception as e:
                duration = time.time() - start_time
                print(f"  ✗ Import failed after {duration:.3f}s: {type(e).__name__}: {e}")

                self.import_times[module_name] = {
                    'total': duration,
                    'exec': 0,
                    'status': 'failed',
                    'error': str(e)
                }

    def test_validate_import_paths(self):
        """Validate import path resolution"""
        print("\n=== Phase 2.5: Validating import paths ===")

        # Test problematic import paths
        test_paths = [
            "netra_backend.app.db.supply_database_manager",
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.agents.supervisor_agent_modern",
            "netra_backend.app.agents.registry"
        ]

        for path in test_paths:
            print(f"\nValidating: {path}")

            try:
                spec = importlib.util.find_spec(path)
                if spec is None:
                    print(f"  ✗ Spec not found")
                    continue

                print(f"  ✓ Spec found: {spec}")
                print(f"    Origin: {spec.origin}")
                print(f"    Loader: {type(spec.loader).__name__}")

                if spec.origin:
                    origin_path = Path(spec.origin)
                    if origin_path.exists():
                        print(f"    ✓ File exists: {origin_path}")
                        file_size = origin_path.stat().st_size
                        print(f"    File size: {file_size} bytes")
                    else:
                        print(f"    ✗ File missing: {origin_path}")

            except Exception as e:
                print(f"  ✗ Validation failed: {type(e).__name__}: {e}")

    def _extract_imports(self, tree):
        """Extract import statements from AST"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def _extract_classes(self, tree):
        """Extract class definitions from AST"""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)

        return classes

    def _detect_circular_imports(self, import_graph):
        """Detect circular import patterns"""
        print("\n  Analyzing circular import patterns:")

        def find_cycles(graph, start, path=None):
            if path is None:
                path = []

            path = path + [start]

            if start not in graph:
                return []

            cycles = []
            for neighbor in graph[start]:
                neighbor_module = neighbor.split('.')[-1]  # Get module name

                if neighbor_module in path:
                    cycle = path[path.index(neighbor_module):] + [neighbor_module]
                    cycles.append(cycle)
                else:
                    cycles.extend(find_cycles(graph, neighbor_module, path))

            return cycles

        all_cycles = []
        for module in import_graph:
            cycles = find_cycles(import_graph, module)
            all_cycles.extend(cycles)

        # Remove duplicates
        unique_cycles = []
        for cycle in all_cycles:
            if cycle not in unique_cycles:
                unique_cycles.append(cycle)

        if unique_cycles:
            print(f"  ✗ Found {len(unique_cycles)} circular import patterns:")
            for i, cycle in enumerate(unique_cycles):
                print(f"    {i+1}. {' -> '.join(cycle)}")
                self.circular_patterns.append(cycle)
        else:
            print(f"  ✓ No circular import patterns detected")

    def tearDown(self):
        """Report dependency analysis results"""
        print("\n" + "="*60)
        print("PHASE 2 DEPENDENCY ANALYSIS SUMMARY")
        print("="*60)

        print(f"Analyzed dependencies: {len(self.dependency_map)}")
        for module, deps in self.dependency_map.items():
            if isinstance(deps, list):
                print(f"  {module}: {len(deps)} imports")
            else:
                print(f"  {module}: {len(deps.get('imports', []))} imports, {len(deps.get('classes', []))} classes")

        print(f"\nMissing modules: {len(self.missing_modules)}")
        for module in self.missing_modules:
            print(f"  - {module}")

        print(f"\nCircular patterns: {len(self.circular_patterns)}")
        for pattern in self.circular_patterns:
            print(f"  - {' -> '.join(pattern)}")

        print(f"\nImport performance:")
        for module, timing in self.import_times.items():
            status = timing['status']
            total_time = timing['total']
            print(f"  {module}: {status} ({total_time:.3f}s)")

if __name__ == "__main__":
    print("="*60)
    print("ISSUE #1079 PHASE 2: DEPENDENCY ANALYSIS")
    print("="*60)
    print("This test analyzes the dependency chains causing import failures:")
    print("- Import dependency mapping")
    print("- Circular dependency detection")
    print("- Import performance measurement")
    print("- Import path validation")
    print("="*60)

    unittest.main(verbosity=2)