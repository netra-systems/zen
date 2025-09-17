#!/usr/bin/env python3
"""
Aggressive syntax fixer for specific file
"""

import re

def fix_file_syntax(file_path):
    """Fix common syntax patterns in a specific file"""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    original_content = content

    # Fix unterminated docstrings
    content = re.sub(r'^\s*"([^"]*)\n', r'    """\1"""\n', content, flags=re.MULTILINE)

    # Fix docstrings that should be triple quoted
    content = re.sub(r'"([^"]*)"(?=\s*\n\s*return)', r'"""\1"""', content)
    content = re.sub(r'"([^"]*)"(?=\s*\n\s*[a-z_])', r'"""\1"""', content)

    # Fix f-strings with missing quotes
    content = re.sub(r'print\(f([^"\']*)\)', r'print(f"\1")', content)
    content = re.sub(r'print\(([^f][^"\']*)\)', r'print("\1")', content)

    # Fix missing quotes in print statements
    content = re.sub(r'print\(([^"\'()]+)\)', r'print("\1")', content)

    # Fix syntax patterns from the automated fixer
    patterns_to_fix = [
        (r'print\(f"([^"]*)\)', r'print(f"\1")'),
        (r'print\(([^f][^"]*)\)', r'print("\1")'),
        (r'"([^"]*)"([^"])', r'"\1"\2'),
        # Fix missing closing quotes
        (r'(["\'][^"\']*)\n', r'\1"\n'),
    ]

    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)

    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed syntax patterns in {file_path}")
        return True
    else:
        print(f"No changes needed for {file_path}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        fix_file_syntax(file_path)
    else:
        print("Usage: python fix_specific_file.py <file_path>")