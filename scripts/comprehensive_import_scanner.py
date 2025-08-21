#!/usr/bin/env python3
"""
Comprehensive Import Scanner and Fixer for Netra Codebase

This tool provides advanced import scanning, analysis, and automated fixing capabilities
for the entire codebase including tests and the System Under Test (SUT).
"""

import ast
import os
import sys
import json
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict
import time
import argparse
import re


@dataclass
class ImportIssue:
    """Represents an import issue found in the codebase"""
    file_path: str
    line_number: int
    module: str
    imported_names: List[str]
    issue_type: str  # 'missing_module', 'missing_name', 'circular', 'syntax', 'relative_import'
    error_message: str
    suggested_fix: Optional[str] = None
    severity: str = "error"  # 'error', 'warning', 'info'
    context: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImportScanResult:
    """Results from scanning imports in a file"""
    file_path: str
    total_imports: int = 0
    valid_imports: int = 0
    issues: List[ImportIssue] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    scan_time: float = 0.0
    parse_error: Optional[str] = None
    
    def has_issues(self) -> bool:
        return len(self.issues) > 0 or self.parse_error is not None


@dataclass
class ComprehensiveScanReport:
    """Complete scan report for the codebase"""
    scan_timestamp: datetime
    total_files: int = 0
    files_with_issues: int = 0
    total_issues: int = 0
    issue_summary: Dict[str, int] = field(default_factory=dict)
    critical_issues: List[ImportIssue] = field(default_factory=list)
    test_files_scanned: int = 0
    test_issues: List[ImportIssue] = field(default_factory=list)
    sut_files_scanned: int = 0
    sut_issues: List[ImportIssue] = field(default_factory=list)
    circular_dependencies: List[List[str]] = field(default_factory=list)
    missing_modules: Set[str] = field(default_factory=set)
    scan_duration: float = 0.0
    
    def to_json(self, filepath: str):
        """Save report as JSON"""
        report_dict = {
            'scan_timestamp': self.scan_timestamp.isoformat(),
            'summary': {
                'total_files': self.total_files,
                'files_with_issues': self.files_with_issues,
                'total_issues': self.total_issues,
                'test_files_scanned': self.test_files_scanned,
                'sut_files_scanned': self.sut_files_scanned,
                'scan_duration': self.scan_duration
            },
            'issue_summary': self.issue_summary,
            'critical_issues': [i.to_dict() for i in self.critical_issues[:20]],
            'test_issues': [i.to_dict() for i in self.test_issues[:50]],
            'sut_issues': [i.to_dict() for i in self.sut_issues[:50]],
            'circular_dependencies': self.circular_dependencies,
            'missing_modules': list(self.missing_modules)
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2)
    
    def print_summary(self):
        """Print a human-readable summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE IMPORT SCAN REPORT")
        print("="*80)
        print(f"Scan Timestamp: {self.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scan Duration: {self.scan_duration:.2f}s")
        print("\nSUMMARY:")
        print(f"  Total Files Scanned: {self.total_files}")
        print(f"  Files with Issues: {self.files_with_issues}")
        print(f"  Total Issues Found: {self.total_issues}")
        print(f"  Test Files: {self.test_files_scanned} ({len(self.test_issues)} issues)")
        print(f"  SUT Files: {self.sut_files_scanned} ({len(self.sut_issues)} issues)")
        
        if self.issue_summary:
            print("\nISSUE BREAKDOWN:")
            for issue_type, count in sorted(self.issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"  {issue_type}: {count}")
        
        if self.circular_dependencies:
            print(f"\nCIRCULAR DEPENDENCIES: {len(self.circular_dependencies)}")
            for cycle in self.circular_dependencies[:3]:
                print(f"  {' -> '.join(cycle[:4])}{'...' if len(cycle) > 4 else ''}")
        
        if self.missing_modules:
            print(f"\nMISSING MODULES: {len(self.missing_modules)}")
            for module in list(self.missing_modules)[:10]:
                print(f"  - {module}")
        
        if self.critical_issues:
            print(f"\nCRITICAL ISSUES (showing first 5):")
            for issue in self.critical_issues[:5]:
                print(f"\n  File: {issue.file_path}:{issue.line_number}")
                print(f"  Type: {issue.issue_type}")
                print(f"  Error: {issue.error_message}")
                if issue.suggested_fix:
                    print(f"  Fix: {issue.suggested_fix}")


class ComprehensiveImportScanner:
    """Main scanner class for comprehensive import analysis"""
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.report = ComprehensiveScanReport(scan_timestamp=datetime.now())
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.visited_modules: Set[str] = set()
        self.import_stack: List[str] = []
        
        # Module resolution cache
        self.module_cache: Dict[str, bool] = {}
        self.name_cache: Dict[Tuple[str, str], bool] = {}
        
        # Common import patterns in the codebase
        self.common_patterns = {
            'auth_integration': ['auth', 'interfaces'],
            'clients.auth': ['auth_client', 'auth_client_core'],
            'core.configuration': ['base', 'services', 'database'],
            'services': ['agent_service', 'thread_service', 'websocket_service'],
            'agents': ['supervisor_consolidated', 'base_agent', 'corpus_admin'],
            'db': ['postgres_core', 'clickhouse_init', 'database_connectivity_master']
        }
        
    def scan_file(self, file_path: Path) -> ImportScanResult:
        """Scan a single Python file for import issues"""
        result = ImportScanResult(file_path=str(file_path))
        start_time = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            # Analyze imports
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._analyze_import(node, file_path, result)
            
        except SyntaxError as e:
            result.parse_error = f"Syntax error at line {e.lineno}: {e.msg}"
            result.issues.append(ImportIssue(
                file_path=str(file_path),
                line_number=e.lineno or 0,
                module="",
                imported_names=[],
                issue_type="syntax",
                error_message=str(e),
                severity="error"
            ))
        except Exception as e:
            result.parse_error = f"Failed to parse: {str(e)}"
        
        result.scan_time = time.time() - start_time
        return result
    
    def _analyze_import(self, node: ast.AST, file_path: Path, result: ImportScanResult):
        """Analyze a single import statement"""
        result.total_imports += 1
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                result.dependencies.add(module_name)
                
                if not self._validate_module(module_name):
                    result.issues.append(ImportIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        module=module_name,
                        imported_names=[],
                        issue_type="missing_module",
                        error_message=f"Module '{module_name}' not found",
                        suggested_fix=self._suggest_module_fix(module_name)
                    ))
                else:
                    result.valid_imports += 1
                    
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level  # Number of dots for relative imports
            
            # Handle relative imports
            if level > 0:
                if not module:
                    module = "." * level
                else:
                    module = "." * level + module
                    
                # Check if relative import can be resolved
                resolved_module = self._resolve_relative_import(file_path, module, level)
                if resolved_module:
                    module = resolved_module
                    result.dependencies.add(module)
                else:
                    result.issues.append(ImportIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        module=module,
                        imported_names=[],
                        issue_type="relative_import",
                        error_message=f"Cannot resolve relative import '{module}'",
                        severity="warning"
                    ))
                    return
            
            result.dependencies.add(module)
            
            # Extract imported names
            imported_names = []
            for alias in node.names:
                if alias.name == "*":
                    imported_names.append("*")
                else:
                    imported_names.append(alias.name)
            
            # Validate module exists
            if not self._validate_module(module):
                result.issues.append(ImportIssue(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    module=module,
                    imported_names=imported_names,
                    issue_type="missing_module",
                    error_message=f"Module '{module}' not found",
                    suggested_fix=self._suggest_module_fix(module)
                ))
                self.report.missing_modules.add(module)
            else:
                # Validate imported names exist in module
                for name in imported_names:
                    if name != "*" and not self._validate_name_in_module(module, name):
                        result.issues.append(ImportIssue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            module=module,
                            imported_names=[name],
                            issue_type="missing_name",
                            error_message=f"Cannot import name '{name}' from '{module}'",
                            suggested_fix=self._suggest_name_fix(module, name)
                        ))
                    else:
                        result.valid_imports += 1
    
    def _validate_module(self, module_name: str) -> bool:
        """Check if a module exists and can be imported"""
        if module_name in self.module_cache:
            return self.module_cache[module_name]
        
        try:
            # Try to import the module
            importlib.import_module(module_name)
            self.module_cache[module_name] = True
            return True
        except:
            # Check if it's a local module
            module_path = module_name.replace('.', os.sep) + '.py'
            full_path = self.root_path / module_path
            
            if full_path.exists():
                self.module_cache[module_name] = True
                return True
            
            # Check for package __init__.py
            package_path = self.root_path / module_name.replace('.', os.sep) / '__init__.py'
            if package_path.exists():
                self.module_cache[module_name] = True
                return True
            
            self.module_cache[module_name] = False
            return False
    
    def _validate_name_in_module(self, module_name: str, name: str) -> bool:
        """Check if a name exists in a module"""
        cache_key = (module_name, name)
        if cache_key in self.name_cache:
            return self.name_cache[cache_key]
        
        try:
            module = importlib.import_module(module_name)
            exists = hasattr(module, name)
            self.name_cache[cache_key] = exists
            return exists
        except:
            # Try to parse the module file directly
            module_file = self._find_module_file(module_name)
            if module_file and module_file.exists():
                try:
                    with open(module_file, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    
                    # Look for the name in the module
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
                            self.name_cache[cache_key] = True
                            return True
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == name:
                                    self.name_cache[cache_key] = True
                                    return True
                except:
                    pass
            
            self.name_cache[cache_key] = False
            return False
    
    def _find_module_file(self, module_name: str) -> Optional[Path]:
        """Find the file path for a module"""
        # Try as a .py file
        module_path = self.root_path / (module_name.replace('.', os.sep) + '.py')
        if module_path.exists():
            return module_path
        
        # Try as a package __init__.py
        package_path = self.root_path / module_name.replace('.', os.sep) / '__init__.py'
        if package_path.exists():
            return package_path
        
        return None
    
    def _resolve_relative_import(self, file_path: Path, module: str, level: int) -> Optional[str]:
        """Resolve a relative import to an absolute module path"""
        # Get the package of the current file
        relative_to_root = file_path.relative_to(self.root_path)
        parts = list(relative_to_root.parts[:-1])  # Remove the file name
        
        # Go up 'level' directories
        if level > len(parts):
            return None
        
        if level > 0:
            parts = parts[:-level+1] if level > 1 else parts
        
        # Add the module part if any
        if module and not module.startswith('.'):
            parts.extend(module.split('.'))
        
        return '.'.join(parts)
    
    def _suggest_module_fix(self, module_name: str) -> Optional[str]:
        """Suggest a fix for a missing module"""
        # Check common typos and patterns
        suggestions = []
        
        # Check if it's a common pattern mismatch
        for pattern, modules in self.common_patterns.items():
            if pattern in module_name:
                for mod in modules:
                    alt_name = module_name.replace(pattern, f"{pattern}.{mod}")
                    if self._validate_module(alt_name):
                        suggestions.append(f"Try: from {alt_name} import ...")
        
        # Check for case sensitivity issues
        lower_name = module_name.lower()
        for root, dirs, files in os.walk(self.root_path):
            for file in files:
                if file.endswith('.py'):
                    file_module = file[:-3].lower()
                    if file_module == lower_name.split('.')[-1]:
                        rel_path = Path(root).relative_to(self.root_path)
                        suggested = '.'.join(rel_path.parts + (file[:-3],))
                        suggestions.append(f"Did you mean: {suggested}?")
        
        return suggestions[0] if suggestions else None
    
    def _suggest_name_fix(self, module_name: str, name: str) -> Optional[str]:
        """Suggest a fix for a missing name in a module"""
        try:
            module = importlib.import_module(module_name)
            available = [n for n in dir(module) if not n.startswith('_')]
            
            # Find similar names
            similar = []
            for available_name in available:
                if name.lower() in available_name.lower() or available_name.lower() in name.lower():
                    similar.append(available_name)
            
            if similar:
                return f"Available similar names: {', '.join(similar[:3])}"
            elif len(available) < 20:
                return f"Available names: {', '.join(available)}"
        except:
            pass
        
        return None
    
    def detect_circular_imports(self, files: List[Path]) -> List[List[str]]:
        """Detect circular import dependencies"""
        # Build dependency graph
        for file in files:
            result = self.scan_file(file)
            file_module = self._path_to_module(file)
            self.dependency_graph[file_module] = result.dependencies
        
        # Find cycles using DFS
        cycles = []
        visited = set()
        rec_stack = []
        
        def dfs(module: str) -> bool:
            visited.add(module)
            rec_stack.append(module)
            
            for dep in self.dependency_graph.get(module, []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    # Found a cycle
                    cycle_start = rec_stack.index(dep)
                    cycle = rec_stack[cycle_start:] + [dep]
                    cycles.append(cycle)
                    return True
            
            rec_stack.pop()
            return False
        
        for module in self.dependency_graph:
            if module not in visited:
                dfs(module)
        
        return cycles
    
    def _path_to_module(self, path: Path) -> str:
        """Convert a file path to a module name"""
        try:
            rel_path = path.relative_to(self.root_path)
            parts = list(rel_path.parts)
            
            if parts[-1].endswith('.py'):
                if parts[-1] == '__init__.py':
                    parts = parts[:-1]
                else:
                    parts[-1] = parts[-1][:-3]
            
            return '.'.join(parts)
        except:
            return str(path)
    
    def scan_directory(self, directory: Path, pattern: str = "*.py", 
                      recursive: bool = True, category: str = "general") -> List[ImportScanResult]:
        """Scan all Python files in a directory"""
        results = []
        
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        print(f"\nScanning {len(files)} {category} files...")
        
        for file in files:
            # Skip virtual environments and cache
            if any(part in str(file) for part in ['venv', '__pycache__', '.git', 'node_modules']):
                continue
            
            result = self.scan_file(file)
            results.append(result)
            
            # Update report
            self.report.total_files += 1
            
            if result.has_issues():
                self.report.files_with_issues += 1
                self.report.total_issues += len(result.issues)
                
                for issue in result.issues:
                    self.report.issue_summary[issue.issue_type] = \
                        self.report.issue_summary.get(issue.issue_type, 0) + 1
                    
                    if issue.severity == "error":
                        self.report.critical_issues.append(issue)
                    
                    if category == "test":
                        self.report.test_issues.append(issue)
                    elif category == "sut":
                        self.report.sut_issues.append(issue)
            
            if category == "test":
                self.report.test_files_scanned += 1
            elif category == "sut":
                self.report.sut_files_scanned += 1
        
        return results
    
    def run_comprehensive_scan(self) -> ComprehensiveScanReport:
        """Run a comprehensive scan of the entire codebase"""
        start_time = time.time()
        
        print("\n" + "="*80)
        print("STARTING COMPREHENSIVE IMPORT SCAN")
        print("="*80)
        
        # Scan E2E test files
        test_dirs = [
            self.root_path / "tests",
            self.root_path / "netra_backend" / "tests",
            self.root_path / "test_framework"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                self.scan_directory(test_dir, pattern="*e2e*.py", category="test")
        
        # Scan System Under Test (main application)
        sut_dirs = [
            self.root_path / "netra_backend" / "app",
            self.root_path / "auth_service",
            self.root_path / "frontend" / "src"  # For TypeScript imports if needed
        ]
        
        for sut_dir in sut_dirs:
            if sut_dir.exists():
                self.scan_directory(sut_dir, pattern="*.py", category="sut")
        
        # Detect circular imports
        all_files = []
        for directory in test_dirs + sut_dirs:
            if directory.exists():
                all_files.extend(list(directory.rglob("*.py")))
        
        self.report.circular_dependencies = self.detect_circular_imports(all_files[:100])  # Limit for performance
        
        self.report.scan_duration = time.time() - start_time
        
        return self.report


class ImportFixer:
    """Automated import fixing capabilities"""
    
    def __init__(self, scanner: ComprehensiveImportScanner):
        self.scanner = scanner
        self.fixes_applied = 0
        self.fixes_failed = 0
        
    def fix_missing_name(self, issue: ImportIssue) -> bool:
        """Attempt to fix a missing name import"""
        try:
            file_path = Path(issue.file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find the import line
            if issue.line_number <= len(lines):
                line = lines[issue.line_number - 1]
                
                # Try to find an alternative import
                if issue.suggested_fix and "Available similar names:" in issue.suggested_fix:
                    # Extract the first suggested name
                    suggested = issue.suggested_fix.split(": ")[1].split(",")[0].strip()
                    
                    # Replace the problematic name with the suggested one
                    for name in issue.imported_names:
                        if name in line:
                            lines[issue.line_number - 1] = line.replace(name, suggested)
                            
                            # Write back
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.writelines(lines)
                            
                            self.fixes_applied += 1
                            return True
        except Exception as e:
            print(f"Failed to fix {issue.file_path}:{issue.line_number} - {e}")
            self.fixes_failed += 1
        
        return False
    
    def fix_missing_module(self, issue: ImportIssue) -> bool:
        """Attempt to fix a missing module import"""
        try:
            if issue.suggested_fix and "Try:" in issue.suggested_fix:
                file_path = Path(issue.file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Extract the suggested import
                suggested_import = issue.suggested_fix.split("Try: ")[1].strip()
                
                # Replace the line
                if issue.line_number <= len(lines):
                    lines[issue.line_number - 1] = suggested_import + "\n"
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    self.fixes_applied += 1
                    return True
        except Exception as e:
            print(f"Failed to fix {issue.file_path}:{issue.line_number} - {e}")
            self.fixes_failed += 1
        
        return False
    
    def auto_fix_issues(self, issues: List[ImportIssue], dry_run: bool = True) -> Dict[str, int]:
        """Automatically fix import issues"""
        fixes = {
            'missing_name': 0,
            'missing_module': 0,
            'total': 0
        }
        
        print(f"\n{'DRY RUN: ' if dry_run else ''}Attempting to fix {len(issues)} issues...")
        
        for issue in issues:
            if dry_run:
                if issue.suggested_fix:
                    print(f"Would fix: {issue.file_path}:{issue.line_number}")
                    print(f"  Issue: {issue.error_message}")
                    print(f"  Fix: {issue.suggested_fix}")
                    fixes['total'] += 1
            else:
                if issue.issue_type == "missing_name" and self.fix_missing_name(issue):
                    fixes['missing_name'] += 1
                    fixes['total'] += 1
                elif issue.issue_type == "missing_module" and self.fix_missing_module(issue):
                    fixes['missing_module'] += 1
                    fixes['total'] += 1
        
        return fixes


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Comprehensive Import Scanner and Fixer')
    parser.add_argument('--fix', action='store_true', help='Attempt to automatically fix issues')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    parser.add_argument('--json', type=str, help='Save detailed report to JSON file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--focus', choices=['tests', 'sut', 'all'], default='all', 
                       help='Focus scan on specific area')
    
    args = parser.parse_args()
    
    # Initialize scanner
    project_root = Path(__file__).parent.parent
    scanner = ComprehensiveImportScanner(root_path=project_root)
    
    # Add project root to sys.path
    sys.path.insert(0, str(project_root))
    
    # Run comprehensive scan
    report = scanner.run_comprehensive_scan()
    
    # Print summary
    report.print_summary()
    
    # Save JSON report if requested
    if args.json:
        report.save_json_report(args.json)
        print(f"\nDetailed report saved to: {args.json}")
    
    # Auto-fix if requested
    if args.fix or args.dry_run:
        fixer = ImportFixer(scanner)
        
        # Collect issues to fix based on focus
        issues_to_fix = []
        if args.focus in ['tests', 'all']:
            issues_to_fix.extend(report.test_issues)
        if args.focus in ['sut', 'all']:
            issues_to_fix.extend(report.sut_issues)
        
        # Filter to only fixable issues
        fixable_issues = [i for i in issues_to_fix if i.suggested_fix]
        
        fixes = fixer.auto_fix_issues(fixable_issues, dry_run=args.dry_run)
        
        print(f"\n{'Would fix' if args.dry_run else 'Fixed'} Summary:")
        print(f"  Total: {fixes['total']}")
        print(f"  Missing Names: {fixes['missing_name']}")
        print(f"  Missing Modules: {fixes['missing_module']}")
    
    # Exit with error code if issues found
    sys.exit(1 if report.total_issues > 0 else 0)


if __name__ == '__main__':
    main()