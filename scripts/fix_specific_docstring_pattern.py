#!/usr/bin/env python3
"""
Targeted fix for specific docstring pattern in corrupted test files.

Fixes the pattern where docstrings use single quotes instead of triple quotes.
"""

import sys
import re
from pathlib import Path

def fix_docstring_patterns(file_path: Path):
    """Fix malformed docstring patterns in a specific file."""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Pattern 1: Fix lone quote at start of docstring
    content = re.sub(r'^(\s+)"$', r'\1"""', content, flags=re.MULTILINE)

    # Pattern 2: Fix lone quote at end of docstring
    content = re.sub(r'^(\s*)"$', r'\1"""', content, flags=re.MULTILINE)

    # Pattern 3: Fix single quotes for method docstrings
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # Look for method definition followed by malformed docstring
        if (line.strip().startswith('def ') and line.strip().endswith(':') and
            i + 1 < len(lines) and lines[i + 1].strip().startswith('"') and
            not lines[i + 1].strip().startswith('"""')):

            fixed_lines.append(line)

            # Fix the docstring line
            next_line = lines[i + 1]
            if next_line.strip() == '"':
                # Lone quote - replace with triple quotes
                fixed_lines.append(next_line.replace('"', '"""'))
            elif next_line.strip().startswith('"') and not next_line.strip().startswith('"""'):
                # Single quote at start - make it triple
                fixed_lines.append(next_line.replace('"', '"""', 1))
            else:
                fixed_lines.append(next_line)

        elif (line.strip().endswith('"') and not line.strip().endswith('"""') and
              i > 0 and '"""' in lines[i-5:i]):  # Check if we're in a docstring
            # End of docstring with single quote
            fixed_lines.append(line.replace('"', '"""'))
        else:
            fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    # Additional fixes for specific patterns
    content = re.sub(r'(\s+)"([^"]+)"$', r'\1"""\2"""', content, flags=re.MULTILINE)

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed docstring patterns in {file_path}")
        return True
    else:
        print(f"No changes needed in {file_path}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_specific_docstring_pattern.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    fix_docstring_patterns(file_path)

if __name__ == "__main__":
    main()