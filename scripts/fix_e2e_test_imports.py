#!/usr/bin/env python3
"""
Fix E2E test helper imports to use root-level tests directory imports.

This script corrects imports from:
  from tests.e2e.* 
to:
  from tests.e2e.*

and from:
  from tests.*
to:
  from tests.*

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development velocity
- Business Goal: Ensure consistent import patterns for test helpers
- Value Impact: Reduces confusion and prevents import errors
- Strategic Impact: Maintains clean test architecture
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the project."""
    python_files = []
    for file_path in root_dir.rglob("*.py"):
        # Skip __pycache__ directories
        if "__pycache__" in str(file_path):
            continue
        python_files.append(file_path)
    return python_files


def fix_imports_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix imports in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, []
    
    original_content = content
    
    # Pattern to match netra_backend.tests.e2e imports
    pattern1 = r'from netra_backend\.tests\.e2e\.(.*)'
    replacement1 = r'from tests.e2e.\1'
    
    # Pattern to match netra_backend.tests.unified imports
    pattern2 = r'from netra_backend\.tests\.unified\.(.*)'
    replacement2 = r'from tests.\1'
    
    # Find all matches before replacing
    matches1 = re.findall(pattern1, content)
    matches2 = re.findall(pattern2, content)
    
    # Apply replacements
    content = re.sub(pattern1, replacement1, content)
    content = re.sub(pattern2, replacement2, content)
    
    # Record changes
    for match in matches1:
        changes.append(f"  from tests.e2e.{match} -> from tests.e2e.{match}")
    for match in matches2:
        changes.append(f"  from tests.{match} -> from tests.{match}")
    
    # Write back if changed
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False, []
    
    return False, []


def main():
    """Main function to fix all imports."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("Fixing E2E test helper imports...")
    print(f"Project root: {project_root}")
    print("-" * 60)
    
    # Find all Python files
    python_files = find_python_files(project_root)
    
    # Track statistics
    files_modified = 0
    total_changes = 0
    
    # Process each file
    for file_path in python_files:
        modified, changes = fix_imports_in_file(file_path)
        
        if modified:
            files_modified += 1
            total_changes += len(changes)
            rel_path = file_path.relative_to(project_root)
            print(f"\nFixed {rel_path}:")
            for change in changes:
                print(change)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Files scanned: {len(python_files)}")
    print(f"  Files modified: {files_modified}")
    print(f"  Total import fixes: {total_changes}")
    
    if files_modified == 0:
        print("\nNo files needed fixing - all imports are already correct!")
    else:
        print(f"\nSuccessfully fixed {total_changes} imports in {files_modified} files.")


if __name__ == "__main__":
    main()