#!/usr/bin/env python3
"""
Import Issue Discovery and Fix Tool for Netra Apex
Discovers and helps fix import issues across the codebase, especially in tests.
"""

import ast
import os
import sys
import json
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
import argparse
import traceback

class ImportAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.issues = defaultdict(list)
        self.import_graph = defaultdict(set)
        self.module_paths = {}
        self.valid_modules = set()
        
    def analyze_file(self, file_path: Path) -> Dict[str, List]:
        """Analyze a single Python file for import issues."""
        issues = {
            'syntax_errors': [],
            'import_errors': [],
            'relative_import_issues': [],
            'circular_dependencies': [],
            'missing_modules': [],
            'duplicate_imports': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                issues['syntax_errors'].append({
                    'file': str(file_path),
                    'line': e.lineno,
                    'error': str(e)
                })
                return issues
            
            # Track imports in this file
            imports_in_file = []
            
            # Analyze imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        imports_in_file.append((module_name, node.lineno))
                        self._check_import(file_path, module_name, node.lineno, issues)
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    level = node.level
                    
                    # Check relative imports
                    if level > 0:
                        resolved = self._resolve_relative_import(file_path, module, level)
                        if resolved:
                            self._check_import(file_path, resolved, node.lineno, issues)
                        else:
                            issues['relative_import_issues'].append({
                                'file': str(file_path),
                                'line': node.lineno,
                                'import': f"{'.' * level}{module}",
                                'error': 'Could not resolve relative import'
                            })
                    else:
                        self._check_import(file_path, module, node.lineno, issues)
                    
                    for alias in node.names:
                        item_name = alias.name
                        full_import = f"{module}.{item_name}" if module else item_name
                        imports_in_file.append((full_import, node.lineno))
            
            # Check for duplicate imports
            seen_imports = {}
            for imp, line in imports_in_file:
                if imp in seen_imports:
                    issues['duplicate_imports'].append({
                        'file': str(file_path),
                        'import': imp,
                        'first_line': seen_imports[imp],
                        'duplicate_line': line
                    })
                else:
                    seen_imports[imp] = line
                    
        except Exception as e:
            issues['syntax_errors'].append({
                'file': str(file_path),
                'error': f"Failed to analyze: {str(e)}"
            })
            
        return issues
    
    def _resolve_relative_import(self, file_path: Path, module: str, level: int) -> Optional[str]:
        """Resolve a relative import to an absolute module path."""
        try:
            # Get the package hierarchy
            rel_path = file_path.relative_to(self.root_path)
            parts = list(rel_path.parts[:-1])  # Remove the file name
            
            # Go up 'level' directories
            if level > len(parts):
                return None
                
            base_parts = parts[:-level] if level > 0 else parts
            
            # Add the module parts
            if module:
                base_parts.extend(module.split('.'))
                
            return '.'.join(base_parts)
            
        except Exception:
            return None
    
    def _check_import(self, file_path: Path, module_name: str, line: int, issues: Dict):
        """Check if an import is valid."""
        if not module_name:
            return
            
        # Track in import graph
        rel_path = file_path.relative_to(self.root_path)
        self.import_graph[str(rel_path)].add(module_name)
        
        # Try to import the module
        try:
            # First check if it's a local module
            local_path = self._find_local_module(module_name)
            if local_path:
                self.valid_modules.add(module_name)
                return
                
            # Try standard import
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                issues['missing_modules'].append({
                    'file': str(file_path),
                    'line': line,
                    'module': module_name,
                    'error': 'Module not found'
                })
        except (ImportError, ModuleNotFoundError) as e:
            issues['import_errors'].append({
                'file': str(file_path),
                'line': line,
                'module': module_name,
                'error': str(e)
            })
        except Exception as e:
            issues['import_errors'].append({
                'file': str(file_path),
                'line': line,
                'module': module_name,
                'error': f"Unexpected error: {str(e)}"
            })
    
    def _find_local_module(self, module_name: str) -> Optional[Path]:
        """Find a local module in the project."""
        parts = module_name.split('.')
        
        # Check common locations
        for base in ['', 'netra_backend', 'tests', 'auth_service', 'frontend']:
            if base:
                search_path = self.root_path / base / Path(*parts[1:] if parts[0] == base else parts)
            else:
                search_path = self.root_path / Path(*parts)
                
            # Check for package
            if (search_path / '__init__.py').exists():
                return search_path
            # Check for module
            if search_path.with_suffix('.py').exists():
                return search_path.with_suffix('.py')
                
        return None
    
    def analyze_directory(self, directory: Path, pattern: str = "*.py") -> Dict[str, Dict]:
        """Analyze all Python files in a directory."""
        all_issues = {}
        
        for file_path in directory.rglob(pattern):
            # Skip __pycache__ and other generated directories
            if '__pycache__' in str(file_path) or '.pyc' in str(file_path):
                continue
                
            issues = self.analyze_file(file_path)
            
            # Only include files with issues
            if any(v for v in issues.values()):
                all_issues[str(file_path)] = issues
                
        return all_issues
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the import graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(module, path):
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for neighbor in self.import_graph.get(module, []):
                if neighbor not in visited:
                    if dfs(neighbor, path[:]):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)
                        
            rec_stack.remove(module)
            return False
        
        for module in self.import_graph:
            if module not in visited:
                dfs(module, [])
                
        return cycles
    
    def generate_report(self, issues: Dict[str, Dict]) -> str:
        """Generate a human-readable report of import issues."""
        report = []
        report.append("=" * 80)
        report.append("IMPORT ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        total_files = len(issues)
        total_issues = sum(
            sum(len(v) for v in file_issues.values())
            for file_issues in issues.values()
        )
        
        report.append(f"Total files with issues: {total_files}")
        report.append(f"Total issues found: {total_issues}")
        report.append("")
        
        # Group by issue type
        by_type = defaultdict(list)
        for file_path, file_issues in issues.items():
            for issue_type, issue_list in file_issues.items():
                for issue in issue_list:
                    by_type[issue_type].append(issue)
        
        # Report each type
        for issue_type in ['syntax_errors', 'import_errors', 'missing_modules', 
                          'relative_import_issues', 'duplicate_imports']:
            if issue_type in by_type:
                report.append("-" * 40)
                report.append(f"{issue_type.upper().replace('_', ' ')}: {len(by_type[issue_type])}")
                report.append("-" * 40)
                
                for issue in by_type[issue_type][:10]:  # Show first 10
                    if issue_type == 'syntax_errors':
                        report.append(f"  {issue['file']}:{issue.get('line', '?')}")
                        report.append(f"    Error: {issue['error']}")
                    elif issue_type in ['import_errors', 'missing_modules']:
                        report.append(f"  {issue['file']}:{issue['line']}")
                        report.append(f"    Module: {issue['module']}")
                        report.append(f"    Error: {issue['error']}")
                    elif issue_type == 'relative_import_issues':
                        report.append(f"  {issue['file']}:{issue['line']}")
                        report.append(f"    Import: {issue['import']}")
                        report.append(f"    Error: {issue['error']}")
                    elif issue_type == 'duplicate_imports':
                        report.append(f"  {issue['file']}")
                        report.append(f"    Import: {issue['import']}")
                        report.append(f"    Lines: {issue['first_line']} and {issue['duplicate_line']}")
                
                if len(by_type[issue_type]) > 10:
                    report.append(f"  ... and {len(by_type[issue_type]) - 10} more")
                report.append("")
        
        # Circular dependencies
        cycles = self.find_circular_dependencies()
        if cycles:
            report.append("-" * 40)
            report.append(f"CIRCULAR DEPENDENCIES: {len(cycles)}")
            report.append("-" * 40)
            for cycle in cycles[:5]:
                report.append(f"  {' -> '.join(cycle)}")
            if len(cycles) > 5:
                report.append(f"  ... and {len(cycles) - 5} more")
            report.append("")
        
        return '\n'.join(report)
    
    def suggest_fixes(self, issues: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Suggest fixes for common import issues."""
        suggestions = defaultdict(list)
        
        for file_path, file_issues in issues.items():
            file_suggestions = []
            
            # Relative import issues
            if file_issues.get('relative_import_issues'):
                file_suggestions.append("Consider using absolute imports instead of relative imports")
                file_suggestions.append("Add __init__.py files to make directories packages")
                
            # Missing modules
            if file_issues.get('missing_modules'):
                missing = {issue['module'] for issue in file_issues['missing_modules']}
                for module in missing:
                    if module.startswith('netra_backend'):
                        file_suggestions.append(f"Ensure PYTHONPATH includes project root")
                    elif module.startswith('tests'):
                        file_suggestions.append(f"Run tests with 'python -m pytest' from project root")
                    else:
                        file_suggestions.append(f"Install missing package: pip install {module.split('.')[0]}")
            
            # Duplicate imports
            if file_issues.get('duplicate_imports'):
                file_suggestions.append("Remove duplicate import statements")
                
            if file_suggestions:
                suggestions[file_path] = file_suggestions
                
        return suggestions

def main():
    parser = argparse.ArgumentParser(description='Analyze Python imports for issues')
    parser.add_argument('path', nargs='?', default='.',
                       help='Path to analyze (default: current directory)')
    parser.add_argument('--fix', action='store_true',
                       help='Attempt to fix issues automatically')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    parser.add_argument('--focus', choices=['tests', 'backend', 'all'], default='all',
                       help='Focus on specific part of codebase')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup paths
    root_path = Path(args.path).resolve()
    
    # Add project root to Python path
    if str(root_path) not in sys.path:
        sys.path.insert(0, str(root_path))
    
    # Initialize analyzer
    analyzer = ImportAnalyzer(root_path)
    
    # Determine what to analyze
    if args.focus == 'tests':
        analyze_paths = [root_path / 'tests']
    elif args.focus == 'backend':
        analyze_paths = [root_path / 'netra_backend']
    else:
        analyze_paths = [root_path]
    
    # Analyze
    all_issues = {}
    for path in analyze_paths:
        if path.exists():
            if args.verbose:
                print(f"Analyzing {path}...")
            issues = analyzer.analyze_directory(path)
            all_issues.update(issues)
    
    # Output results
    if args.json:
        print(json.dumps(all_issues, indent=2))
    else:
        report = analyzer.generate_report(all_issues)
        print(report)
        
        # Show suggestions
        if all_issues:
            print("\n" + "=" * 80)
            print("SUGGESTED FIXES")
            print("=" * 80)
            suggestions = analyzer.suggest_fixes(all_issues)
            for file_path, file_suggestions in list(suggestions.items())[:10]:
                print(f"\n{file_path}:")
                for suggestion in file_suggestions:
                    print(f"  - {suggestion}")
            
            if len(suggestions) > 10:
                print(f"\n... and suggestions for {len(suggestions) - 10} more files")
    
    # Return exit code based on issues found
    return 1 if all_issues else 0

if __name__ == '__main__':
    sys.exit(main())