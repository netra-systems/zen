#!/usr/bin/env python3
"""
Fix dollar amount syntax errors in test files.
Replaces $""XXX"" patterns with $XXX to fix syntax errors.
"""

import re
import os
from pathlib import Path

def fix_dollar_quotes(file_path):
    """Fix dollar quote patterns in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    # Pattern to match $""number"" or $""number with text""
    pattern1 = r'\$""(\d+[KMB]?)""\+?'
    pattern2 = r'\$""(\d+)""\+'
    pattern3 = r'\$""(\d+K?)""\+'

    original_content = content

    # Replace patterns
    content = re.sub(pattern1, r'$\1+', content)
    content = re.sub(pattern2, r'$\1+', content)
    content = re.sub(pattern3, r'$\1+', content)

    # Also handle cases without the + sign
    content = re.sub(r'\$""(\d+[KMB]?)""', r'$\1', content)

    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False
    return False

def main():
    """Find and fix all files with dollar quote issues."""
    root_dir = Path('.')
    test_dirs = ['tests/mission_critical', 'tests/critical', 'tests/e2e', 'tests/integration', 'tests/unit']

    fixed_count = 0
    for test_dir in test_dirs:
        test_path = root_dir / test_dir
        if not test_path.exists():
            continue

        for file_path in test_path.glob('*.py'):
            if fix_dollar_quotes(file_path):
                print(f"Fixed: {file_path}")
                fixed_count += 1

    print(f"\n✅ Total files fixed: {fixed_count}")

    # Verify no more dollar quote patterns remain
    remaining_count = 0
    for test_dir in test_dirs:
        test_path = root_dir / test_dir
        if not test_path.exists():
            continue

        for file_path in test_path.glob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '$""' in content:
                        remaining_count += 1
                        print(f"Still has issues: {file_path}")
            except:
                pass

    print(f"⚠️ Files still with issues: {remaining_count}")

if __name__ == "__main__":
    main()