#!/usr/bin/env python3
"""
Script to fix all import issues in netra_backend test files.

This script systematically fixes:
1. from netra_backend.tests.* imports -> from tests.* imports
2. from netra_backend.app.* imports -> from app.* imports (within tests directory)
"""

import os
import re
from pathlib import Path


def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: from netra_backend.tests.* imports
        # Replace with from tests.* imports
        content = re.sub(
            r'from netra_backend\.tests\.([a-zA-Z_][a-zA-Z0-9_\.]*)',
            r'from tests.\1',
            content
        )
        
        # Pattern 2: from netra_backend.app.* imports  
        # Replace with from app.* imports
        content = re.sub(
            r'from netra_backend\.app\.([a-zA-Z_][a-zA-Z0-9_\.]*)',
            r'from app.\1',
            content
        )
        
        # Pattern 3: import netra_backend.tests.*
        # Replace with import tests.*
        content = re.sub(
            r'import netra_backend\.tests\.([a-zA-Z_][a-zA-Z0-9_\.]*)',
            r'import tests.\1',
            content
        )
        
        # Pattern 4: import netra_backend.app.*
        # Replace with import app.*
        content = re.sub(
            r'import netra_backend\.app\.([a-zA-Z_][a-zA-Z0-9_\.]*)',
            r'import app.\1',
            content
        )
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix imports in all test files."""
    # Get the netra_backend/tests directory
    tests_dir = Path(__file__).parent / "tests"
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        return
    
    print(f"Fixing imports in test files under: {tests_dir}")
    
    # Find all Python files
    python_files = list(tests_dir.rglob("*.py"))
    
    fixed_count = 0
    total_count = len(python_files)
    
    for file_path in python_files:
        try:
            if fix_imports_in_file(file_path):
                print(f"Fixed: {file_path.relative_to(tests_dir)}")
                fixed_count += 1
        except Exception as e:
            print(f"Error with {file_path}: {e}")
    
    print(f"\nSummary:")
    print(f"Total files checked: {total_count}")
    print(f"Files with fixed imports: {fixed_count}")
    print(f"Files unchanged: {total_count - fixed_count}")


if __name__ == "__main__":
    main()