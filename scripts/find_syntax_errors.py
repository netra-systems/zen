#!/usr/bin/env python3
"""
Comprehensive syntax error detection script for e2e tests.
Scans all Python files recursively and reports syntax errors with precise locations.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict


def scan_python_file(file_path: Path) -> List[Tuple[int, str]]:
    """
    Parse a Python file and return syntax errors with line numbers.
    
    Returns:
        List of tuples (line_number, error_message)
    """
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try to parse the file
        ast.parse(content, filename=str(file_path))
        
    except SyntaxError as e:
        errors.append((e.lineno or 0, str(e)))
    except UnicodeDecodeError as e:
        errors.append((0, f"Unicode decode error: {e}"))
    except Exception as e:
        errors.append((0, f"Unexpected error: {e}"))
        
    return errors


def scan_directory(directory: Path) -> Dict[Path, List[Tuple[int, str]]]:
    """
    Recursively scan directory for Python files with syntax errors.
    
    Returns:
        Dictionary mapping file paths to lists of errors
    """
    results = {}
    
    if not directory.exists():
        print(f"Directory does not exist: {directory}")
        return results
        
    # Find all Python files recursively
    python_files = list(directory.rglob("*.py"))
    
    print(f"Scanning {len(python_files)} Python files in {directory}...")
    
    for file_path in python_files:
        errors = scan_python_file(file_path)
        if errors:
            results[file_path] = errors
            
    return results


def print_results(results: Dict[Path, List[Tuple[int, str]]]) -> None:
    """Print syntax error results in a clear format."""
    
    if not results:
        print("[U+2713] No syntax errors found!")
        return
        
    print(f"\n! Found syntax errors in {len(results)} files:\n")
    
    for file_path, errors in results.items():
        print(f"File: {file_path}")
        for line_num, error_msg in errors:
            if line_num > 0:
                print(f"   Line {line_num}: {error_msg}")
            else:
                print(f"   {error_msg}")
        print()


def main():
    """Main execution function."""
    
    # Get the e2e tests directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    e2e_tests_dir = project_root / "tests" / "e2e"
    
    print(f"Scanning for syntax errors in: {e2e_tests_dir}")
    print("=" * 60)
    
    # Scan for syntax errors
    results = scan_directory(e2e_tests_dir)
    
    # Print results
    print_results(results)
    
    # Exit with appropriate code
    if results:
        print(f"X Found syntax errors in {len(results)} files")
        sys.exit(1)
    else:
        print("[U+2713] All files passed syntax check")
        sys.exit(0)


if __name__ == "__main__":
    main()