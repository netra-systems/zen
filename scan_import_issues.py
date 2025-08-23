#!/usr/bin/env python3
"""
Import Issues Scanner
Scans all test files for import problems using AST parsing
"""

import ast
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
import traceback

class ImportIssueScanner:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.issues = []
        self.patterns = {
            'connection_manager': {
                'old_patterns': [
                    'from netra_backend.app.websocket.connection_manager',
                    'import connection_manager',
                    'from .connection_manager',
                    'from ..connection_manager',
                    'from websocket.connection_manager',
                    'from ...websocket.connection_manager'
                ],
                'correct_import': 'from netra_backend.app.websocket.connection import ConnectionManager'
            },
            'thread_service': {
                'old_patterns': [
                    'from netra_backend.services.thread_service',
                    'from services.thread_service',
                    'from ..services.thread_service',
                    'from ...services.thread_service'
                ],
                'correct_import': 'from netra_backend.app.services.thread_service import ThreadService'
            },
            'ws_manager': {
                'old_patterns': [
                    'from netra_backend.app.websocket.ws_manager',
                    'from websocket.ws_manager',
                    'from ..websocket.ws_manager'
                ],
                'correct_import': 'from netra_backend.app.ws_manager import WebSocketManager'
            }
        }
        
    def find_test_files(self) -> List[Path]:
        """Find all test files in the project"""
        test_files = []
        
        # Test directories to scan
        test_dirs = [
            'netra_backend/tests',
            'auth_service/tests', 
            'tests/e2e',
            'test_framework',
            'dev_launcher/tests'
        ]
        
        for test_dir in test_dirs:
            test_path = self.root_dir / test_dir
            if test_path.exists():
                for file_path in test_path.rglob('*.py'):
                    if file_path.name.startswith('test_') or 'test' in file_path.name:
                        test_files.append(file_path)
                        
        # Also find standalone test files
        for file_path in self.root_dir.rglob('test_*.py'):
            if file_path not in test_files:
                test_files.append(file_path)
                
        return test_files
    
    def parse_file_imports(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse imports from a Python file using AST"""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno,
                            'full_statement': f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
                        })
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    level = node.level
                    
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'level': level,
                            'line': node.lineno,
                            'full_statement': f"from {'.' * level}{module} import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
                        })
                        
        except Exception as e:
            self.issues.append({
                'file': str(file_path),
                'line': 0,
                'issue_type': 'parse_error',
                'description': f"Failed to parse file: {e}",
                'current_import': '',
                'suggested_fix': 'Fix syntax errors in file'
            })
            
        return imports
    
    def check_import_issues(self, file_path: Path, imports: List[Dict[str, Any]]):
        """Check for import issues in the parsed imports"""
        
        for import_info in imports:
            issue = self.detect_import_issue(import_info)
            if issue:
                issue['file'] = str(file_path)
                issue['line'] = import_info['line']
                self.issues.append(issue)
    
    def detect_import_issue(self, import_info: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if an import has issues"""
        
        statement = import_info['full_statement']
        
        # Check for ConnectionManager issues
        if any(pattern in statement for pattern in self.patterns['connection_manager']['old_patterns']):
            return {
                'issue_type': 'incorrect_connection_manager_import',
                'description': 'Incorrect ConnectionManager import path',
                'current_import': statement,
                'suggested_fix': self.patterns['connection_manager']['correct_import']
            }
            
        # Check for ThreadService issues  
        if any(pattern in statement for pattern in self.patterns['thread_service']['old_patterns']):
            return {
                'issue_type': 'incorrect_thread_service_import',
                'description': 'Incorrect ThreadService import path',
                'current_import': statement,
                'suggested_fix': self.patterns['thread_service']['correct_import']
            }
            
        # Check for WebSocketManager issues
        if any(pattern in statement for pattern in self.patterns['ws_manager']['old_patterns']):
            return {
                'issue_type': 'incorrect_ws_manager_import',
                'description': 'Incorrect WebSocketManager import path',
                'current_import': statement,
                'suggested_fix': self.patterns['ws_manager']['correct_import']
            }
        
        # Check for relative import issues
        if import_info['type'] == 'from_import' and import_info['level'] > 0:
            if import_info['level'] > 3:  # Too many relative levels
                return {
                    'issue_type': 'excessive_relative_import',
                    'description': f'Excessive relative import with {import_info["level"]} levels',
                    'current_import': statement,
                    'suggested_fix': 'Use absolute import path'
                }
        
        # Check for missing module paths (common after restructuring)
        if import_info['type'] == 'from_import':
            module = import_info['module']
            if module and not module.startswith('netra_backend') and not module.startswith('auth_service'):
                if any(suspect in module for suspect in ['services', 'websocket', 'agents', 'core']):
                    return {
                        'issue_type': 'missing_service_prefix',
                        'description': 'Import missing service prefix after restructuring',
                        'current_import': statement,
                        'suggested_fix': f'Add netra_backend.app prefix: from netra_backend.app.{module} import ...'
                    }
        
        return None
    
    def scan_all_files(self):
        """Scan all test files for import issues"""
        test_files = self.find_test_files()
        
        print(f"Found {len(test_files)} test files to scan")
        
        for file_path in test_files:
            print(f"Scanning: {file_path}")
            imports = self.parse_file_imports(file_path)
            self.check_import_issues(file_path, imports)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report"""
        
        # Group issues by type
        issues_by_type = {}
        for issue in self.issues:
            issue_type = issue['issue_type']
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        # Group issues by file
        issues_by_file = {}
        for issue in self.issues:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        return {
            'total_issues': len(self.issues),
            'issues_by_type': {k: len(v) for k, v in issues_by_type.items()},
            'issues_by_file': {k: len(v) for k, v in issues_by_file.items()},
            'detailed_issues': self.issues,
            'summary': {
                'most_common_issue': max(issues_by_type.keys(), key=lambda k: len(issues_by_type[k])) if issues_by_type else None,
                'files_with_most_issues': sorted(issues_by_file.keys(), key=lambda k: len(issues_by_file[k]), reverse=True)[:5]
            }
        }

def main():
    root_dir = os.getcwd()
    scanner = ImportIssueScanner(root_dir)
    
    print("Starting import issues scan...")
    scanner.scan_all_files()
    
    report = scanner.generate_report()
    
    # Save detailed report
    with open('import_issues_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n=== Import Issues Summary ===")
    print(f"Total issues found: {report['total_issues']}")
    print(f"\nIssues by type:")
    for issue_type, count in report['issues_by_type'].items():
        print(f"  {issue_type}: {count}")
    
    print(f"\nFiles with most issues:")
    for file_path in report['summary']['files_with_most_issues']:
        count = report['issues_by_file'][file_path]
        print(f"  {file_path}: {count} issues")
    
    if report['total_issues'] > 0:
        print(f"\nDetailed report saved to: import_issues_report.json")
        return 1
    else:
        print("\nNo import issues found!")
        return 0

if __name__ == '__main__':
    sys.exit(main())