#!/usr/bin/env python3
"""
Fix Unicode encoding issues in test files - addresses charmap errors from Issue #1332
"""

import os
import sys
from pathlib import Path
import re

def fix_unicode_in_file(file_path: Path) -> bool:
    """Fix Unicode encoding issues in a file"""
    try:
        # Read with UTF-8 and ignore problematic characters
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Common Unicode fixes
        fixes_made = False

        # Replace common problematic Unicode characters
        problematic_chars = {
            '\u274c': 'X',  # Cross mark
            '\u2705': 'CHECK',  # Check mark
            '\u2713': 'CHECK',  # Check mark
            '\u26a0': 'WARNING',  # Warning
            '\u2192': '->',  # Right arrow
            '\u2190': '<-',  # Left arrow
        }

        for unicode_char, replacement in problematic_chars.items():
            if unicode_char in content:
                content = content.replace(unicode_char, replacement)
                fixes_made = True

        # Fix invalid escape sequences in strings
        # Look for patterns like \s, \., \( in docstrings/comments
        lines = content.split('\n')
        for i, line in enumerate(lines):
            original_line = line

            # Fix escape sequences in docstrings/comments
            if '"""' in line or "'''" in line or line.strip().startswith('#'):
                line = re.sub(r'\\([^nrtfbav\'\"\\])', r'\\\\\\1', line)
                if line != original_line:
                    lines[i] = line
                    fixes_made = True

        if fixes_made:
            # Write back with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

    return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        test_dir = Path("tests")

    if not test_dir.exists():
        print(f"Directory {test_dir} does not exist")
        sys.exit(1)

    print(f"Fixing Unicode encoding issues in {test_dir}")

    total_files = 0
    fixed_files = 0

    for py_file in test_dir.rglob("*.py"):
        total_files += 1
        if fix_unicode_in_file(py_file):
            fixed_files += 1
            print(f"Fixed: {py_file}")

    print(f"\nResults:")
    print(f"  Total files: {total_files}")
    print(f"  Files fixed: {fixed_files}")

    return fixed_files

if __name__ == "__main__":
    main()