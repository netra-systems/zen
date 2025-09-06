#!/usr/bin/env python3
"""
Find files with actual syntax errors (not fixed by the fixer).
"""

import ast
import os
import sys
from pathlib import Path


def check_syntax(file_path):
    """Check if a Python file has syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            return True, "Empty file"
        
        try:
            ast.parse(content)
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}"
        except Exception as e:
            return False, f"ParseError: {str(e)}"
    
    except Exception as e:
        return False, f"ReadError: {str(e)}"


def find_syntax_errors(directory):
    """Find all Python files with syntax errors in a directory."""
    directory = Path(directory)
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return
    
    python_files = list(directory.rglob("*.py"))
    print(f"Checking {len(python_files)} Python files in {directory}...")
    
    error_files = []
    valid_files = 0
    
    for file_path in python_files:
        is_valid, message = check_syntax(file_path)
        if not is_valid:
            error_files.append((str(file_path), message))
            print(f"ERROR: {file_path} - {message}")
        else:
            valid_files += 1
            if len(error_files) < 20:  # Show progress for first few
                print(f"OK: {file_path}")
    
    print(f"\nSummary:")
    print(f"Valid files: {valid_files}")
    print(f"Files with syntax errors: {len(error_files)}")
    
    if error_files:
        print(f"\nFiles with syntax errors:")
        for file_path, error in error_files[:50]:  # Show first 50
            print(f"  {file_path}: {error}")
        if len(error_files) > 50:
            print(f"  ... and {len(error_files) - 50} more")
    
    return error_files


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python find_real_syntax_errors.py <directory>")
        print("Example: python find_real_syntax_errors.py netra_backend/tests")
        sys.exit(1)
    
    directory = sys.argv[1]
    error_files = find_syntax_errors(directory)
    
    if error_files:
        sys.exit(1)
    else:
        print("All files have valid syntax!")
        sys.exit(0)