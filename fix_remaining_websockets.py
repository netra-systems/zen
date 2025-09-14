#!/usr/bin/env python3
"""
Quick script to fix remaining websockets exception imports
"""

import os
import re
import glob

def fix_websockets_exceptions(file_path: str) -> bool:
    """Fix websockets.exceptions imports in a file. Returns True if changes made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix all imports from websockets.exceptions
        # Pattern: from websockets.exceptions import X, Y, Z
        content = re.sub(
            r'from websockets\.exceptions import ([^\n]+)',
            r'from websockets import \1',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def main():
    """Fix websockets.exceptions imports across the codebase."""
    base_dir = "/Users/anthony/Desktop/netra-apex"
    patterns = [
        os.path.join(base_dir, "tests/**/*.py"),
        os.path.join(base_dir, "scripts/*.py"),
        os.path.join(base_dir, "netra_backend/**/*.py")
    ]
    
    fixed_count = 0
    total_files = 0
    
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            # Only process files that contain websockets.exceptions imports
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if 'from websockets.exceptions import' in f.read():
                        total_files += 1
                        if fix_websockets_exceptions(file_path):
                            print(f"Fixed: {file_path}")
                            fixed_count += 1
            except:
                continue
    
    print(f"\nSummary: Fixed {fixed_count} out of {total_files} files with websockets.exceptions imports")

if __name__ == "__main__":
    main()