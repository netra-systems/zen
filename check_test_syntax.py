#!/usr/bin/env python3
"""
Script to identify test files with syntax errors.
Used to diagnose the P0 infrastructure crisis with 339 corrupted test files.
"""

import os
import py_compile
import sys
from pathlib import Path

def check_file_syntax(file_path):
    """Check if a Python file has syntax errors."""
    try:
        py_compile.compile(file_path, doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return str(e)
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def main():
    """Main function to check test files for syntax errors."""
    test_directories = [
        'analytics_service/tests',
        'auth_service/tests',
        'auth_service/test_framework',
        'dev_launcher/tests',
        'netra_backend/tests',
        'test_framework',
        'tests'
    ]

    syntax_errors = []
    total_files = 0

    for test_dir in test_directories:
        if not os.path.exists(test_dir):
            print(f"Warning: Directory {test_dir} does not exist")
            continue

        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    total_files += 1

                    # Check syntax
                    error = check_file_syntax(file_path)
                    if error:
                        syntax_errors.append({
                            'file': file_path,
                            'error': error
                        })

                    # Progress indicator
                    if total_files % 100 == 0:
                        print(f"Checked {total_files} files, found {len(syntax_errors)} syntax errors so far...")

    print(f"\n=== SYNTAX ERROR REPORT ===")
    print(f"Total files checked: {total_files}")
    print(f"Files with syntax errors: {len(syntax_errors)}")
    if total_files > 0:
        print(f"Error rate: {len(syntax_errors)/total_files*100:.1f}%")
    else:
        print("Error rate: N/A (no files found)")

    if syntax_errors:
        print(f"\n=== FIRST 20 SYNTAX ERRORS ===")
        for i, error_info in enumerate(syntax_errors[:20]):
            print(f"\n{i+1}. {error_info['file']}")
            print(f"   Error: {error_info['error']}")

    return len(syntax_errors)

if __name__ == "__main__":
    error_count = main()
    sys.exit(0 if error_count == 0 else 1)