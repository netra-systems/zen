#!/usr/bin/env python3
"""Fix files that start with incorrect number of quotes"""

import os
import glob

def fix_file(filepath):
    """Fix a single file's docstring quotes"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Fix files that start with wrong number of quotes
        if content.startswith('""""""'):
            content = '"""' + content[6:]
            print(f"Fixed 6->3 quotes: {filepath}")
        elif content.startswith('"""""'):
            content = '"""' + content[5:]
            print(f"Fixed 5->3 quotes: {filepath}")
        elif content.startswith('""""'):
            content = '"""' + content[4:]
            print(f"Fixed 4->3 quotes: {filepath}")

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def main():
    # Find all Python test files
    test_dirs = [
        "/c/netra-apex/tests/e2e",
        "/c/netra-apex/tests/integration",
        "/c/netra-apex/tests/mission_critical"
    ]

    fixed_count = 0

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for filepath in glob.glob(f"{test_dir}/**/*.py", recursive=True):
                if fix_file(filepath):
                    fixed_count += 1

    print(f"\nFixed {fixed_count} files with docstring quote issues")

if __name__ == "__main__":
    main()