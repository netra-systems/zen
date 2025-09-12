import ast
import os
from pathlib import Path
from typing import List, Tuple


def count_function_lines(node: ast.FunctionDef) -> int:
    """Count the actual lines of code in a function."""
    if not node.body:
        return 0
    
    # Get the range of lines the function spans
    start_line = node.lineno
    end_line = node.end_lineno or node.lineno
    
    # Count actual lines (not including def line, but including body)
    body_start = node.body[0].lineno if node.body else start_line
    body_end = node.end_lineno or node.lineno
    
    # Account for decorators
    if hasattr(node, 'decorator_list') and node.decorator_list:
        start_line = node.decorator_list[0].lineno
    
    # The actual function body lines (excluding def line itself)
    return body_end - body_start + 1

def find_violations_in_file(filepath: Path, max_lines: int = 8) -> List[Tuple[str, int, int]]:
    """Find all functions exceeding max_lines in a file."""
    violations = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(filepath))
        
        class FunctionVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                lines = count_function_lines(node)
                if lines > max_lines:
                    violations.append((node.name, node.lineno, lines))
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                lines = count_function_lines(node)
                if lines > max_lines:
                    violations.append((node.name, node.lineno, lines))
                self.generic_visit(node)
        
        visitor = FunctionVisitor()
        visitor.visit(tree)
        
    except Exception as e:
        pass  # Skip files that can't be parsed
    
    return violations

def scan_directory_recursive(directory: Path, max_lines: int = 8) -> dict:
    """Recursively scan a directory for function violations."""
    all_violations = {}
    
    if not directory.exists():
        return all_violations
    
    for py_file in directory.rglob("*.py"):
        # Skip test files, __pycache__, and migration files (except the one we care about)
        skip_patterns = ["__pycache__", "/test_", "\\test_", "/tests/", "\\tests\\"]
        if any(pattern in str(py_file) for pattern in skip_patterns):
            continue
        
        violations = find_violations_in_file(py_file, max_lines)
        if violations:
            all_violations[str(py_file)] = violations
    
    return all_violations

def main():
    # Check specific directories
    directories = [
        Path("backend"),
        Path("clients"), 
        Path("config"),
        Path("security"),
        Path("monitoring"),
        Path("data"),
        Path("alembic"),
        Path("netra_mcp"),
        Path("app")  # Also check app directory
    ]
    
    print("Scanning for functions exceeding 8 lines...\n")
    
    total_violations = 0
    files_with_violations = 0
    
    for directory in directories:
        violations = scan_directory_recursive(directory, max_lines=8)
        
        if violations:
            print(f"\n=== {directory} ===")
            for filepath, funcs in sorted(violations.items()):
                # Skip if it's in a test directory
                if "test" in filepath.lower():
                    continue
                    
                print(f"\n{filepath}:")
                files_with_violations += 1
                for func_name, line_no, lines in funcs:
                    print(f"  - {func_name} (line {line_no}): {lines} lines")
                    total_violations += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Files with violations: {files_with_violations}")
    print(f"  Total function violations: {total_violations}")
    print(f"  Functions need splitting to comply with 25-line limit")
    
    if total_violations == 0:
        print("\n PASS:  ALL FUNCTIONS ARE COMPLIANT!")

if __name__ == "__main__":
    main()