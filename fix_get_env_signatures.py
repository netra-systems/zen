#!/usr/bin/env python3
"""
Automated script to fix get_env() signature issues across codebase.

Issue #639 Remediation - Fix get_env().get("key", "default") -> get_env().get("key", "default")
"""

import os
import re
import sys
from pathlib import Path

def find_problematic_files():
    """Find files with get_env(key, default) pattern."""
    problematic_files = []
    pattern = re.compile(r'get_env\s*\(\s*"[^"]*"\s*,\s*"[^"]*"\s*\)')
    
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    matches = pattern.findall(content)
                    if matches:
                        problematic_files.append({
                            'file': str(file_path),
                            'matches': matches
                        })
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
    return problematic_files

def fix_file(file_path, dry_run=True):
    """Fix get_env patterns in a single file."""
    pattern = re.compile(r'get_env\s*\(\s*("[^"]*")\s*,\s*("[^"]*")\s*\)')
    replacement = r'get_env().get(\1, \2)'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            
        new_content = pattern.sub(replacement, original_content)
        
        if original_content != new_content:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ FIXED: {file_path}")
            else:
                print(f"🔍 WOULD FIX: {file_path}")
                
            return True
    except Exception as e:
        print(f"❌ ERROR fixing {file_path}: {e}")
        return False
        
    return False

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    
    print("🔍 Scanning for get_env() signature issues...")
    problematic_files = find_problematic_files()
    
    print(f"Found {len(problematic_files)} files with issues")
    
    for file_info in problematic_files:
        print(f"FILE: {file_info['file']}")
        for match in file_info['matches']:
            print(f"  - {match}")
    
    if "--apply" in sys.argv:
        print("\n🛠️ Applying fixes...")
        fixed_count = 0
        for file_info in problematic_files:
            if fix_file(file_info['file'], dry_run=False):
                fixed_count += 1
                
        print(f"✅ FIXED: {fixed_count} files")
    else:
        print("\n🔍 DRY RUN - Use --apply to actually fix files")
        fixed_count = 0
        for file_info in problematic_files:
            if fix_file(file_info['file'], dry_run=True):
                fixed_count += 1
                
        print(f"🔍 WOULD FIX: {fixed_count} files")