"""
Circular Import Detection Test
This test analyzes the codebase to detect circular import dependencies
"""

import os
import sys
import ast
import importlib.util
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict, deque


class CircularImportDetector:
    """Detects circular imports in Python codebase"""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).absolute()
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.module_paths: Dict[str, Path] = {}
        self.circular_imports: List[List[str]] = []
        
    def _get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name"""
        try:
            rel_path = file_path.relative_to(self.root_dir)
            parts = list(rel_path.parts[:-1]) + [rel_path.stem]
            # Remove __pycache__ directories
            parts = [p for p in parts if p != '__pycache__']
            return '.'.join(parts)
        except ValueError:
            return str(file_path.stem)
    
    def _extract_imports(self, file_path: Path) -> Set[str]:
        """Extract all imports from a Python file"""
        imports = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Handle relative imports
                        if node.level > 0:
                            # Relative import
                            module_parts = self._get_module_name(file_path).split('.')
                            if node.level <= len(module_parts):
                                base_parts = module_parts[:-node.level]
                                if node.module:
                                    full_module = '.'.join(base_parts + [node.module])
                                else:
                                    full_module = '.'.join(base_parts)
                                imports.add(full_module)
                        else:
                            imports.add(node.module)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return imports
    
    def _build_import_graph(self):
        """Build the import dependency graph"""
        print("Building import graph...")
        
        # First pass: collect all Python files
        python_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip virtual environments and cache directories
            dirs[:] = [d for d in dirs if d not in {
                'venv', '.venv', '__pycache__', '.git', 
                'node_modules', '.pytest_cache', '.tox'
            }]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        print(f"Found {len(python_files)} Python files")
        
        # Second pass: extract imports
        for file_path in python_files:
            module_name = self._get_module_name(file_path)
            self.module_paths[module_name] = file_path
            
            imports = self._extract_imports(file_path)
            
            # Filter imports to only include project modules
            for imp in imports:
                # Check if this import refers to a module in our project
                imp_parts = imp.split('.')
                for i in range(len(imp_parts), 0, -1):
                    potential_module = '.'.join(imp_parts[:i])
                    if potential_module in self.module_paths or \
                       any(m.startswith(potential_module + '.') for m in self.module_paths):
                        self.import_graph[module_name].add(potential_module)
                        break
    
    def _detect_cycles_dfs(self):
        """Detect cycles using DFS with path tracking"""
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(module):
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for neighbor in self.import_graph.get(module, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    self.circular_imports.append(cycle)
                    return False  # Continue searching for more cycles
            
            path.pop()
            rec_stack.remove(module)
            return False
        
        for module in list(self.import_graph.keys()):
            if module not in visited:
                dfs(module)
    
    def detect_circular_imports(self) -> List[List[str]]:
        """Main method to detect circular imports"""
        self._build_import_graph()
        self._detect_cycles_dfs()
        
        # Remove duplicate cycles
        unique_cycles = []
        seen = set()
        for cycle in self.circular_imports:
            # Normalize cycle (start from smallest element)
            if cycle:
                min_idx = cycle.index(min(cycle))
                normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
                if normalized not in seen:
                    seen.add(normalized)
                    unique_cycles.append(list(normalized))
        
        return unique_cycles
    
    def print_report(self):
        """Print a detailed report of circular imports"""
        cycles = self.detect_circular_imports()
        
        if not cycles:
            print("\n[SUCCESS] No circular imports detected!")
            return False
        
        print(f"\n[ERROR] Found {len(cycles)} circular import(s):\n")
        
        for i, cycle in enumerate(cycles, 1):
            print(f"Circular Import #{i}:")
            for j in range(len(cycle) - 1):
                module = cycle[j]
                next_module = cycle[j + 1]
                if module in self.module_paths:
                    print(f"  {module} -> {next_module}")
                    print(f"    File: {self.module_paths[module]}")
            print()
        
        return True


def main():
    """Main function to run circular import detection"""
    # Get the project root (netra_backend)
    project_root = Path(__file__).parent / "netra_backend"
    
    if not project_root.exists():
        print(f"Error: Project root not found at {project_root}")
        return 1
    
    print(f"Analyzing project at: {project_root}")
    print("=" * 60)
    
    detector = CircularImportDetector(str(project_root))
    has_circular_imports = detector.print_report()
    
    if has_circular_imports:
        print("\n[WARNING] Circular imports can cause:")
        print("  - Import errors at runtime")
        print("  - Difficulty in testing")
        print("  - Poor code maintainability")
        print("\nRecommended fixes:")
        print("  1. Move shared code to a separate module")
        print("  2. Use import statements inside functions")
        print("  3. Reorganize module structure")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())