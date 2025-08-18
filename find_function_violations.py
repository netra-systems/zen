import ast
import os
from pathlib import Path
from typing import List, Tuple

def count_function_lines(node):
    """Count physical lines in function definition."""
    return node.end_lineno - node.lineno + 1

def find_violations_in_file(filepath):
    """Find functions over 8 lines in a file."""
    violations = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines = count_function_lines(node)
                if lines > 8:
                    violations.append({
                        'function': node.name,
                        'lines': lines,
                        'start': node.lineno,
                        'end': node.end_lineno
                    })
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    
    return violations

def scan_routes_directory():
    """Scan all Python files in routes directory."""
    routes_dir = Path('app/routes')
    results = {}
    
    for py_file in routes_dir.rglob('*.py'):
        # Skip test files
        if 'test' in str(py_file).lower() or '__pycache__' in str(py_file):
            continue
            
        violations = find_violations_in_file(py_file)
        if violations:
            results[str(py_file)] = violations
    
    return results

def main():
    """Main function to find and report violations."""
    print("=" * 80)
    print("FUNCTION LENGTH VIOLATIONS IN ROUTES (>8 LINES)")
    print("=" * 80)
    
    results = scan_routes_directory()
    
    if not results:
        print("\n[PASS] No violations found! All functions are 8 lines or less.")
        return
    
    total_violations = 0
    
    for filepath, violations in sorted(results.items()):
        print(f"\n[FILE] {filepath}")
        print("-" * 40)
        for v in violations:
            print(f"  [VIOLATION] {v['function']}() - {v['lines']} lines (lines {v['start']}-{v['end']})")
            total_violations += 1
    
    print("\n" + "=" * 80)
    print(f"TOTAL VIOLATIONS: {total_violations}")
    print("=" * 80)

if __name__ == "__main__":
    main()