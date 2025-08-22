#!/usr/bin/env python3
"""Fix datetime.utcnow() deprecation warnings by replacing with datetime.now(UTC)"""

import os
import re
from pathlib import Path


def fix_datetime_in_file(filepath):
    """Fix datetime deprecation in a single file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check if datetime is imported
    has_datetime_import = bool(re.search(r'from datetime import.*datetime', content) or 
                               re.search(r'import datetime', content))
    
    if not has_datetime_import:
        return False
    
    # Check if UTC is imported
    has_utc_import = bool(re.search(r'from datetime import.*UTC', content))
    
    # Replace datetime.utcnow() with datetime.now(UTC)
    if 'datetime.utcnow()' in content:
        # Add UTC import if needed
        if not has_utc_import:
            # Find the datetime import line
            import_match = re.search(r'(from datetime import[^\n]+)', content)
            if import_match:
                import_line = import_match.group(1)
                # Add UTC to the import
                if ', UTC' not in import_line and 'UTC' not in import_line:
                    new_import = import_line.rstrip() + ', UTC'
                    content = content.replace(import_line, new_import)
            else:
                # If using import datetime, add separate UTC import
                datetime_import_match = re.search(r'(import datetime\n)', content)
                if datetime_import_match:
                    content = content.replace(
                        datetime_import_match.group(1),
                        'import datetime\nfrom datetime import UTC\n'
                    )
        
        # Replace all occurrences
        content = content.replace('datetime.utcnow()', 'datetime.now(UTC)')
        
        # Also handle cases where utcnow is imported directly
        content = re.sub(r'datetime\.datetime\.utcnow\(\)', 'datetime.datetime.now(UTC)', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    
    return False

def main():
    """Fix datetime deprecation in all Python files"""
    root_dir = Path(__file__).parent.parent / 'app'
    
    fixed_files = []
    
    for filepath in root_dir.rglob('*.py'):
        if fix_datetime_in_file(filepath):
            fixed_files.append(filepath)
            print(f"Fixed: {filepath.relative_to(root_dir.parent)}")
    
    print(f"\nTotal files fixed: {len(fixed_files)}")

if __name__ == '__main__':
    main()