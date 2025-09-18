#!/usr/bin/env python3
"""
Validate test file syntax - fast syntax checker for Issue #1332
"""
import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple

def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """Check if file has valid Python syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Parse error: {str(e)}"

def main():
    """Main validation function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--directory":
        test_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tests")
    else:
        test_dir = Path("tests")

    if not test_dir.exists():
        print(f"ERROR: Directory {test_dir} does not exist")
        sys.exit(1)

    print(f"Validating syntax in {test_dir}")

    valid_files = []
    error_files = []

    # Find all Python test files
    for py_file in test_dir.rglob("*.py"):
        is_valid, error = check_syntax(py_file)
        if is_valid:
            valid_files.append(py_file)
        else:
            error_files.append((py_file, error))

    total_files = len(valid_files) + len(error_files)

    print(f"\nSYNTAX VALIDATION RESULTS:")
    print(f"  Total files: {total_files}")
    print(f"  Valid files: {len(valid_files)} ({len(valid_files)/total_files*100:.1f}%)")
    print(f"  Error files: {len(error_files)} ({len(error_files)/total_files*100:.1f}%)")

    if error_files:
        print(f"\nFILES WITH SYNTAX ERRORS ({len(error_files)}):")
        for file_path, error in error_files[:20]:  # Show first 20
            try:
                rel_path = file_path.relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path
            print(f"  {rel_path}: {error}")

        if len(error_files) > 20:
            print(f"  ... and {len(error_files) - 20} more files")

    return len(error_files)

if __name__ == "__main__":
    error_count = main()
    sys.exit(0 if error_count == 0 else 1)