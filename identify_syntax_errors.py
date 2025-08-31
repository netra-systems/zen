#!/usr/bin/env python3
"""Identify all test files with syntax errors preventing discovery."""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple

def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """Check if a Python file has syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def find_test_files() -> List[Path]:
    """Find all test files in the project."""
    test_files = []
    
    # Search patterns for test files
    patterns = [
        "tests/**/*.py",
        "test_*.py",
        "*_test.py"
    ]
    
    root = Path(__file__).parent
    
    for pattern in patterns:
        test_files.extend(root.glob(pattern))
    
    # Also check service-specific test directories
    service_dirs = [
        "netra_backend/tests",
        "auth_service/tests",
        "frontend/tests"
    ]
    
    for service_dir in service_dirs:
        service_path = root / service_dir
        if service_path.exists():
            test_files.extend(service_path.glob("**/*.py"))
    
    return sorted(set(test_files))

def main():
    """Main function to identify syntax errors in test files."""
    print("Scanning for test files with syntax errors...\n")
    
    test_files = find_test_files()
    print(f"Found {len(test_files)} test files to check\n")
    
    error_files = []
    
    for test_file in test_files:
        is_valid, error_msg = check_syntax(test_file)
        if not is_valid:
            error_files.append((test_file, error_msg))
            rel_path = test_file.relative_to(Path(__file__).parent)
            print(f"ERROR: {rel_path}")
            print(f"   Error: {error_msg}\n")
    
    print(f"\nSummary:")
    print(f"   Total test files: {len(test_files)}")
    print(f"   Files with errors: {len(error_files)}")
    print(f"   Files without errors: {len(test_files) - len(error_files)}")
    
    if error_files:
        print(f"\nFOUND {len(error_files)} test files with syntax errors!")
        print("\nFiles needing fixes:")
        for file_path, _ in error_files:
            rel_path = file_path.relative_to(Path(__file__).parent)
            print(f"  - {rel_path}")
    else:
        print("\nAll test files have valid syntax!")
    
    return len(error_files)

if __name__ == "__main__":
    sys.exit(main())