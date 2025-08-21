#!/usr/bin/env python3
"""Validate all auth service imports across the netra_backend codebase."""

import os
import ast
import sys
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

class AuthImportValidator:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.errors = []
        self.warnings = []
        self.valid_imports = []
        
        # Expected import patterns for auth services
        self.auth_modules = {
            'auth_integration': {
                'auth': ['get_current_user', 'require_admin', 'require_permission', 'ActiveUserWsDep', 'validate_token_jwt'],
                'interfaces': []
            },
            'clients': {
                'auth_client': ['auth_client'],
                'auth_client_core': ['AuthServiceClient'],
                'auth_client_cache': ['AuthCircuitBreakerManager'],
                'auth_client_config': ['Environment', 'OAuthConfig']
            },
            'core': {
                'cross_service_auth': [],
                'cross_service_validators': []
            }
        }
        
    def validate_file(self, file_path: Path) -> List[Dict]:
        """Validate imports in a single Python file."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    
                    # Check auth_integration imports
                    if 'auth_integration' in module:
                        self._validate_auth_import(node, file_path, issues, 'auth_integration')
                    
                    # Check clients.auth imports
                    elif 'clients.auth' in module:
                        self._validate_auth_import(node, file_path, issues, 'clients')
                    
                    # Check core.cross_service imports
                    elif 'cross_service' in module:
                        self._validate_auth_import(node, file_path, issues, 'core')
                        
        except SyntaxError as e:
            issues.append({
                'file': str(file_path),
                'type': 'error',
                'message': f'Syntax error in file: {e}'
            })
        except Exception as e:
            issues.append({
                'file': str(file_path),
                'type': 'error',
                'message': f'Failed to parse file: {e}'
            })
            
        return issues
    
    def _validate_auth_import(self, node, file_path, issues, category):
        """Validate auth-related imports."""
        module = node.module or ''
        line = node.lineno
        
        # Extract what's being imported
        imports = []
        for alias in node.names:
            if alias.name == '*':
                imports.append('*')
            else:
                imports.append(alias.name)
        
        # Record valid import
        self.valid_imports.append({
            'file': str(file_path),
            'line': line,
            'module': module,
            'imports': imports,
            'category': category
        })
    
    def scan_directory(self, directory: Path) -> Dict:
        """Scan all Python files in directory for auth imports."""
        all_issues = []
        
        for py_file in directory.rglob('*.py'):
            # Skip virtual environments and cache
            if any(part in str(py_file) for part in ['venv', '__pycache__', '.git', 'node_modules', 'migrations']):
                continue
            
            issues = self.validate_file(py_file)
            if issues:
                all_issues.extend(issues)
        
        return {
            'issues': all_issues,
            'valid_imports': self.valid_imports,
            'summary': self._generate_summary(all_issues)
        }
    
    def _generate_summary(self, issues: List[Dict]) -> Dict:
        """Generate a summary of validation results."""
        # Count imports by category
        import_categories = defaultdict(int)
        import_modules = defaultdict(set)
        
        for imp in self.valid_imports:
            import_categories[imp['category']] += 1
            import_modules[imp['category']].add(imp['module'])
        
        summary = {
            'total_issues': len(issues),
            'errors': len([i for i in issues if i['type'] == 'error']),
            'warnings': len([i for i in issues if i['type'] == 'warning']),
            'total_valid_imports': len(self.valid_imports),
            'by_category': dict(import_categories),
            'unique_modules': {k: list(v) for k, v in import_modules.items()},
            'files_with_imports': len(set(i['file'] for i in self.valid_imports))
        }
        
        return summary

def main():
    """Main function to validate all auth imports."""
    # Get the netra_backend directory
    root_path = Path(__file__).parent / 'netra_backend'
    
    if not root_path.exists():
        print(f"Error: {root_path} does not exist")
        sys.exit(1)
    
    print("=" * 80)
    print("AUTH SERVICE IMPORT VALIDATION")
    print("=" * 80)
    print(f"Scanning directory: {root_path}\n")
    
    validator = AuthImportValidator(root_path)
    results = validator.scan_directory(root_path)
    
    # Print summary
    summary = results['summary']
    print("SUMMARY")
    print("-" * 40)
    print(f"Total auth-related imports found: {summary['total_valid_imports']}")
    print(f"Files with auth imports: {summary['files_with_imports']}")
    print(f"Total issues found: {summary['total_issues']}")
    
    if summary['errors'] > 0:
        print(f"  [ERROR] Errors: {summary['errors']}")
    
    print("\nIMPORT CATEGORIES:")
    print("-" * 40)
    for category, count in summary['by_category'].items():
        print(f"  {category}: {count} imports")
        if category in summary['unique_modules']:
            modules = summary['unique_modules'][category]
            for module in sorted(modules)[:5]:  # Show first 5 modules
                print(f"    - {module}")
            if len(modules) > 5:
                print(f"    ... and {len(modules) - 5} more")
    
    # Show some example imports
    print("\nEXAMPLE IMPORTS (first 15):")
    print("-" * 40)
    for imp in results['valid_imports'][:15]:
        rel_path = Path(imp['file']).relative_to(root_path)
        print(f"  {rel_path}:{imp['line']}")
        print(f"    from {imp['module']} import {', '.join(imp['imports'])}")
    
    # Check if there are any potential issues
    if summary['total_issues'] > 0:
        print("\n[WARNING] ISSUES FOUND:")
        print("-" * 40)
        for issue in results['issues']:
            print(f"  {issue['file']}")
            print(f"    {issue['message']}")
    
    # Exit with appropriate code
    if summary['errors'] > 0:
        print("\n[FAILED] Validation failed with errors")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All auth imports are valid!")

if __name__ == "__main__":
    main()