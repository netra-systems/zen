#!/usr/bin/env python3
"""
Prioritized checking - stricter for main application code, more lenient for tests and utilities.
Focus on maintaining quality where it matters most.
"""
import sys
import argparse
from pathlib import Path
import ast

def get_file_priority(filepath):
    """Determine priority level of a file based on its location."""
    path_str = str(filepath).replace('\\', '/')
    
    # Priority 1 (HIGHEST): Core application code
    if any(p in path_str for p in [
        'netra_backend/app/core',
        'netra_backend/app/services',
        'auth_service/auth_core',
        'frontend/src/components/core',
        'frontend/src/services'
    ]):
        return 1
    
    # Priority 2 (HIGH): General application code
    if any(p in path_str for p in [
        'netra_backend/app',
        'auth_service',
        'frontend/src'
    ]):
        return 2
    
    # Priority 3 (MEDIUM): Scripts and utilities
    if 'scripts/' in path_str:
        return 3
    
    # Priority 4 (LOW): Tests
    if any(p in path_str for p in ['test', 'tests', 'test_', '_test']):
        return 4
    
    # Priority 5 (LOWEST): Everything else
    return 5

def check_file_by_priority(filepath, priority):
    """Apply different standards based on file priority."""
    path = Path(filepath)
    
    if not path.exists():
        return True, []
    
    issues = []
    
    # Different limits based on priority
    limits = {
        1: {'file_lines': 300, 'function_lines': 25, 'complexity': 10},
        2: {'file_lines': 450, 'function_lines': 40, 'complexity': 15},
        3: {'file_lines': 600, 'function_lines': 60, 'complexity': 20},
        4: {'file_lines': 1000, 'function_lines': 100, 'complexity': 30},
        5: {'file_lines': 2000, 'function_lines': 200, 'complexity': 50}
    }
    
    limit = limits[priority]
    
    if path.suffix == '.py':
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check file size based on priority
        if len(lines) > limit['file_lines']:
            severity = "ERROR" if priority <= 2 else "WARNING"
            issues.append(f"{severity}: File exceeds {limit['file_lines']} line limit ({len(lines)} lines)")
        
        # Parse AST for function checks (only for high priority files)
        if priority <= 2:
            try:
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                        if func_lines > limit['function_lines']:
                            severity = "ERROR" if priority == 1 else "WARNING"
                            issues.append(f"{severity}: Function '{node.name}' exceeds {limit['function_lines']} lines ({func_lines} lines)")
            except SyntaxError:
                if priority == 1:
                    issues.append("ERROR: Syntax error in core file")
    
    # Return based on priority - only fail for high priority files with errors
    if priority <= 2 and any("ERROR" in issue for issue in issues):
        return False, issues
    
    return True, issues

def main():
    """Main entry point for pre-commit hook."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--priority', default='app', help='Priority focus area')
    parser.add_argument('filenames', nargs='*', help='Files to check')
    args = parser.parse_args()
    
    if not args.filenames:
        return 0
    
    print(f"Checking files with priority-based standards...")
    
    files_by_priority = {}
    for filepath in args.filenames:
        priority = get_file_priority(filepath)
        if priority not in files_by_priority:
            files_by_priority[priority] = []
        files_by_priority[priority].append(filepath)
    
    # Show what we're checking
    priority_names = {
        1: "[U+1F534] CRITICAL (Core)",
        2: "[U+1F7E0] HIGH (App)",
        3: "[U+1F7E1] MEDIUM (Scripts)",
        4: "[U+1F7E2] LOW (Tests)",
        5: "[U+26AA] MINIMAL (Other)"
    }
    
    for priority in sorted(files_by_priority.keys()):
        print(f"\n{priority_names[priority]}: {len(files_by_priority[priority])} files")
    
    # Check files
    has_errors = False
    for priority in sorted(files_by_priority.keys()):
        for filepath in files_by_priority[priority]:
            passed, issues = check_file_by_priority(filepath, priority)
            
            if issues:
                print(f"\n{priority_names[priority]} - {filepath}")
                for issue in issues:
                    print(f"   {issue}")
                    if "ERROR" in issue:
                        has_errors = True
    
    if has_errors:
        print("\nERROR: Critical issues found in high-priority files")
        print("Fail-fast enabled - stopping at first critical error")
        return 1
    else:
        print("\nOK: All priority checks passed (warnings may exist)")
        return 0

if __name__ == '__main__':
    sys.exit(main())