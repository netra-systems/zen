import ast
import os
from pathlib import Path
from typing import Dict, List, Tuple

def count_function_lines(node: ast.FunctionDef) -> int:
    """Count actual lines of code in a function."""
    if not node.body:
        return 0
    
    # Get start and end lines
    start_line = node.lineno
    end_line = node.end_lineno or start_line
    
    # Return total lines (including decorators and signature)
    return end_line - start_line + 1

def find_long_functions(file_path: str, max_lines: int = 8) -> List[Tuple[str, int, int]]:
    """Find functions exceeding max_lines in a file."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = count_function_lines(node)
                if lines > max_lines:
                    violations.append((node.name, node.lineno, lines))
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return violations

def scan_directory(path: str = "app/db", max_lines: int = 8) -> Dict[str, List[Tuple[str, int, int]]]:
    """Scan all Python files in directory for long functions."""
    results = {}
    
    for root, dirs, files in os.walk(path):
        # Skip test directories
        if 'test' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                violations = find_long_functions(file_path, max_lines)
                if violations:
                    results[file_path] = violations
    
    return results

if __name__ == "__main__":
    print("Scanning app/db for functions over 8 lines...\n")
    results = scan_directory("app/db", 8)
    
    if not results:
        print("[PASS] No violations found!")
    else:
        total_violations = 0
        for file_path, violations in sorted(results.items()):
            print(f"\n[FILE] {file_path}")
            for func_name, line_no, line_count in violations:
                print(f"  [VIOLATION] Function '{func_name}' at line {line_no}: {line_count} lines")
                total_violations += 1
        
        print(f"\n[TOTAL] Total violations: {total_violations}")