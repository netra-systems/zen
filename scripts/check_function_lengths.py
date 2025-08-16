#!/usr/bin/env python3
"""Script to check function lengths in triage_sub_agent module"""

import ast
import os
from typing import List, Tuple

def count_function_lines(node: ast.FunctionDef) -> int:
    """Count lines in a function (excluding docstring)"""
    if not node.body:
        return 0
    
    # Skip docstring if present
    start_idx = 0
    if (node.body and isinstance(node.body[0], ast.Expr) and 
        isinstance(node.body[0].value, (ast.Str, ast.Constant)) and
        isinstance(getattr(node.body[0].value, 'value', None), str)):
        start_idx = 1
    
    if start_idx >= len(node.body):
        return 0
    
    first_line = node.body[start_idx].lineno
    last_line = node.body[-1].lineno
    
    # For single-line statements, count as 1
    if first_line == last_line:
        return 1
    
    return last_line - first_line + 1

def analyze_file(file_path: str) -> List[Tuple[str, int]]:
    """Analyze a file for function line violations"""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                line_count = count_function_lines(node)
                if line_count > 8:
                    violations.append((node.name, line_count))
    
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
    
    return violations

def main():
    """Main analysis function"""
    triage_dir = "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\agents\\triage_sub_agent"
    
    print("=== FUNCTION LENGTH VIOLATIONS (>8 lines) ===")
    print()
    
    total_violations = 0
    
    for filename in sorted(os.listdir(triage_dir)):
        if filename.endswith('.py') and filename != '__init__.py':
            file_path = os.path.join(triage_dir, filename)
            violations = analyze_file(file_path)
            
            if violations:
                print(f"FILE: {filename}")
                for func_name, line_count in violations:
                    print(f"   VIOLATION: {func_name}(): {line_count} lines")
                    total_violations += 1
                print()
    
    if total_violations == 0:
        print("SUCCESS: All functions comply with 8-line limit!")
    else:
        print(f"TOTAL VIOLATIONS: {total_violations}")

if __name__ == "__main__":
    main()