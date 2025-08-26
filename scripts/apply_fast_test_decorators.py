#!/usr/bin/env python3
"""
Apply Fast Test Decorators

Automatically applies @fast_test decorators to test functions that use sleep calls
to improve test suite performance.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_test_functions_with_sleep(content: str) -> List[Tuple[int, str]]:
    """Find test functions that contain sleep calls."""
    functions_with_sleep = []
    
    # Find all test function definitions
    test_func_pattern = r'(async\s+)?def\s+(test_\w+)\s*\([^)]*\):'
    sleep_patterns = [r'time\.sleep\(', r'asyncio\.sleep\(']
    
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line contains a test function definition
        func_match = re.search(test_func_pattern, line)
        if func_match:
            is_async = func_match.group(1) is not None
            func_name = func_match.group(2)
            func_start_line = i
            
            # Find the end of this function by looking for the next function or class
            func_end_line = len(lines)
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if (re.match(r'^(def |class |@)', next_line.strip()) and 
                    not next_line.strip().startswith('@')):
                    func_end_line = j
                    break
            
            # Check if this function contains sleep calls
            func_content = '\n'.join(lines[func_start_line:func_end_line])
            has_sleep = any(re.search(pattern, func_content) for pattern in sleep_patterns)
            
            if has_sleep:
                functions_with_sleep.append((func_start_line, func_name))
        
        i += 1
    
    return functions_with_sleep


def add_performance_imports(content: str) -> str:
    """Add performance helper imports if not present."""
    if 'from test_framework.performance_helpers import' in content:
        return content
    
    # Find where to insert the import (after other imports)
    lines = content.split('\n')
    import_end_line = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            import_end_line = i
        elif line.strip() and not line.strip().startswith('#'):
            break
    
    # Insert the import
    import_line = "from test_framework.performance_helpers import fast_test, timeout_override"
    lines.insert(import_end_line + 1, import_line)
    lines.insert(import_end_line + 2, "")
    
    return '\n'.join(lines)


def apply_fast_test_decorator(content: str, functions_with_sleep: List[Tuple[int, str]]) -> str:
    """Apply @fast_test decorator to functions that need it."""
    lines = content.split('\n')
    
    # Apply decorators in reverse order to avoid line number shifts
    for line_num, func_name in reversed(functions_with_sleep):
        # Check if decorator is already present
        if line_num > 0 and '@fast_test' in lines[line_num - 1]:
            continue
        
        # Find the appropriate indentation
        func_line = lines[line_num]
        indentation = len(func_line) - len(func_line.lstrip())
        decorator = ' ' * indentation + '@fast_test'
        
        # Insert the decorator
        lines.insert(line_num, decorator)
    
    return '\n'.join(lines)


def optimize_test_file(file_path: Path, dry_run: bool = True) -> Tuple[bool, str]:
    """Optimize a single test file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Find functions with sleep calls
        functions_with_sleep = find_test_functions_with_sleep(original_content)
        
        if not functions_with_sleep:
            return False, "No functions with sleep calls found"
        
        # Add imports
        content = add_performance_imports(original_content)
        
        # Apply decorators
        content = apply_fast_test_decorator(content, functions_with_sleep)
        
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        func_names = [name for _, name in functions_with_sleep]
        return True, f"Applied @fast_test to {len(func_names)} functions: {', '.join(func_names[:3])}{'...' if len(func_names) > 3 else ''}"
    
    except Exception as e:
        return False, f"Error: {e}"


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply @fast_test decorators to slow tests")
    parser.add_argument("--test-dir", type=Path, default=Path("netra_backend/tests"),
                       help="Test directory")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--critical-only", action="store_true", 
                       help="Only process files with critical performance issues")
    
    args = parser.parse_args()
    
    if not args.test_dir.exists():
        print(f"Error: Test directory {args.test_dir} does not exist")
        return 1
    
    # Critical files with excessive sleep calls (>10s)
    critical_files = [
        "test_deployment_edge_cases.py",
        "test_gcp_staging_startup_sequence_robustness.py",
        "test_gcp_staging_database_index_creation_skipped.py",
        "test_agent_priority_queue.py",
        "test_agent_metrics_collection.py",
        "test_websocket_auth_cold_start_extended.py",
        "test_routes/test_websocket_advanced.py",
        "test_server_startup_timeout_fix.py",
    ]
    
    if args.critical_only:
        test_files = []
        for critical_file in critical_files:
            matches = list(args.test_dir.rglob(f"*{critical_file}"))
            test_files.extend(matches)
    else:
        test_files = list(args.test_dir.rglob("test_*.py"))
    
    total_files = len(test_files)
    modified_files = 0
    
    print(f"Processing {total_files} test files...")
    print(f"Mode: {'APPLY CHANGES' if args.apply else 'DRY RUN'}")
    print()
    
    for test_file in test_files:
        modified, message = optimize_test_file(test_file, dry_run=not args.apply)
        if modified:
            modified_files += 1
            print(f"[OK] {test_file.relative_to(args.test_dir)}: {message}")
        elif "Error" in message:
            print(f"[ERR] {test_file.relative_to(args.test_dir)}: {message}")
    
    print(f"\nSummary:")
    print(f"Files processed: {total_files}")
    print(f"Files modified: {modified_files}")
    
    if not args.apply and modified_files > 0:
        print(f"\nTo apply these changes, run with --apply flag")
    
    return 0


if __name__ == "__main__":
    exit(main())