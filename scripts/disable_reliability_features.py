#!/usr/bin/env python
"""
Script to disable reliability features that were hiding errors.
See AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md for details.

This script updates all agent files that explicitly enable reliability features
to disable them with a warning comment.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_files_with_reliability_enabled() -> List[Path]:
    """Find all Python files with enable_reliability=True."""
    files = []
    
    # Search patterns
    patterns = [
        r'enable_reliability\s*=\s*True',
    ]
    
    # Directories to search
    search_dirs = [
        'netra_backend/app/agents',
        'tests',
    ]
    
    for search_dir in search_dirs:
        if not Path(search_dir).exists():
            continue
            
        for file_path in Path(search_dir).rglob('*.py'):
            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern in patterns:
                    if re.search(pattern, content):
                        files.append(file_path)
                        break
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
    return files

def update_file(file_path: Path) -> bool:
    """Update a single file to disable reliability features."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Replace enable_reliability=True with False and add warning
        replacements = [
            (
                r'enable_reliability\s*=\s*True,\s*#[^\n]*',
                'enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md'
            ),
            (
                r'enable_reliability\s*=\s*True(?!,)',
                'enable_reliability=False  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md'
            ),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
            
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
            
        return False
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function to disable reliability features across codebase."""
    print("=" * 60)
    print("DISABLING RELIABILITY FEATURES THAT HIDE ERRORS")
    print("See AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md")
    print("=" * 60)
    print()
    
    # Find files
    print("Searching for files with reliability features enabled...")
    files = find_files_with_reliability_enabled()
    
    if not files:
        print("No files found with enable_reliability=True")
        return
        
    print(f"Found {len(files)} files with reliability features enabled:")
    for file_path in files:
        print(f"  - {file_path}")
    print()
    
    # Update files
    print("Updating files...")
    updated = 0
    failed = 0
    
    for file_path in files:
        if update_file(file_path):
            print(f"[OK] Updated: {file_path}")
            updated += 1
        else:
            print(f"[FAIL] Failed: {file_path}")
            failed += 1
            
    print()
    print("=" * 60)
    print(f"SUMMARY: Updated {updated} files, {failed} failures")
    
    if updated > 0:
        print()
        print("IMPORTANT: These reliability features were disabled because they:")
        print("  1. Hide critical errors behind DEBUG logging")
        print("  2. Create zombie agents that appear alive but are dead")
        print("  3. Return fake success results when operations fail")
        print("  4. Generate false positives in health monitoring")
        print()
        print("DO NOT RE-ENABLE without fixing the error visibility issues!")
    
    print("=" * 60)

if __name__ == "__main__":
    main()