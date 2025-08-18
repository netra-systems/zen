#!/usr/bin/env python3
"""Quick check for route function compliance."""

import os
import re
from pathlib import Path


def count_function_lines(file_path):
    """Count lines in each function."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return violations
        
    current_function = None
    function_start = 0
    indent_level = 0
    in_function = False
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            continue
            
        # Check for function definition
        if re.match(r'^(\s*)(def\s+\w+|async\s+def\s+\w+)', line):
            # If we were in a function, check its length
            if in_function and current_function:
                func_lines = i - function_start - 1
                if func_lines > 8:
                    violations.append({
                        'function': current_function,
                        'lines': func_lines,
                        'start_line': function_start
                    })
            
            # Start new function
            current_function = stripped.split('(')[0].replace('async def ', '').replace('def ', '')
            function_start = i
            indent_level = len(line) - len(line.lstrip())
            in_function = True
            
        elif in_function and line.strip():
            # Check if we're still in the function
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and not line.strip().startswith(('@', 'class ', 'def ', 'async def')):
                # Function ended
                func_lines = i - function_start - 1
                if func_lines > 8:
                    violations.append({
                        'function': current_function,
                        'lines': func_lines,
                        'start_line': function_start
                    })
                in_function = False
                current_function = None
    
    # Check last function if file ended
    if in_function and current_function:
        func_lines = len(lines) - function_start
        if func_lines > 8:
            violations.append({
                'function': current_function,
                'lines': func_lines,
                'start_line': function_start
            })
    
    return violations


def main():
    """Check route functions."""
    route_dir = Path('app/routes')
    total_violations = 0
    total_files = 0
    
    print("Checking route function compliance...")
    print("=" * 60)
    
    for py_file in route_dir.rglob('*.py'):
        if py_file.name.startswith('__'):
            continue
            
        violations = count_function_lines(py_file)
        total_files += 1
        
        if violations:
            total_violations += len(violations)
            print(f"\n📁 {py_file.relative_to(Path('.'))}:")
            for violation in violations:
                print(f"  ❌ {violation['function']}: {violation['lines']} lines (line {violation['start_line']})")
        else:
            print(f"✅ {py_file.relative_to(Path('.'))} - All functions ≤8 lines")
    
    print("\n" + "=" * 60)
    print(f"📊 SUMMARY:")
    print(f"   Total files checked: {total_files}")
    print(f"   Total violations: {total_violations}")
    print(f"   Files with violations: {sum(1 for py_file in route_dir.rglob('*.py') if not py_file.name.startswith('__') and count_function_lines(py_file))}")
    
    if total_violations == 0:
        print("🎉 ALL ROUTE FUNCTIONS COMPLY WITH 8-LINE LIMIT!")
    else:
        print(f"⚠️  {total_violations} functions need to be reduced to ≤8 lines")


if __name__ == '__main__':
    main()