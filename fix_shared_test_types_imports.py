#!/usr/bin/env python
"""
Fix imports of shared_test_types in test files.
"""

import re
from pathlib import Path

def fix_shared_test_types_import(file_path: Path) -> bool:
    """Fix the import path for shared_test_types."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    # Check current directory relative to tests
    relative_path = file_path.relative_to(Path(__file__).parent / 'netra_backend' / 'tests')
    current_dir = relative_path.parent
    
    # Determine correct import path based on location
    if current_dir.name == 'helpers':
        # Same directory
        new_import = 'from .shared_test_types import'
    elif current_dir.parent == Path('.'):
        # Direct child of tests directory (e.g., agents, services)
        new_import = 'from ..helpers.shared_test_types import'
    else:
        # Nested deeper
        depth = len(current_dir.parts)
        dots = '.' * (depth + 1)
        new_import = f'from {dots}helpers.shared_test_types import'
    
    # Replace the import
    patterns = [
        r'from \.shared_test_types import',
        r'from shared_test_types import',
        r'from tests\.helpers\.shared_test_types import',
        r'from \.\.shared_test_types import',
        r'from \.\.\. shared_test_types import'
    ]
    
    modified = False
    for pattern in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, new_import, content)
            modified = True
    
    if modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[FIXED] {file_path.relative_to(Path(__file__).parent)}")
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
    
    return False

def main():
    """Main function."""
    project_root = Path(__file__).parent
    tests_dir = project_root / 'netra_backend' / 'tests'
    
    # Find all files that import shared_test_types
    files_to_fix = []
    for py_file in tests_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'shared_test_types import' in content:
                    files_to_fix.append(py_file)
        except:
            pass
    
    print(f"Found {len(files_to_fix)} files with shared_test_types imports")
    
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_shared_test_types_import(file_path):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()