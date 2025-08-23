#!/usr/bin/env python3
"""
Check new files only - applies strict standards to newly created files
while ignoring existing legacy files entirely.
"""
import sys
import subprocess
import os
from pathlib import Path

def get_new_files():
    """Get list of newly added files in this commit."""
    try:
        # Get list of new files (added in this commit)
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-status', '--diff-filter=A'],
            capture_output=True,
            text=True,
            check=True
        )
        
        new_files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    new_files.append(parts[1])
        
        return new_files
    except subprocess.CalledProcessError:
        return []

def check_new_file_compliance(filepath):
    """Apply strict checks only to new files."""
    path = Path(filepath)
    
    if not path.exists():
        return True, []
    
    issues = []
    
    # Only check Python files for now
    if path.suffix == '.py':
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check file size (strict for new files: 300 lines)
        if len(lines) > 300:
            issues.append(f"New file exceeds 300 line limit: {len(lines)} lines")
        
        # Check for relative imports in new files
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('from .') or line.strip().startswith('from ..'):
                issues.append(f"Line {i}: New files must use absolute imports")
        
        # Check for proper type hints in new files
        import ast
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.returns is None and node.name != '__init__':
                        issues.append(f"Function '{node.name}' missing return type hint")
        except SyntaxError:
            issues.append("Syntax error in file")
    
    return len(issues) == 0, issues

def main():
    """Main entry point for pre-commit hook."""
    new_files = get_new_files()
    
    if not new_files:
        # No new files, nothing to check
        return 0
    
    print(f"Checking {len(new_files)} new file(s) for compliance...")
    
    all_passed = True
    failed_count = 0
    
    for filepath in new_files:
        # Only check Python/TypeScript files
        if not filepath.endswith(('.py', '.ts', '.tsx')):
            continue
            
        passed, issues = check_new_file_compliance(filepath)
        
        if not passed:
            all_passed = False
            failed_count += 1
            print(f"\nERROR: NEW FILE: {filepath}")
            for issue in issues:
                print(f"   - {issue}")
            
            # With fail-fast enabled, pre-commit will stop here
            # Return immediately on first failure for faster feedback
            print("\nNew files must meet quality standards.")
            print("Tip: Break large files into smaller modules")
            return 1
        else:
            print(f"OK: NEW FILE: {filepath}")
    
    if not all_passed:
        print(f"\n{failed_count} new file(s) failed quality checks")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())