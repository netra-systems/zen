import ast
import os
from pathlib import Path

def count_function_lines(node):
    """Count actual lines in a function (excluding decorators and docstrings)."""
    start_line = node.lineno
    end_line = node.end_lineno
    
    # Skip decorators
    if hasattr(node, 'decorator_list'):
        if node.decorator_list:
            start_line = node.decorator_list[-1].end_lineno + 1
    
    # Skip docstring
    if (node.body and 
        isinstance(node.body[0], ast.Expr) and 
        isinstance(node.body[0].value, ast.Constant) and
        isinstance(node.body[0].value.value, str)):
        if len(node.body) > 1:
            start_line = node.body[1].lineno
        else:
            return 0
    
    return end_line - start_line + 1

def check_file(filepath):
    violations = []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines = count_function_lines(node)
                    if lines > 8:
                        violations.append((node.name, node.lineno, lines))
        except:
            pass
    return violations

# Check production files
app_dir = Path('app')
violations_by_file = {}

for py_file in app_dir.rglob('*.py'):
    if 'test' not in str(py_file).lower():
        violations = check_file(py_file)
        if violations:
            violations_by_file[str(py_file)] = violations

# Show worst offenders
print("Files with functions exceeding 8 lines:")
sorted_files = sorted(violations_by_file.items(), 
                      key=lambda x: sum(v[2] for v in x[1]), 
                      reverse=True)[:10]

for filepath, violations in sorted_files:
    total_lines = sum(v[2] for v in violations)
    print(f"\n{filepath}: {len(violations)} functions, {total_lines} excess lines")
    for func_name, line_no, lines in violations[:3]:
        print(f"  - {func_name} (line {line_no}): {lines} lines")