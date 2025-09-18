#!/usr/bin/env python3
"""
Script to identify syntax errors in test files
"""
import ast
import os
import sys
from pathlib import Path

def check_syntax_errors(root_dir):
    """Check for syntax errors in Python test files"""
    test_dirs = [
        "tests",
        "netra_backend/tests",
        "auth_service/tests",
        "frontend/tests"
    ]

    errors = []
    total_files = 0

    for test_dir in test_dirs:
        test_path = Path(root_dir) / test_dir
        if not test_path.exists():
            continue

        for py_file in test_path.rglob("*.py"):
            total_files += 1
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    ast.parse(content, filename=str(py_file))
            except SyntaxError as e:
                errors.append({
                    'file': str(py_file),
                    'error': str(e),
                    'lineno': e.lineno,
                    'offset': e.offset,
                    'text': e.text.strip() if e.text else None
                })
            except Exception as e:
                errors.append({
                    'file': str(py_file),
                    'error': f"Other error: {str(e)}",
                    'lineno': None,
                    'offset': None,
                    'text': None
                })

    print(f"Checked {total_files} test files")
    print(f"Found {len(errors)} syntax errors")
    print("\n" + "="*80)

    # Sort errors by priority - mission critical, websocket, agent tests first
    def priority_key(error):
        file_path = error['file'].lower()
        if 'mission_critical' in file_path:
            return 0
        elif 'websocket' in file_path:
            return 1
        elif 'agent' in file_path:
            return 2
        elif 'integration' in file_path:
            return 3
        else:
            return 4

    errors.sort(key=priority_key)

    for i, error in enumerate(errors[:50], 1):  # Show first 50 errors
        print(f"\n{i}. {error['file']}")
        if error['lineno']:
            print(f"   Line {error['lineno']}: {error['error']}")
            if error['text']:
                try:
                    safe_text = error['text'].encode('ascii', 'replace').decode('ascii')
                    print(f"   Text: {safe_text}")
                except:
                    print(f"   Text: [Text with special characters]")
        else:
            print(f"   Error: {error['error']}")
        print("-" * 40)

    if len(errors) > 50:
        print(f"\n... and {len(errors) - 50} more errors")

    return errors

if __name__ == "__main__":
    root_dir = "."
    errors = check_syntax_errors(root_dir)
    sys.exit(1 if errors else 0)