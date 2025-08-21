#!/usr/bin/env python3
"""Enhanced script to fix datetime.utcnow() deprecation warnings in all patterns"""

import os
import re
from pathlib import Path


def fix_datetime_in_file(filepath) -> bool:
    """Fix datetime deprecation in a single file"""
    content = _read_file_content(filepath)
    original_content = content
    if not _has_datetime_import(content):
        return False
    content = _fix_utc_imports(content)
    content = _replace_datetime_patterns(content)
    return _save_if_changed(filepath, content, original_content)


def _read_file_content(filepath) -> str:
    """Read file content safely."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def _has_datetime_import(content: str) -> bool:
    """Check if datetime is imported."""
    return bool(re.search(r'from datetime import.*datetime', content) or 
                re.search(r'import datetime', content))


def _fix_utc_imports(content: str) -> str:
    """Add UTC import if needed for utcnow usage."""
    if not re.search(r'datetime\.utcnow', content):
        return content
    if re.search(r'from datetime import.*UTC', content):
        return content
    return _add_utc_import(content)


def _add_utc_import(content: str) -> str:
    """Add UTC to existing datetime import."""
    import_match = re.search(r'(from datetime import[^\n]+)', content)
    if import_match:
        return _update_from_import(content, import_match)
    else:
        return _add_separate_utc_import(content)


def _update_from_import(content: str, import_match) -> str:
    """Update from datetime import line to include UTC."""
    import_line = import_match.group(1)
    if ', UTC' not in import_line and 'UTC' not in import_line:
        new_import = import_line.rstrip() + ', UTC'
        return content.replace(import_line, new_import)
    return content


def _add_separate_utc_import(content: str) -> str:
    """Add separate UTC import for import datetime pattern."""
    datetime_import_match = re.search(r'(import datetime\n)', content)
    if datetime_import_match:
        return content.replace(
            datetime_import_match.group(1),
            'import datetime\nfrom datetime import UTC\n'
        )
    return content


def _replace_datetime_patterns(content: str) -> str:
    """Replace all datetime.utcnow patterns."""
    # 1. datetime.utcnow() -> datetime.now(UTC)
    content = content.replace('datetime.utcnow()', 'datetime.now(UTC)')
    # 2. Field patterns
    content = re.sub(r'Field\(default_factory=datetime\.utcnow', 
                     r'Field(default_factory=lambda: datetime.now(UTC)', content)
    # 3. field patterns  
    content = re.sub(r'field\(default_factory=datetime\.utcnow',
                     r'field(default_factory=lambda: datetime.now(UTC)', content)
    # 4. datetime.datetime.utcnow() -> datetime.datetime.now(UTC)
    content = re.sub(r'datetime\.datetime\.utcnow\(\)', 'datetime.datetime.now(UTC)', content)
    return content


def _save_if_changed(filepath, content: str, original_content: str) -> bool:
    """Save file if content changed."""
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