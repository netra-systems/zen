#!/usr/bin/env python3
"""
Comprehensive import fixer for Netra codebase.
Fixes ALL 'from app.' imports to 'from netra_backend.app.' patterns.
"""

import os
import re
import sys
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix all 'from app.' imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: Direct 'from app.' imports
        content = re.sub(
            r'^(\s*)from app\.(.+)$',
            r'\1from netra_backend.app.\2',
            content,
            flags=re.MULTILINE
        )
        
        # Pattern 2: Direct 'import app.' imports  
        content = re.sub(
            r'^(\s*)import app\.(.+)$',
            r'\1import netra_backend.app.\2',
            content,
            flags=re.MULTILINE
        )
        
        # Check if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False
        
    return False

def find_python_files_with_app_imports(root_dir):
    """Find all Python files that contain 'from app.' imports."""
    files_with_issues = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for problematic import patterns
                    if (re.search(r'^from app\.', content, re.MULTILINE) or
                        re.search(r'^import app\.', content, re.MULTILINE)):
                        files_with_issues.append(file_path)
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
    return files_with_issues

def main():
    # Get the root directory
    root_dir = Path(__file__).parent
    print(f"Scanning for import issues in: {root_dir}")
    
    # Find all files with problematic imports
    files_with_issues = find_python_files_with_app_imports(root_dir)
    
    if not files_with_issues:
        print("No files found with 'from app.' import patterns!")
        return
        
    print(f"Found {len(files_with_issues)} files with import issues:")
    for file_path in files_with_issues:
        rel_path = os.path.relpath(file_path, root_dir)
        print(f"  {rel_path}")
    
    # Fix imports in all files
    fixed_count = 0
    for file_path in files_with_issues:
        if fix_imports_in_file(file_path):
            fixed_count += 1
            rel_path = os.path.relpath(file_path, root_dir)
            print(f"✅ Fixed: {rel_path}")
    
    print(f"\n🎉 Successfully fixed imports in {fixed_count} files!")
    
    # Verify no issues remain
    remaining_issues = find_python_files_with_app_imports(root_dir)
    if remaining_issues:
        print(f"⚠️  WARNING: {len(remaining_issues)} files still have issues!")
        for file_path in remaining_issues[:5]:  # Show first 5
            rel_path = os.path.relpath(file_path, root_dir)
            print(f"  {rel_path}")
    else:
        print("✅ All import issues resolved!")

if __name__ == "__main__":
    main()