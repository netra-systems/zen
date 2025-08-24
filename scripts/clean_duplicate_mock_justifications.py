#!/usr/bin/env python3
"""
Clean Duplicate Mock Justifications Script

This script removes duplicate justification comments that may have been added
multiple times to the same mock lines.
"""

import os
import re
from pathlib import Path

def clean_file(file_path: Path) -> bool:
    """Clean duplicate justifications in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_count = len(lines)
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Check if this is a Mock: comment
        if re.match(r'^\s*#\s*Mock:', line):
            # Add this justification
            cleaned_lines.append(line + '\n')
            i += 1
            
            # Skip subsequent identical Mock: comments
            while i < len(lines) and re.match(r'^\s*#\s*Mock:', lines[i].rstrip()):
                # Skip this duplicate
                i += 1
        else:
            cleaned_lines.append(line + '\n')
            i += 1
    
    if len(cleaned_lines) != original_count:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            print(f"Cleaned {file_path}: {original_count - len(cleaned_lines)} duplicates removed")
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False
    
    return False

def main():
    """Clean duplicate justifications in all project test files"""
    project_dirs = ['tests/', 'netra_backend/tests/', 'auth_service/tests/', 'dev_launcher/tests/']
    
    total_files_cleaned = 0
    
    for project_dir in project_dirs:
        if not os.path.exists(project_dir):
            continue
            
        for file_path in Path(project_dir).rglob('*.py'):
            if 'archive' in str(file_path) or 'legacy' in str(file_path):
                continue
                
            if clean_file(file_path):
                total_files_cleaned += 1
    
    print(f"\n=== CLEANUP COMPLETE ===")
    print(f"Files cleaned: {total_files_cleaned}")

if __name__ == '__main__':
    main()