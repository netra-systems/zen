#!/usr/bin/env python3
"""
Comprehensive fix for datetime.now(timezone.utc) deprecation warnings.
Replaces with datetime.now(timezone.utc) and ensures proper imports.
"""

import os
import re
from pathlib import Path
from typing import List, Set

def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the directory tree."""
    python_files = []
    exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv', '.tox'}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files

def fix_file_datetime(file_path: Path) -> bool:
    """Fix datetime deprecation in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'datetime.now(timezone.utc)' not in content:
            return False
        
        original_content = content
        
        # Check current imports
        has_datetime_import = 'import datetime' in content or 'from datetime import' in content
        has_timezone_import = 'timezone' in content
        
        # If using datetime but no timezone import, add it
        if has_datetime_import and not has_timezone_import:
            # Find existing datetime import to extend
            datetime_from_match = re.search(r'from datetime import ([^\n]+)', content)
            if datetime_from_match:
                imports = datetime_from_match.group(1)
                if 'timezone' not in imports:
                    # Add timezone to existing import
                    new_imports = imports.rstrip() + ', timezone'
                    content = content.replace(
                        f'from datetime import {imports}',
                        f'from datetime import {new_imports}'
                    )
            else:
                # Add timezone import after datetime import
                content = re.sub(
                    r'(import datetime\n)',
                    r'\1from datetime import timezone\n',
                    content
                )
        
        # Replace datetime.now(timezone.utc) with datetime.now(timezone.utc)
        content = content.replace('datetime.now(timezone.utc)', 'datetime.now(timezone.utc)')
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix datetime deprecation warnings."""
    root_dir = Path(__file__).parent.parent
    print(f"Scanning for Python files in {root_dir}")
    
    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")
    
    fixed_files = []
    
    for file_path in python_files:
        if fix_file_datetime(file_path):
            fixed_files.append(file_path)
            rel_path = file_path.relative_to(root_dir)
            print(f"Fixed: {rel_path}")
    
    print(f"\nSummary: Fixed {len(fixed_files)} files")
    
    if fixed_files:
        print("Files modified:")
        for file_path in fixed_files:
            rel_path = file_path.relative_to(root_dir)
            print(f"  {rel_path}")

if __name__ == "__main__":
    main()