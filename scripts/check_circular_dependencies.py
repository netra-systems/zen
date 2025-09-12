#!/usr/bin/env python3
"""
Circular Dependency Checker for Frontend Modules

This script analyzes the frontend codebase to detect circular dependencies
that could cause initialization failures and white screen issues.

Usage:
    python scripts/check_circular_dependencies.py [--fix]
    
Options:
    --fix    Attempt to automatically fix simple circular dependencies
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

class DependencyAnalyzer:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.frontend_dir = root_dir / "frontend"
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.file_contents: Dict[str, str] = {}
        self.circular_dependencies: List[List[str]] = []
        
    def parse_imports(self, file_path: Path) -> Set[str]:
        """Parse all imports from a TypeScript/JavaScript file."""
        imports = set()
        
        try:
            content = file_path.read_text(encoding='utf-8')
            self.file_contents[str(file_path)] = content
            
            # Patterns to match various import styles
            patterns = [
                r'import\s+(?:[\w\s{},*]+\s+from\s+)?[\'"]([^\'"]+)[\'"]',
                r'import\s*\([\'"]([^\'"]+)[\'"]\)',
                r'require\s*\([\'"]([^\'"]+)[\'"]\)',
                r'export\s+(?:[\w\s{},*]+\s+from\s+)?[\'"]([^\'"]+)[\'"]',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Resolve @/ alias to frontend directory
                    if match.startswith('@/'):
                        resolved = match.replace('@/', '')
                        imports.add(resolved)
                    elif match.startswith('./') or match.startswith('../'):
                        # Resolve relative imports
                        resolved = self.resolve_relative_import(file_path, match)
                        if resolved:
                            imports.add(resolved)
                            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return imports
    
    def resolve_relative_import(self, from_file: Path, import_path: str) -> Optional[str]:
        """Resolve a relative import to an absolute path."""
        try:
            base_dir = from_file.parent
            resolved = (base_dir / import_path).resolve()
            
            # Convert to relative path from frontend directory
            if resolved.is_relative_to(self.frontend_dir):
                return str(resolved.relative_to(self.frontend_dir))
        except:
            pass
        return None
    
    def resolve_import_to_file(self, import_path: str) -> Optional[Path]:
        """Resolve an import path to an actual file."""
        base_path = self.frontend_dir / import_path
        
        # Try various extensions
        candidates = [
            base_path.with_suffix('.ts'),
            base_path.with_suffix('.tsx'),
            base_path.with_suffix('.js'),
            base_path.with_suffix('.jsx'),
            base_path / 'index.ts',
            base_path / 'index.tsx',
            base_path / 'index.js',
            base_path / 'index.jsx',
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
                
        return None
    
    def build_dependency_graph(self):
        """Build the complete dependency graph for the frontend."""
        print("Building dependency graph...")
        
        # Find all TypeScript/JavaScript files
        extensions = ['.ts', '.tsx', '.js', '.jsx']
        files = []
        
        for ext in extensions:
            files.extend(self.frontend_dir.rglob(f'*{ext}'))
        
        # Exclude node_modules and test files
        files = [f for f in files if 'node_modules' not in str(f) and '.next' not in str(f)]
        
        print(f"Analyzing {len(files)} files...")
        
        for file_path in files:
            rel_path = str(file_path.relative_to(self.frontend_dir))
            imports = self.parse_imports(file_path)
            
            for import_path in imports:
                resolved = self.resolve_import_to_file(import_path)
                if resolved:
                    resolved_rel = str(resolved.relative_to(self.frontend_dir))
                    self.dependencies[rel_path].add(resolved_rel)
    
    def detect_circular_dependencies(self):
        """Detect all circular dependencies using DFS."""
        print("\nDetecting circular dependencies...")
        
        visited = set()
        rec_stack = []
        
        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = rec_stack.index(node)
                cycle = rec_stack[cycle_start:] + [node]
                self.circular_dependencies.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.append(node)
            
            for neighbor in self.dependencies.get(node, []):
                dfs(neighbor, path + [neighbor])
            
            rec_stack.pop()
            return False
        
        for node in self.dependencies:
            if node not in visited:
                dfs(node, [node])
        
        # Remove duplicate cycles
        unique_cycles = []
        seen = set()
        
        for cycle in self.circular_dependencies:
            # Normalize cycle to start with smallest element
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
            
            if normalized not in seen:
                seen.add(normalized)
                unique_cycles.append(list(normalized)[:-1])  # Remove duplicate last element
        
        self.circular_dependencies = unique_cycles
    
    def check_critical_modules(self):
        """Check specific critical modules for issues."""
        critical_modules = [
            ('lib/logger.ts', ['lib/unified-api-config']),
            ('lib/unified-api-config.ts', ['lib/logger']),
            ('auth/context.tsx', []),
            ('providers/WebSocketProvider.tsx', []),
        ]
        
        issues = []
        
        for module, forbidden_imports in critical_modules:
            file_path = self.frontend_dir / module
            if not file_path.exists():
                continue
            
            imports = self.parse_imports(file_path)
            
            for forbidden in forbidden_imports:
                if any(forbidden in imp for imp in imports):
                    issues.append({
                        'module': module,
                        'forbidden_import': forbidden,
                        'severity': 'CRITICAL'
                    })
        
        return issues
    
    def analyze_import_depth(self) -> Dict[str, int]:
        """Calculate import depth for each module."""
        depths = {}
        
        def calculate_depth(node: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            
            if node in depths:
                return depths[node]
            
            if node in visited:
                return 0  # Circular dependency
            
            visited.add(node)
            
            max_depth = 0
            for dep in self.dependencies.get(node, []):
                depth = calculate_depth(dep, visited.copy())
                max_depth = max(max_depth, depth + 1)
            
            depths[node] = max_depth
            return max_depth
        
        for node in self.dependencies:
            if node not in depths:
                calculate_depth(node)
        
        return depths
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive dependency analysis report."""
        report = {
            'total_files': len(self.dependencies),
            'circular_dependencies': [],
            'critical_issues': [],
            'import_depths': {},
            'recommendations': []
        }
        
        # Add circular dependencies
        for cycle in self.circular_dependencies:
            report['circular_dependencies'].append({
                'cycle': ' -> '.join(cycle),
                'files': cycle,
                'severity': 'CRITICAL' if any('logger' in f or 'config' in f for f in cycle) else 'HIGH'
            })
        
        # Check critical modules
        critical_issues = self.check_critical_modules()
        report['critical_issues'] = critical_issues
        
        # Calculate import depths
        depths = self.analyze_import_depth()
        
        # Find modules with excessive depth
        for module, depth in depths.items():
            if depth > 10:
                report['import_depths'][module] = depth
        
        # Add recommendations
        if self.circular_dependencies:
            report['recommendations'].append(
                "Break circular dependencies by extracting shared types to separate files"
            )
        
        if critical_issues:
            report['recommendations'].append(
                "Remove logger imports from configuration modules"
            )
        
        if report['import_depths']:
            report['recommendations'].append(
                "Consider refactoring modules with deep import chains"
            )
        
        return report
    
    def fix_simple_issues(self) -> List[str]:
        """Attempt to fix simple circular dependency issues."""
        fixes = []
        
        # Fix: Remove logger import from unified-api-config
        config_file = self.frontend_dir / 'lib/unified-api-config.ts'
        if config_file.exists():
            content = config_file.read_text()
            
            if "import { logger }" in content:
                # Replace logger calls with console
                new_content = content.replace("import { logger } from '@/lib/logger';", "")
                new_content = re.sub(r'logger\.info\(', 'console.log(', new_content)
                new_content = re.sub(r'logger\.warn\(', 'console.warn(', new_content)
                new_content = re.sub(r'logger\.error\(', 'console.error(', new_content)
                new_content = re.sub(r'logger\.debug\(', 'console.debug(', new_content)
                
                config_file.write_text(new_content)
                fixes.append(f"Fixed: Removed logger import from {config_file}")
        
        return fixes

def main():
    parser = argparse.ArgumentParser(description='Check for circular dependencies in frontend code')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix simple issues')
    parser.add_argument('--json', action='store_true', help='Output report as JSON')
    args = parser.parse_args()
    
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    analyzer = DependencyAnalyzer(project_root)
    
    # Build dependency graph
    analyzer.build_dependency_graph()
    
    # Detect circular dependencies
    analyzer.detect_circular_dependencies()
    
    # Generate report
    report = analyzer.generate_report()
    
    # Apply fixes if requested
    if args.fix:
        fixes = analyzer.fix_simple_issues()
        report['fixes_applied'] = fixes
        
        if fixes:
            print("\nFixes applied:")
            for fix in fixes:
                print(f"  - {fix}")
    
    # Output report
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "="*60)
        print("CIRCULAR DEPENDENCY ANALYSIS REPORT")
        print("="*60)
        
        if report['circular_dependencies']:
            print(f"\n FAIL:  Found {len(report['circular_dependencies'])} circular dependencies:")
            for dep in report['circular_dependencies']:
                print(f"  [{dep['severity']}] {dep['cycle']}")
        else:
            print("\n PASS:  No circular dependencies found!")
        
        if report['critical_issues']:
            print(f"\n FAIL:  Critical issues found:")
            for issue in report['critical_issues']:
                print(f"  [{issue['severity']}] {issue['module']} imports {issue['forbidden_import']}")
        
        if report['import_depths']:
            print(f"\n WARNING: [U+FE0F]  Modules with excessive import depth (>10):")
            for module, depth in sorted(report['import_depths'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {module}: depth {depth}")
        
        if report['recommendations']:
            print("\n[U+1F4CB] Recommendations:")
            for rec in report['recommendations']:
                print(f"  [U+2022] {rec}")
        
        # Exit with error code if issues found
        if report['circular_dependencies'] or report['critical_issues']:
            sys.exit(1)
        else:
            print("\n PASS:  All checks passed!")
            sys.exit(0)

if __name__ == '__main__':
    main()