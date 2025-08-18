#!/usr/bin/env python3
"""Validate refactored example_integration.py file compliance."""

import ast
import sys
from pathlib import Path

def check_function_compliance(file_path):
    """Check if all functions are 8 lines or under."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the AST to count function lines
    tree = ast.parse(content)
    
    function_violations = []
    total_functions = 0
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            total_functions += 1
            func_lines = node.end_lineno - node.lineno + 1
            if func_lines > 8:
                function_violations.append((node.name, func_lines))
    
    print(f"=== Function Compliance Check ===")
    print(f"Total functions: {total_functions}")
    print(f"Total file lines: {len(content.splitlines())}")
    
    if function_violations:
        print(f"FAIL: Found {len(function_violations)} function violations:")
        for name, lines in function_violations:
            print(f"  - {name}: {lines} lines")
        return False
    else:
        print("PASS: All functions are 8 lines or under")
        return True

def main():
    file_path = Path("app/agents/base/example_integration.py")
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1
    
    is_compliant = check_function_compliance(file_path)
    
    if is_compliant:
        print("SUCCESS: REFACTORING COMPLETE - All 9 function violations have been fixed!")
        return 0
    else:
        print("ERROR: REFACTORING INCOMPLETE - Function violations still exist")
        return 1

if __name__ == "__main__":
    sys.exit(main())