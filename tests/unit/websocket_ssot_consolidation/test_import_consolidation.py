"""
Test WebSocket SSOT Consolidation - Import Pattern Analysis

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: Reduce import confusion and circular dependency risk
- Value Impact: Clear import paths = fewer bugs = more reliable chat functionality
- Strategic Impact: Import clarity enables faster onboarding and development

PURPOSE: Measure import fragmentation and validate consolidation approach
Tests the import complexity that makes WebSocket development confusing.
"""

import pytest
import ast
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketImportConsolidation(SSotBaseTestCase, unittest.TestCase):
    """Test WebSocket import patterns to validate SSOT consolidation benefits."""

    def setUp(self):
        """Set up import analysis infrastructure."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.websocket_modules = self._discover_websocket_modules()

    def _discover_websocket_modules(self) -> List[Path]:
        """Discover all WebSocket-related Python modules."""
        websocket_patterns = [
            "websocket_core",
            "websocket",
            "routes/websocket",
        ]

        modules = []
        for pattern in websocket_patterns:
            pattern_path = self.project_root / "netra_backend" / "app"
            if "/" in pattern:
                parts = pattern.split("/")
                pattern_path = pattern_path.joinpath(*parts[:-1])
                if pattern_path.exists():
                    for py_file in pattern_path.glob(f"{parts[-1]}*.py"):
                        modules.append(py_file)
            else:
                pattern_path = pattern_path / pattern
                if pattern_path.exists():
                    for py_file in pattern_path.glob("*.py"):
                        modules.append(py_file)

        return [m for m in modules if m.is_file()]

    @pytest.mark.unit
    def test_websocket_import_discovery(self):
        """Test that we can discover WebSocket modules for analysis."""
        print(f"\n=== WebSocket Module Discovery ===")
        print(f"Found {len(self.websocket_modules)} WebSocket modules:")
        for module in self.websocket_modules:
            print(f"  {module.relative_to(self.project_root)}")

        self.assertGreater(len(self.websocket_modules), 2,
            "Should discover multiple WebSocket modules to analyze")

    @pytest.mark.unit
    def test_import_fragmentation_analysis(self):
        """Test import fragmentation across WebSocket modules."""
        import_sources = {}  # What each module imports
        import_targets = {}  # What imports each module
        all_imports = set()

        for module_path in self.websocket_modules:
            try:
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                module_imports = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module_imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_imports.add(node.module)

                # Filter for local imports (our codebase)
                local_imports = {imp for imp in module_imports
                               if any(imp.startswith(prefix) for prefix in
                                     ['netra_backend', 'auth_service', 'shared', 'test_framework'])}

                import_sources[module_path.name] = local_imports
                all_imports.update(local_imports)

            except Exception as e:
                print(f"Could not analyze {module_path}: {e}")

        print(f"\n=== Import Fragmentation Analysis ===")
        print(f"Total unique local imports: {len(all_imports)}")
        print(f"Modules with imports: {len(import_sources)}")

        # Identify fragmentation patterns
        common_imports = {}
        for module, imports in import_sources.items():
            for imp in imports:
                common_imports.setdefault(imp, []).append(module)

        # Find imports used by multiple modules (fragmentation indicators)
        fragmented_imports = {imp: modules for imp, modules in common_imports.items()
                            if len(modules) > 1}

        print(f"Fragmented imports (used by multiple modules): {len(fragmented_imports)}")
        for imp, modules in list(fragmented_imports.items())[:10]:  # Top 10
            print(f"  {imp}: {len(modules)} modules")

        # Calculate fragmentation metrics
        avg_imports_per_module = len(all_imports) / len(import_sources) if import_sources else 0
        fragmentation_factor = len(fragmented_imports) / len(all_imports) if all_imports else 0

        print(f"Average imports per module: {avg_imports_per_module:.1f}")
        print(f"Fragmentation factor: {fragmentation_factor:.2f}")

        # Business thresholds for import complexity
        self.assertGreater(len(fragmented_imports), 5,
            "Should have fragmented imports demonstrating consolidation opportunity")
        self.assertGreater(fragmentation_factor, 0.3,
            "Fragmentation factor should justify SSOT approach")

    @pytest.mark.unit
    def test_circular_dependency_risk_analysis(self):
        """Test potential circular dependency risks in current import structure."""
        import_graph = {}  # module -> list of modules it imports

        for module_path in self.websocket_modules:
            try:
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                module_name = module_path.stem

                imported_modules = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and any(node.module.startswith(prefix) for prefix in
                                             ['netra_backend.app.websocket', 'netra_backend.app.routes']):
                            # Extract the module name
                            parts = node.module.split('.')
                            if len(parts) >= 3:
                                imported_modules.add(parts[-1])

                import_graph[module_name] = imported_modules

            except Exception as e:
                print(f"Could not analyze {module_path} for circular deps: {e}")

        print(f"\n=== Circular Dependency Risk Analysis ===")
        print(f"Import graph: {len(import_graph)} modules")

        # Look for potential circular dependencies
        potential_cycles = []
        for module, imports in import_graph.items():
            for imported in imports:
                if imported in import_graph and module in import_graph[imported]:
                    potential_cycles.append((module, imported))

        # Look for longer cycles (A -> B -> C -> A)
        def find_path(graph, start, end, path=[]):
            path = path + [start]
            if start == end:
                return path
            if start not in graph:
                return None
            for node in graph[start]:
                if node not in path:
                    extended_path = find_path(graph, node, end, path)
                    if extended_path:
                        return extended_path
            return None

        complex_cycles = []
        for module in import_graph:
            for imported in import_graph[module]:
                cycle_path = find_path(import_graph, imported, module)
                if cycle_path and len(cycle_path) > 2:
                    complex_cycles.append(cycle_path)

        print(f"Direct circular imports: {len(potential_cycles)}")
        print(f"Complex circular paths: {len(complex_cycles)}")

        for cycle in potential_cycles:
            print(f"  {cycle[0]} <-> {cycle[1]}")

        for cycle in complex_cycles[:3]:  # Show first 3
            print(f"  Complex: {' -> '.join(cycle)}")

        # Risk assessment
        total_risk_indicators = len(potential_cycles) + len(complex_cycles)

        print(f"Total circular dependency risk indicators: {total_risk_indicators}")

        # This measures current risk that SSOT consolidation would reduce
        if total_risk_indicators > 0:
            print("⚠️  Circular dependency risks detected - SSOT consolidation would help")

    @pytest.mark.unit
    def test_import_path_consistency_analysis(self):
        """Test consistency of import paths across WebSocket modules."""
        import_patterns = {}  # pattern -> list of variations

        for module_path in self.websocket_modules:
            try:
                with open(module_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line in lines:
                    line = line.strip()
                    if line.startswith('from ') and 'websocket' in line:
                        # Extract the import pattern
                        if ' import ' in line:
                            module_part = line.split(' import ')[0].replace('from ', '')
                            # Group by pattern family
                            if 'websocket_core' in module_part:
                                pattern = 'websocket_core'
                            elif 'routes' in module_part and 'websocket' in module_part:
                                pattern = 'routes_websocket'
                            else:
                                pattern = 'other_websocket'

                            import_patterns.setdefault(pattern, set()).add(module_part)

            except Exception as e:
                print(f"Could not analyze import patterns in {module_path}: {e}")

        print(f"\n=== Import Path Consistency Analysis ===")

        # Calculate consistency metrics
        inconsistency_score = 0
        for pattern, variations in import_patterns.items():
            variation_count = len(variations)
            print(f"{pattern}: {variation_count} variations")
            for variation in variations:
                print(f"  {variation}")

            if variation_count > 1:
                inconsistency_score += variation_count - 1  # Extra variations are inconsistencies

        total_patterns = sum(len(variations) for variations in import_patterns.values())
        consistency_ratio = 1 - (inconsistency_score / total_patterns) if total_patterns > 0 else 1

        print(f"Inconsistency score: {inconsistency_score}")
        print(f"Consistency ratio: {consistency_ratio:.2f}")

        # Business metrics for developer confusion
        self.assertLess(consistency_ratio, 0.8,
            "Low consistency demonstrates import confusion issue")

    @pytest.mark.unit
    def test_ssot_consolidation_target_analysis(self):
        """Test what SSOT consolidation should achieve for imports."""

        # Analyze current state vs. SSOT target
        current_websocket_imports = set()
        import_complexity_by_module = {}

        for module_path in self.websocket_modules:
            try:
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                module_imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and 'websocket' in node.module.lower():
                            module_imports.append(node.module)
                            current_websocket_imports.add(node.module)

                import_complexity_by_module[module_path.name] = len(module_imports)

            except Exception as e:
                print(f"Could not analyze SSOT targets in {module_path}: {e}")

        print(f"\n=== SSOT Consolidation Target Analysis ===")
        print(f"Current unique WebSocket imports: {len(current_websocket_imports)}")
        print(f"Current import complexity by module:")
        for module, complexity in import_complexity_by_module.items():
            print(f"  {module}: {complexity} WebSocket imports")

        # Calculate consolidation potential
        total_current_imports = sum(import_complexity_by_module.values())
        avg_imports_per_module = total_current_imports / len(import_complexity_by_module) if import_complexity_by_module else 0

        # SSOT target: 1-2 imports per module maximum
        target_imports_per_module = 2
        consolidation_potential = avg_imports_per_module / target_imports_per_module

        print(f"Average WebSocket imports per module: {avg_imports_per_module:.1f}")
        print(f"SSOT target imports per module: {target_imports_per_module}")
        print(f"Consolidation potential: {consolidation_potential:.1f}x improvement")

        # Validate consolidation opportunity
        self.assertGreater(consolidation_potential, 1.5,
            "Should have significant consolidation potential")

        # Identify specific consolidation targets
        high_complexity_modules = {module: complexity for module, complexity
                                 in import_complexity_by_module.items()
                                 if complexity > target_imports_per_module}

        print(f"Modules needing consolidation: {len(high_complexity_modules)}")
        for module, complexity in high_complexity_modules.items():
            print(f"  {module}: {complexity} -> {target_imports_per_module} imports")

        self.assertGreater(len(high_complexity_modules), 0,
            "Should have modules that would benefit from import consolidation")