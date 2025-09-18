#!/usr/bin/env python3
"""
Unterminated String Fixer - Fix the 542 files with unterminated string literals
"""

import ast
import os
import re
from pathlib import Path

def check_syntax_basic(file_path):
    """Check a single file for syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return None  # No error
    except Exception as e:
        return str(e)

def fix_unterminated_strings(file_path):
    """Fix unterminated string literals in a specific file."""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            fixed_line = line

            # Pattern 1: Line that is just a single quote at start
            if line.strip() == '"':
                fixed_line = '"""Empty docstring."""'

            # Pattern 2: Line that starts with quote but is unterminated
            elif re.match(r'^\s*"[^"]*$', line) and not line.strip().endswith('"""'):
                # Check if it's meant to be a docstring (after class/def or at module start)
                is_docstring = False
                if i == 0:  # First line of file
                    is_docstring = True
                elif i > 0:
                    prev_line = lines[i-1].strip()
                    if (prev_line.endswith(':') and
                        ('class ' in prev_line or 'def ' in prev_line or 'async def' in prev_line)):
                        is_docstring = True

                if is_docstring:
                    # Make it a proper docstring
                    fixed_line = line + '"""'
                else:
                    # Make it a regular string
                    fixed_line = line + '"'

            # Pattern 3: Fix specific broken docstring patterns
            fixed_line = re.sub(r'^(\s*)"([^"]*)"([^"]*)"$', r'\1"""\2\3"""', fixed_line)

            # Pattern 4: Lines that end with unterminated quote
            if ('"' in fixed_line and
                not '"""' in fixed_line and
                not "'''" in fixed_line and
                not fixed_line.strip().startswith('#')):

                # Count quotes to see if we have an odd number (unterminated)
                quote_count = fixed_line.count('"')
                if quote_count % 2 == 1:
                    fixed_line = fixed_line + '"'

            fixed_lines.append(fixed_line)

        # Apply additional fixes for common patterns
        content = '\n'.join(fixed_lines)

        # Fix specific broken patterns that appear across files
        content = re.sub(r'super\(\).__init__\("formatted_string\)', 'super().__init__()', content)
        content = re.sub(r'print\("formatted_string\)', 'print("")', content)
        content = re.sub(r'"formatted_string\)', '""', content)

        # Only write if content actually changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Verify the fix worked
            error = check_syntax_basic(file_path)
            if error:
                return False, f"Fix failed: {error}"
            else:
                return True, "Fixed successfully"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error processing file: {str(e)}"

def main():
    """Fix all files with unterminated string literal errors."""

    # Get list of files with unterminated string errors
    test_patterns = [
        "tests/e2e/test_websocket*.py",
        "tests/mission_critical/*.py",
        "tests/integration/test_websocket*.py",
        "tests/integration/test_*websocket*.py"
    ]

    root = Path(".")
    all_files = set()

    for pattern in test_patterns:
        all_files.update(root.glob(pattern))

    # Filter to only files with unterminated string errors
    files_to_fix = []
    for file_path in all_files:
        if file_path.suffix == '.py' and "__pycache__" not in str(file_path):
            error = check_syntax_basic(file_path)
            if error and 'unterminated string literal' in error:
                files_to_fix.append(file_path)

    print(f"UNTERMINATED STRING FIXER")
    print("="*60)
    print(f"Found {len(files_to_fix)} files with unterminated string errors")
    print()

    fixed_count = 0
    still_broken = 0
    no_change = 0

    for file_path in sorted(files_to_fix):
        print(f"Fixing: {file_path}")
        success, message = fix_unterminated_strings(file_path)

        if success:
            print(f"  SUCCESS: {message}")
            fixed_count += 1
        elif "No changes needed" in message:
            print(f"  SKIPPED: {message}")
            no_change += 1
        else:
            print(f"  FAILED: {message}")
            still_broken += 1

    print()
    print("RESULTS:")
    print(f"  Files fixed: {fixed_count}")
    print(f"  Files still broken: {still_broken}")
    print(f"  Files needing no changes: {no_change}")
    print(f"  Total processed: {len(files_to_fix)}")

    if fixed_count > 0:
        print(f"\nProgress: {fixed_count} unterminated string errors resolved!")

    if still_broken > 0:
        print(f"Remaining work: {still_broken} files still need manual review")

    return fixed_count

if __name__ == "__main__":
    fixed = main()
    print(f"\nFinal result: {fixed} files fixed")