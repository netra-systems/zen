#!/usr/bin/env python3
"""Enhanced script to fix datetime.utcnow() deprecation warnings in all patterns"""

import os
import re
from pathlib import Path

def fix_datetime_in_file(filepath):
    """Fix datetime deprecation in a single file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changed = False
    
    # Check if datetime is imported
    has_datetime_import = bool(re.search(r'from datetime import.*datetime', content) or 
                               re.search(r'import datetime', content))
    
    if not has_datetime_import:
        return False
    
    # Check if UTC is imported
    has_utc_import = bool(re.search(r'from datetime import.*UTC', content))
    
    # Check if we have any datetime.utcnow patterns
    has_utcnow = bool(re.search(r'datetime\.utcnow', content))
    
    if has_utcnow:
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
                    changed = True
            else:
                # If using import datetime, add separate UTC import
                datetime_import_match = re.search(r'(import datetime\n)', content)
                if datetime_import_match:
                    content = content.replace(
                        datetime_import_match.group(1),
                        'import datetime\nfrom datetime import UTC\n'
                    )
                    changed = True
        
        # Replace patterns:
        # 1. datetime.utcnow() -> datetime.now(UTC)
        if 'datetime.utcnow()' in content:
            content = content.replace('datetime.utcnow()', 'datetime.now(UTC)')
            changed = True
        
        # 2. Field(default_factory=datetime.utcnow) -> Field(default_factory=lambda: datetime.now(UTC))
        pattern = r'Field\(default_factory=datetime\.utcnow'
        replacement = r'Field(default_factory=lambda: datetime.now(UTC)'
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changed = True
        
        # 3. field(default_factory=datetime.utcnow) -> field(default_factory=lambda: datetime.now(UTC))
        pattern = r'field\(default_factory=datetime\.utcnow'
        replacement = r'field(default_factory=lambda: datetime.now(UTC)'
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changed = True
        
        # 4. datetime.datetime.utcnow() -> datetime.datetime.now(UTC)
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