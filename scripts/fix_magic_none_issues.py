#!/usr/bin/env python3
"""
Script to systematically fix all MagicNone issues in test files.

This script:
1. Finds all files with MagicNone references
2. Adds proper mock imports if missing
3. Replaces all MagicNone with MagicMock()
4. Reports all changes made

Business Value: Fixes critical syntax errors preventing tests from running.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

def find_files_with_magic_none(root_dir: str) -> List[Path]:
    """Find all Python files containing MagicNone."""
    files_with_magic_none = []
    root_path = Path(root_dir)
    
    for py_file in root_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'MagicNone' in content:
                    files_with_magic_none.append(py_file)
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return files_with_magic_none

def has_mock_import(content: str) -> bool:
    """Check if file already has proper mock imports."""
    mock_import_patterns = [
        r'from unittest\.mock import',
        r'import.*Mock',
    ]
    
    for pattern in mock_import_patterns:
        if re.search(pattern, content):
            return True
    return False

def add_mock_import(content: str) -> str:
    """Add mock import to file content."""
    # Find the import section (after docstring, before first class/function)
    lines = content.split('\n')
    
    # Look for the last import statement
    last_import_idx = -1
    in_docstring = False
    docstring_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track docstrings
        if '"""' in stripped or "'''" in stripped:
            docstring_count += stripped.count('"""') + stripped.count("'''")
            if docstring_count % 2 == 1:
                in_docstring = True
            else:
                in_docstring = False
        
        # Skip docstring lines
        if in_docstring:
            continue
            
        # Find import lines
        if (stripped.startswith('import ') or 
            stripped.startswith('from ') or 
            stripped.startswith('#') or
            stripped == ''):
            if stripped.startswith('import ') or stripped.startswith('from '):
                last_import_idx = i
    
    # Insert mock import after last import
    if last_import_idx >= 0:
        mock_import_line = "from unittest.mock import MagicMock, AsyncMock, Mock, patch"
        lines.insert(last_import_idx + 1, mock_import_line)
    else:
        # If no imports found, add after potential docstring
        insert_idx = 0
        if lines and (lines[0].strip().startswith('"""') or lines[0].strip().startswith("'''")):
            # Find end of module docstring
            for i, line in enumerate(lines[1:], 1):
                if '"""' in line or "'''" in line:
                    insert_idx = i + 1
                    break
        
        lines.insert(insert_idx, "from unittest.mock import MagicMock, AsyncMock, Mock, patch")
        lines.insert(insert_idx + 1, "")  # Add blank line
    
    return '\n'.join(lines)

def fix_magic_none_in_content(content: str) -> Tuple[str, int]:
    """Replace all MagicNone with MagicMock() in content."""
    # Replace MagicNone with MagicMock()
    fixed_content = re.sub(r'\bMagicNone\b', 'MagicMock()', content)
    
    # Count replacements
    original_count = len(re.findall(r'\bMagicNone\b', content))
    
    return fixed_content, original_count

def fix_file(file_path: Path) -> Tuple[bool, int, str]:
    """Fix a single file and return (success, replacements_made, error_msg)."""
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Check if already has mock imports
        needs_import = not has_mock_import(original_content)
        
        # Add mock import if needed
        content = original_content
        if needs_import:
            content = add_mock_import(content)
        
        # Fix MagicNone issues
        fixed_content, replacement_count = fix_magic_none_in_content(content)
        
        # Write back if changed
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True, replacement_count, ""
        else:
            return True, 0, "No changes needed"
            
    except Exception as e:
        return False, 0, str(e)

def main():
    """Main script execution."""
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"[SEARCH] Searching for MagicNone issues in: {root_dir}")
    
    # Find all files with MagicNone
    files_to_fix = find_files_with_magic_none(root_dir)
    
    if not files_to_fix:
        print("[SUCCESS] No files with MagicNone found!")
        return
    
    print(f"[FOUND] Found {len(files_to_fix)} files with MagicNone issues")
    
    # Process each file
    total_replacements = 0
    successful_fixes = 0
    errors = []
    
    for file_path in files_to_fix:
        print(f"[FIXING] {file_path}")
        
        success, replacements, error_msg = fix_file(file_path)
        
        if success:
            successful_fixes += 1
            total_replacements += replacements
            if replacements > 0:
                print(f"   [SUCCESS] Fixed {replacements} MagicNone instances")
            else:
                print(f"   [INFO] {error_msg}")
        else:
            errors.append((file_path, error_msg))
            print(f"   [ERROR] {error_msg}")
    
    # Summary report
    print(f"\n[SUMMARY REPORT]")
    print(f"   Files processed: {len(files_to_fix)}")
    print(f"   Successful fixes: {successful_fixes}")
    print(f"   Total MagicNone replacements: {total_replacements}")
    print(f"   Errors encountered: {len(errors)}")
    
    if errors:
        print(f"\n[ERRORS]:")
        for file_path, error_msg in errors:
            print(f"   {file_path}: {error_msg}")
    
    print(f"\n[COMPLETE] MagicNone fix script completed!")

if __name__ == "__main__":
    main()