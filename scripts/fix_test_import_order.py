"""Fix the import order in test files to ensure setup_test_path() is called first."""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

def fix_import_order(file_path):
    """Fix the import order in a test file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the setup_test_path import and call lines
    setup_import_line_idx = None
    setup_call_line_idx = None
    first_netra_import_idx = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Find setup_test_path import
        if 'from netra_backend.tests.test_utils import setup_test_path' in line:
            setup_import_line_idx = i
        
        # Find setup_test_path() call
        if stripped == 'setup_test_path()':
            setup_call_line_idx = i
        
        # Find first netra_backend import (excluding test_utils)
        if first_netra_import_idx is None:
            if 'from netra_backend' in line and 'test_utils' not in line:
                first_netra_import_idx = i
            elif 'import netra_backend' in line:
                first_netra_import_idx = i
    
    # If we don't have both setup lines, skip this file
    if setup_import_line_idx is None or setup_call_line_idx is None:
        return False, "Missing setup_test_path import or call"
    
    # If there are no netra_backend imports, nothing to fix
    if first_netra_import_idx is None:
        return False, "No netra_backend imports found"
    
    # If setup is already before imports, nothing to fix
    if setup_call_line_idx < first_netra_import_idx:
        return False, "Already in correct order"
    
    # Fix the order
    new_lines = []
    setup_import = lines[setup_import_line_idx]
    setup_call = lines[setup_call_line_idx]
    
    # Remove the old setup lines
    lines_to_skip = {setup_import_line_idx, setup_call_line_idx}
    
    # Also remove any empty lines or comments immediately after the setup call
    if setup_call_line_idx + 1 < len(lines):
        next_line = lines[setup_call_line_idx + 1]
        if next_line.strip() == '' or next_line.strip().startswith('#'):
            lines_to_skip.add(setup_call_line_idx + 1)
    
    # Build the new file content
    added_setup = False
    for i, line in enumerate(lines):
        if i in lines_to_skip:
            continue
        
        # Add setup before first netra_backend import
        if i == first_netra_import_idx and not added_setup:
            # Add a comment if not already present
            if i > 0 and not lines[i-1].strip().startswith('#'):
                new_lines.append('# Add project root to path\n')
            new_lines.append(setup_import)
            new_lines.append(setup_call)
            new_lines.append('\n')
            added_setup = True
        
        new_lines.append(line)
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return True, "Fixed import order"

def main():
    # Find all test files
    test_dir = Path('netra_backend/tests')
    test_files = list(test_dir.rglob('test_*.py'))
    
    fixed_count = 0
    skip_count = 0
    errors = []
    
    for test_file in test_files:
        try:
            fixed, message = fix_import_order(test_file)
            if fixed:
                fixed_count += 1
                print(f"Fixed: {test_file}")
            else:
                skip_count += 1
        except Exception as e:
            errors.append((test_file, str(e)))
    
    print(f"\nSummary:")
    print(f"  - Fixed {fixed_count} files")
    print(f"  - Skipped {skip_count} files (already correct or no setup_test_path)")
    print(f"  - Errors in {len(errors)} files")
    
    if errors:
        print("\nErrors:")
        for file_path, error in errors[:5]:
            print(f"  {file_path}: {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")

if __name__ == '__main__':
    main()