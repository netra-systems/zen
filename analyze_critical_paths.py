import os
import ast
import sys

CRITICAL_PATHS = [
    'app/agents/supervisor',
    'app/agents/admin_tool_dispatcher',
    'app/agents/corpus_admin',
    'app/agents/data_sub_agent',
    'app/agents/supply_researcher',
    'app/agents/triage_sub_agent',
    'app/services/corpus',
    'app/db',
    'app/websocket',
    'app/llm',
]

def count_function_lines(node):
    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
        return node.end_lineno - node.lineno + 1
    return 0

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines = count_function_lines(node)
                if lines > 8:
                    violations.append((node.name, lines, node.lineno))
        
        return violations
    except:
        return []

violations_by_path = {}
total_violations = 0

for critical_path in CRITICAL_PATHS:
    if not os.path.exists(critical_path):
        continue
    
    path_violations = []
    for root, dirs, files in os.walk(critical_path):
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                filepath = os.path.join(root, file)
                file_violations = analyze_file(filepath)
                if file_violations:
                    path_violations.append({
                        'file': filepath.replace(os.sep, '/'),
                        'violations': file_violations
                    })
                    total_violations += len(file_violations)
    
    if path_violations:
        violations_by_path[critical_path] = path_violations

print(f'CRITICAL PATH FUNCTION VIOLATIONS (>8 lines)')
print('=' * 80)
print(f'Total violations in critical paths: {total_violations}')
print()

for path, files in violations_by_path.items():
    print(f'\n{path}:')
    print('-' * 40)
    file_count = 0
    for file_info in files[:5]:  # Show first 5 files per path
        file_count += 1
        print(f'  {file_info["file"]}')
        for func_name, lines, lineno in file_info['violations'][:3]:  # Show first 3 violations per file
            print(f'    - {func_name}() at line {lineno}: {lines} lines')
    
    total_files = len(files)
    if total_files > 5:
        print(f'  ... and {total_files - 5} more files with violations')