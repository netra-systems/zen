#!/usr/bin/env python3
"""
Fix E2E Test ConnectionManager Import Issues

This script systematically fixes all e2e tests that are importing the old
ConnectionManager class name, replacing it with the new ConnectionManager
and proper import patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Test Infrastructure Stability
- Value Impact: Restores 46 failing e2e tests critical for release confidence
- Strategic Impact: Enables continuous deployment and quality assurance
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple


def find_files_with_connection_manager_imports(root_dir: str) -> List[Path]:
    """Find all Python files importing ConnectionManager from connection_manager."""
    files = []
    
    # Search patterns for files that likely contain the problematic import
    search_dirs = [
        "app/tests/e2e",
        "tests/unified/e2e", 
        "tests/websocket",
        "app/tests/unit",
        "app/tests/critical",
        "app/tests/websocket"
    ]
    
    for search_dir in search_dirs:
        search_path = Path(root_dir) / search_dir
        if search_path.exists():
            for py_file in search_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'from netra_backend.app.websocket.connection_manager import' in content and 'ConnectionManager' in content:
                            files.append(py_file)
                except Exception as e:
                    print(f"Warning: Could not read {py_file}: {e}")
    
    return files

def fix_connection_manager_imports(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix ConnectionManager imports in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: Direct import replacement
        pattern1 = r'from app\.websocket\.connection_manager import ConnectionManager'
        replacement1 = 'from netra_backend.app.websocket.connection_manager import get_connection_monitor, ConnectionManager'
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            changes.append("Updated import statement to use ConnectionManager")
        
        # Pattern 2: Mixed imports with ConnectionManager
        pattern2 = r'from app\.websocket\.connection_manager import ([^,]*,\s*)*ConnectionManager([^,\n]*)'
        def replace_mixed_import(match):
            full_match = match.group(0)
            if 'get_connection_monitor' not in full_match and 'ConnectionManager' not in full_match:
                return full_match.replace('ConnectionManager', 'get_connection_monitor, ConnectionManager')
            elif 'ConnectionManager' in full_match and 'ConnectionManager' not in full_match:
                return full_match.replace('ConnectionManager', 'ConnectionManager')
            return full_match
        
        content = re.sub(pattern2, replace_mixed_import, content)
        
        # Pattern 3: Fix type hints and instantiation
        # Type hint fixes
        content = re.sub(r':\s*ConnectionManager\b', ': ConnectionManager', content)
        content = re.sub(r'spec=ConnectionManager\b', 'spec=ConnectionManager', content)
        
        # Instantiation fixes - replace ConnectionManager() with get_connection_monitor()
        pattern3 = r'\bConnectionManager\(\)'
        if re.search(pattern3, content):
            content = re.sub(pattern3, 'get_connection_monitor()', content)
            changes.append("Updated instantiation to use get_connection_monitor()")
        
        # Pattern 4: Variable assignments
        content = re.sub(r'=\s*ConnectionManager\b', '= get_connection_monitor', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        
        return False, []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, [f"Error: {e}"]

def main():
    """Main function to fix all e2e test import issues."""
    root_dir = Path(__file__).parent.parent.absolute()
    
    print("Finding files with ConnectionManager import issues...")
    files_to_fix = find_files_with_connection_manager_imports(str(root_dir))
    
    if not files_to_fix:
        print("No files found with ConnectionManager import issues")
        return
    
    print(f"Found {len(files_to_fix)} files to fix:")
    for file_path in files_to_fix:
        print(f"  - {file_path}")
    
    print("\nFixing import issues...")
    
    fixed_count = 0
    total_changes = []
    
    for file_path in files_to_fix:
        was_fixed, changes = fix_connection_manager_imports(file_path)
        if was_fixed:
            fixed_count += 1
            print(f"Fixed {file_path}")
            for change in changes:
                print(f"   - {change}")
            total_changes.extend(changes)
        else:
            print(f"No changes needed for {file_path}")
    
    print(f"\nSummary:")
    print(f"  Files processed: {len(files_to_fix)}")
    print(f"  Files fixed: {fixed_count}")
    print(f"  Total changes: {len(total_changes)}")
    
    if fixed_count > 0:
        print(f"\nSuccessfully fixed {fixed_count} e2e test files!")
        print("Next steps:")
        print("  1. Run tests to verify fixes: python unified_test_runner.py --level integration")
        print("  2. Check for any remaining import issues")
        print("  3. Review changes with git diff")
    else:
        print("\nNo files were modified. All imports may already be correct.")

if __name__ == "__main__":
    main()