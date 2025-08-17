#!/usr/bin/env python
"""Analyze compliance violations in backend."""
import os
import ast
import json

def count_lines(file_path):
    """Count lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def analyze_functions(file_path):
    """Analyze functions in a Python file."""
    violations = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    line_count = node.end_lineno - node.lineno + 1
                    if line_count > 8:
                        violations.append({
                            'name': node.name,
                            'lines': line_count,
                            'start': node.lineno,
                            'end': node.end_lineno
                        })
    except:
        pass
    return violations

def analyze_backend():
    """Analyze backend for compliance violations."""
    results = {
        'file_violations': [],
        'function_violations': []
    }
    
    # Walk through app directory
    for root, dirs, files in os.walk('app'):
        # Skip __pycache__ and .pyc files
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                # Check file size
                lines = count_lines(file_path)
                if lines > 300:
                    results['file_violations'].append({
                        'file': file_path,
                        'lines': lines
                    })
                
                # Check function sizes
                func_violations = analyze_functions(file_path)
                for v in func_violations:
                    v['file'] = file_path
                    results['function_violations'].append(v)
    
    # Sort by size
    results['file_violations'].sort(key=lambda x: x['lines'], reverse=True)
    results['function_violations'].sort(key=lambda x: x['lines'], reverse=True)
    
    return results

def main():
    print("Analyzing backend compliance...")
    results = analyze_backend()
    
    # Save to JSON
    with open('violations.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nFound {len(results['file_violations'])} file violations (>300 lines)")
    print(f"Found {len(results['function_violations'])} function violations (>8 lines)")
    
    # Show top violations
    if results['file_violations']:
        print("\nTop 5 file violations:")
        for v in results['file_violations'][:5]:
            print(f"  {v['lines']:4d} lines: {v['file']}")
    
    if results['function_violations']:
        print("\nTop 5 function violations:")
        for v in results['function_violations'][:5]:
            print(f"  {v['lines']:4d} lines: {v['name']} in {v['file']}")

if __name__ == '__main__':
    main()