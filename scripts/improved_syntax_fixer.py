#!/usr/bin/env python3
"""
Improved Syntax Fixer for Test Files
===================================

Targeted fixes for specific syntax error patterns in test files.
"""

import ast
import os
import re
from typing import List, Tuple

def fix_indentation_error_simple(file_path: str) -> bool:
    """Fix simple indentation errors where a statement after : is not indented."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # If this line ends with : and is a control statement
            if (stripped.endswith(':') and
                any(stripped.startswith(keyword) for keyword in
                    ['if ', 'for ', 'while ', 'def ', 'class ', 'try:', 'except', 'else:', 'elif ', 'finally:', 'with ', 'async def '])):

                fixed_lines.append(line)

                # Check if next line needs indentation
                if i + 1 < len(lines):
                    next_line = lines[i + 1]

                    # If next line exists and is not empty/comment
                    if (next_line.strip() and
                        not next_line.strip().startswith('#') and
                        not next_line.strip().startswith('"""') and
                        not next_line.strip().startswith("'''") and
                        len(next_line) - len(next_line.lstrip()) <= len(line) - len(line.lstrip())):

                        # Calculate proper indentation
                        current_indent = len(line) - len(line.lstrip())
                        proper_indent = ' ' * (current_indent + 4)

                        # Apply fix to next line
                        lines[i + 1] = proper_indent + next_line.lstrip()
            else:
                fixed_lines.append(line)

        # Write fixed content back
        fixed_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        # Verify syntax is now valid
        ast.parse(fixed_content)
        return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def fix_bracket_mismatches(file_path: str) -> bool:
    """Fix bracket/parenthesis mismatches."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Common bracket mismatch patterns
        fixes = [
            (r'\[\s*\)', '[]'),  # [ ) -> [ ]
            (r'\{\s*\)', '{}'),  # { ) -> { }
            (r'\(\s*\]', '()'),  # ( ] -> ( )
            (r'\(\s*\}', '()'),  # ( } -> ( )
            (r'\[\s*\}', '[]'),  # [ } -> [ ]
            (r'\{\s*\]', '{}'),  # { ] -> { }
        ]

        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # Verify syntax
        ast.parse(content)
        return True

    except Exception as e:
        print(f"Error fixing brackets in {file_path}: {e}")
        return False

def fix_unterminated_strings(file_path: str) -> bool:
    """Fix unterminated string literals."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            original_line = line

            # Count quotes to detect unterminated strings
            if line.count('"') % 2 == 1 and not line.strip().startswith('#'):
                # Odd number of quotes - likely unterminated
                line = line + '"'
            elif line.count("'") % 2 == 1 and '"""' not in line and "'''" not in line and not line.strip().startswith('#'):
                # Odd number of single quotes - likely unterminated
                line = line + "'"

            fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

        # Verify syntax
        ast.parse(fixed_content)
        return True

    except Exception as e:
        print(f"Error fixing strings in {file_path}: {e}")
        return False

def fix_unexpected_indents(file_path: str) -> bool:
    """Fix unexpected indent errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            if i == 0:
                fixed_lines.append(line)
                continue

            # Check for unexpected indentation
            prev_line = lines[i-1].strip()
            current_indent = len(line) - len(line.lstrip())

            # If previous line doesn't end with : but current line is indented
            if (line.strip() and
                not prev_line.endswith(':') and
                current_indent > 0 and
                not line.strip().startswith('#') and
                not prev_line.startswith('"""') and
                not prev_line.startswith("'''")):

                # Remove unexpected indentation
                fixed_lines.append(line.lstrip())
            else:
                fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        # Verify syntax
        ast.parse(fixed_content)
        return True

    except Exception as e:
        print(f"Error fixing unexpected indents in {file_path}: {e}")
        return False

def fix_single_file(file_path: str) -> bool:
    """Apply all fixes to a single file."""
    print(f"Fixing: {file_path}")

    # Try each fix type
    fixes = [
        fix_indentation_error_simple,
        fix_bracket_mismatches,
        fix_unterminated_strings,
        fix_unexpected_indents
    ]

    for fix_func in fixes:
        try:
            if fix_func(file_path):
                print(f"  ✓ Fixed with {fix_func.__name__}")
                return True
        except Exception as e:
            print(f"  ✗ {fix_func.__name__} failed: {e}")
            continue

    print(f"  ✗ All fixes failed for {file_path}")
    return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python improved_syntax_fixer.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if fix_single_file(file_path):
        print("✓ File fixed successfully")
    else:
        print("✗ Failed to fix file")