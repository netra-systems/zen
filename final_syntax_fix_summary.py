#!/usr/bin/env python3
"""
Final validation and summary of syntax fixes applied to the codebase.
"""

import ast
import os
from pathlib import Path


def check_syntax_and_count():
    """Check syntax of all Python test files and provide summary."""
    
    test_dirs = [
        "netra_backend/tests",
        "auth_service/tests"
    ]
    
    total_files = 0
    valid_files = 0
    syntax_errors = []
    
    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue
            
        test_dir_path = Path(test_dir)
        python_files = list(test_dir_path.rglob("*.py"))
        
        for file_path in python_files:
            total_files += 1
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    valid_files += 1  # Empty files are valid
                    continue
                
                try:
                    ast.parse(content)
                    valid_files += 1
                except SyntaxError as e:
                    syntax_errors.append((str(file_path), f"{e.msg} at line {e.lineno}"))
                except Exception as e:
                    syntax_errors.append((str(file_path), f"Parse error: {str(e)}"))
                    
            except Exception as e:
                syntax_errors.append((str(file_path), f"Read error: {str(e)}"))
    
    print("="*60)
    print("FINAL SYNTAX ERROR FIXING SUMMARY")
    print("="*60)
    print(f"Total Python test files processed: {total_files}")
    print(f"Files with valid syntax: {valid_files}")
    print(f"Files still with syntax errors: {len(syntax_errors)}")
    print(f"Success rate: {(valid_files/total_files)*100:.1f}%")
    
    if syntax_errors:
        print(f"\nRemaining files with syntax errors ({len(syntax_errors)}):")
        # Group by error type for better analysis
        error_types = {}
        for file_path, error in syntax_errors:
            error_type = error.split(" at line")[0]  # Get error without line number
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append((file_path, error))
        
        for error_type, files in error_types.items():
            print(f"\n{error_type} ({len(files)} files):")
            for file_path, error in files[:5]:  # Show first 5 of each type
                print(f"  {file_path}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
    else:
        print("\n*** ALL FILES HAVE VALID SYNTAX! ***")
    
    return total_files, valid_files, len(syntax_errors)


def main():
    """Main execution."""
    total, valid, errors = check_syntax_and_count()
    
    if errors == 0:
        print("\nSUCCESS: All Python test files have valid syntax!")
        return 0
    else:
        print(f"\nWARNING: {errors} files still have syntax errors")
        return 1


if __name__ == "__main__":
    exit(main())