import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple


def count_function_lines(node: ast.FunctionDef) -> int:
    """Count lines in a function."""
    if not node.body:
        return 0
    first_line = node.body[0].lineno
    last_line = node.body[-1].end_lineno or node.body[-1].lineno
    return last_line - first_line + 1

def find_long_functions(file_path: str, threshold: int = 80) -> List[Tuple[str, int, int]]:
    """Find functions exceeding threshold lines."""
    violations = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = count_function_lines(node)
                if lines > threshold:
                    violations.append((node.name, node.lineno, lines))
            elif isinstance(node, ast.AsyncFunctionDef):
                lines = count_function_lines(node)
                if lines > threshold:
                    violations.append((node.name, node.lineno, lines))
                    
    except Exception as e:
        pass
    return violations

def scan_directory(path: str, threshold: int = 80):
    """Scan directory for long functions."""
    path_obj = Path(path)
    total_violations = 0
    
    for py_file in path_obj.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        if ".venv" in str(py_file) or "venv" in str(py_file):
            continue
            
        violations = find_long_functions(str(py_file), threshold)
        if violations:
            print(f"\n{py_file}:")
            for func_name, line_no, line_count in violations:
                print(f"  {func_name} (line {line_no}): {line_count} lines")
                total_violations += 1
    
    print(f"\nTotal functions over {threshold} lines: {total_violations}")

if __name__ == "__main__":
    # Scan app directory
    print("Scanning for functions over 80 lines...")
    print("=" * 60)
    scan_directory("app", 80)
    scan_directory("scripts", 80)
    scan_directory("frontend", 80)