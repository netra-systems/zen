#!/usr/bin/env python3
"""
Quick Syntax Error Scanner - Focus on critical test files first
"""

import ast
import os
from pathlib import Path
import traceback

def check_syntax(file_path):
    """Check a single file for syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        ast.parse(content, filename=str(file_path))
        return None  # No error
    except SyntaxError as e:
        return {
            'error_type': 'SyntaxError',
            'error': str(e),
            'line': getattr(e, 'lineno', None),
            'column': getattr(e, 'offset', None),
            'text': getattr(e, 'text', '').strip() if getattr(e, 'text', None) else None
        }
    except Exception as e:
        return {
            'error_type': 'OtherError',
            'error': str(e),
            'line': None,
            'column': None,
            'text': None
        }

def main():
    """Scan critical test files first."""

    # Critical test patterns to scan first
    critical_patterns = [
        "tests/mission_critical/*.py",
        "netra_backend/tests/critical/*.py",
        "tests/e2e/test_websocket*.py",
        "netra_backend/tests/agents/test_*websocket*.py",
        "netra_backend/tests/agents/test_*agent*.py",
        "tests/integration/test_*websocket*.py"
    ]

    # Regular test directories
    test_dirs = [
        "tests",
        "netra_backend/tests",
        "auth_service/tests"
    ]

    errors_found = []
    files_scanned = 0

    print("QUICK SYNTAX SCAN - CRITICAL FILES FIRST")
    print("="*60)

    # Scan critical patterns first
    root = Path(".")
    critical_files = set()

    for pattern in critical_patterns:
        critical_files.update(root.glob(pattern))

    print(f"\nScanning {len(critical_files)} critical files...")
    for file_path in sorted(critical_files):
        if file_path.suffix == '.py' and "__pycache__" not in str(file_path):
            files_scanned += 1
            error = check_syntax(file_path)
            if error:
                errors_found.append({
                    'file': str(file_path),
                    'error': error,
                    'priority': 'CRITICAL'
                })
                print(f"ERROR CRITICAL: {file_path}")
                print(f"   {error['error_type']}: {error['error']}")
                if error['line']:
                    print(f"   Line {error['line']}: {error['text']}")

    # Quick scan of other test directories (sample)
    print(f"\nScanning sample of other test files...")
    other_files = []
    for test_dir in test_dirs:
        test_dir_path = root / test_dir
        if test_dir_path.exists():
            for py_file in test_dir_path.rglob("*.py"):
                if py_file not in critical_files and "__pycache__" not in str(py_file):
                    other_files.append(py_file)

    # Sample first 50 non-critical files
    for file_path in sorted(other_files)[:50]:
        files_scanned += 1
        error = check_syntax(file_path)
        if error:
            errors_found.append({
                'file': str(file_path),
                'error': error,
                'priority': 'NORMAL'
            })
            print(f"ERROR NORMAL: {file_path}")
            print(f"   {error['error_type']}: {error['error']}")
            if error['line']:
                print(f"   Line {error['line']}: {error['text']}")

    # Summary
    print(f"\nSUMMARY:")
    print(f"Files scanned: {files_scanned}")
    print(f"Files with errors: {len(errors_found)}")

    critical_errors = [e for e in errors_found if e['priority'] == 'CRITICAL']
    normal_errors = [e for e in errors_found if e['priority'] == 'NORMAL']

    print(f"Critical errors: {len(critical_errors)}")
    print(f"Normal errors: {len(normal_errors)}")

    if critical_errors:
        print(f"\nCRITICAL FILES TO FIX FIRST:")
        for error_info in critical_errors[:10]:
            print(f"  {error_info['file']}")

    return errors_found

if __name__ == "__main__":
    errors = main()