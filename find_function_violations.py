import ast
import os
from pathlib import Path
from typing import List, Tuple

def count_function_lines(node: ast.FunctionDef) -> int:
    """Count the actual lines of code in a function (excluding docstring)."""
    if not node.body:
        return 0
    
    start_line = node.body[0].lineno
    # Skip docstring if present
    if (isinstance(node.body[0], ast.Expr) and 
        isinstance(node.body[0].value, ast.Constant) and
        isinstance(node.body[0].value.value, str)):
        if len(node.body) > 1:
            start_line = node.body[1].lineno
        else:
            return 0
    
    end_line = node.end_lineno or node.lineno
    return end_line - start_line + 1

def find_violations_in_file(filepath: Path, max_lines: int = 8) -> List[Tuple[str, int, int]]:
    """Find all functions exceeding max_lines in a file."""
    violations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(filepath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = count_function_lines(node)
                if lines > max_lines:
                    violations.append((node.name, node.lineno, lines))
    except Exception:
        pass  # Skip files that can't be parsed
    
    return violations

def scan_directories(directories: List[str], max_lines: int = 8):
    """Scan directories for function violations."""
    all_violations = {}
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "__pycache__" in str(py_file) or "/test" in str(py_file):
                continue
                
            violations = find_violations_in_file(py_file, max_lines)
            if violations:
                all_violations[str(py_file)] = violations
    
    return all_violations

def main():
    directories = ["backend", "clients", "config", "security", "monitoring", "data", "alembic", "netra_mcp"]
    violations = scan_directories(directories, max_lines=8)
    
    if not violations:
        print("✅ No function violations found!")
        return
    
    print(f"Found violations in {len(violations)} files:\n")
    total_functions = 0
    
    for filepath, funcs in violations.items():
        print(f"\n{filepath}:")
        for func_name, line_no, lines in funcs:
            print(f"  - {func_name} (line {line_no}): {lines} lines (needs splitting into ~{lines//8 + 1} functions)")
            total_functions += 1
    
    print(f"\nTotal functions to fix: {total_functions}")

if __name__ == "__main__":
    main()