#!/usr/bin/env python3
"""
Check for direct os.environ usage in test files.

This script enforces the unified_environment_management.xml specification
by detecting violations where tests directly modify os.environ instead of
using IsolatedEnvironment.

Used as a pre-commit hook to prevent environment isolation violations.
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Tuple


class EnvironmentViolationChecker(ast.NodeVisitor):
    """AST visitor to detect direct os.environ usage."""
    
    VIOLATION_PATTERNS = [
        # Direct assignment patterns
        ('os.environ[', 'Direct assignment to os.environ'),
        ('os.environ.update', 'Direct update of os.environ'),
        ('os.environ.setdefault', 'Direct setdefault on os.environ'),
        ('os.environ.pop', 'Direct pop from os.environ'),
        ('os.environ.clear', 'Direct clear of os.environ'),
        ('os.getenv', 'Use of os.getenv instead of IsolatedEnvironment'),
        ('os.putenv', 'Use of os.putenv instead of IsolatedEnvironment'),
    ]
    
    ALLOWED_PATTERNS = [
        'get_env().get(',
        'get_env().set(',
        'IsolatedEnvironment',
        'isolated_test_env',
        'test_env_manager',
    ]
    
    def __init__(self, filename: str):
        self.filename = filename
        self.violations = []
        self.line_map = {}
    
    def check_file(self, content: str) -> List[Tuple[int, str, str]]:
        """
        Check file content for violations.
        
        Returns:
            List of (line_number, violation_type, line_content) tuples
        """
        lines = content.split('\n')
        self.line_map = {i+1: line for i, line in enumerate(lines)}
        
        # Check for string patterns
        for line_num, line in self.line_map.items():
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Check for violations
            for pattern, violation_type in self.VIOLATION_PATTERNS:
                if pattern in line:
                    # Check if it's in an allowed context
                    if not any(allowed in line for allowed in self.ALLOWED_PATTERNS):
                        self.violations.append((line_num, violation_type, line.strip()))
        
        # Also parse AST for more complex patterns
        try:
            tree = ast.parse(content)
            self.visit(tree)
        except SyntaxError:
            # If we can't parse, rely on string matching
            pass
        
        return self.violations
    
    def visit_Subscript(self, node):
        """Check for os.environ[key] = value patterns."""
        if isinstance(node.value, ast.Attribute):
            if (isinstance(node.value.value, ast.Name) and 
                node.value.value.id == 'os' and 
                node.value.attr == 'environ'):
                
                line_num = node.lineno
                if line_num in self.line_map:
                    line_content = self.line_map[line_num]
                    if not any(allowed in line_content for allowed in self.ALLOWED_PATTERNS):
                        self.violations.append((
                            line_num,
                            'Direct os.environ access',
                            line_content.strip()
                        ))
        
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check for os.environ.method() calls."""
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Attribute) and
                isinstance(node.func.value.value, ast.Name) and
                node.func.value.value.id == 'os' and
                node.func.value.attr == 'environ'):
                
                method = node.func.attr
                if method in ['update', 'setdefault', 'pop', 'clear']:
                    line_num = node.lineno
                    if line_num in self.line_map:
                        line_content = self.line_map[line_num]
                        if not any(allowed in line_content for allowed in self.ALLOWED_PATTERNS):
                            self.violations.append((
                                line_num,
                                f'os.environ.{method}() call',
                                line_content.strip()
                            ))
        
        self.generic_visit(node)


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Check a single file for environment violations.
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        List of violations found
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        checker = EnvironmentViolationChecker(str(filepath))
        return checker.check_file(content)
    except Exception as e:
        print(f"Error checking {filepath}: {e}", file=sys.stderr)
        return []


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Check for direct os.environ usage in test files'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to check (if not specified, checks all test files)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Suggest fixes for violations'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Exit with error code if violations found'
    )
    
    args = parser.parse_args()
    
    # Determine which files to check
    if args.files:
        files_to_check = [Path(f) for f in args.files]
    else:
        # Check all test files
        project_root = Path(__file__).parent.parent
        test_patterns = [
            'tests/**/*.py',
            'netra_backend/tests/**/*.py',
            'auth_service/tests/**/*.py',
            'frontend/**/*.test.py',
            'test_framework/**/*.py',
        ]
        
        files_to_check = []
        for pattern in test_patterns:
            files_to_check.extend(project_root.glob(pattern))
    
    # Filter to only Python files
    files_to_check = [f for f in files_to_check if f.suffix == '.py']
    
    # Check each file
    total_violations = 0
    files_with_violations = []
    
    for filepath in files_to_check:
        violations = check_file(filepath)
        
        if violations:
            files_with_violations.append(filepath)
            total_violations += len(violations)
            
            try:
                rel_path = filepath.relative_to(Path.cwd())
            except ValueError:
                rel_path = filepath
            
            print(f"\n[FAIL] {rel_path}:")
            for line_num, violation_type, line_content in violations:
                print(f"  Line {line_num}: {violation_type}")
                print(f"    {line_content}")
                
                if args.fix:
                    print("  [TIP] Fix: Replace with get_env().set() or get_env().get()")
    
    # Summary
    if total_violations:
        print(f"\n[ERROR] Found {total_violations} violation(s) in {len(files_with_violations)} file(s)")
        print("\nTo fix these violations:")
        print("1. Import: from shared.isolated_environment import get_env")
        print("2. Replace os.environ['KEY'] = 'value' with get_env().set('KEY', 'value', 'source')")
        print("3. Replace os.getenv('KEY') with get_env().get('KEY')")
        print("4. For test files, use test_framework.environment_isolation fixtures")
        
        if args.strict:
            sys.exit(1)
    else:
        print("[PASS] No environment isolation violations found!")
    
    return 0 if total_violations == 0 else 1


if __name__ == '__main__':
    sys.exit(main())