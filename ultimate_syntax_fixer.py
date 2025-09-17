#!/usr/bin/env python3
"""
Ultimate Syntax Fixer - Fix the most common patterns causing syntax errors
"""

import ast
import os
import re
from pathlib import Path
import traceback

def check_syntax(file_path):
    """Check a single file for syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return None  # No error
    except Exception as e:
        return str(e)

def fix_file_aggressive(file_path):
    """Fix syntax errors using aggressive pattern matching"""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            fixed_line = line

            # Pattern 1: Line that starts with just a quote
            if line.strip() == '"':
                # Check if next line exists and looks like content
                if i + 1 < len(lines) and lines[i + 1].strip():
                    fixed_line = '"""'
                else:
                    fixed_line = '""'

            # Pattern 2: Line with unterminated docstring at start of line
            elif re.match(r'^\s*"[^"]*$', line) and not line.strip().endswith('"""'):
                # If line contains actual content, make it a proper docstring
                if len(line.strip()) > 1:  # More than just quote
                    fixed_line = line + '"""'
                else:
                    fixed_line = '"""'

            # Pattern 3: Lines with malformed string patterns
            fixed_line = re.sub(r'"Real WebSocket connection for testing instead of mocks\."$',
                               '"""Real WebSocket connection for testing instead of mocks."""', fixed_line)

            # Pattern 4: Fix specific broken patterns
            fixed_line = re.sub(r'^(\s*)"([^"]*)"([^"]*)"$', r'\1"""\2\3"""', fixed_line)

            # Pattern 5: Fix unterminated strings at end of line
            if re.search(r'"[^"]*$', fixed_line) and not '"""' in fixed_line and not "'''" in fixed_line:
                quote_count = fixed_line.count('"')
                if quote_count % 2 == 1:  # Odd number means unterminated
                    fixed_line = fixed_line + '"'

            fixed_lines.append(fixed_line)

        content = '\n'.join(fixed_lines)

        # Additional global fixes
        content = re.sub(r'super\(\).__init__\("formatted_string\)', 'super().__init__()', content)
        content = re.sub(r'print\("formatted_string\)', 'print("")', content)
        content = re.sub(r'"formatted_string\)', '""', content)

        # Write the file back only if it changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Verify the fix worked
            new_error = check_syntax(file_path)
            if new_error:
                return False, f"Fix failed: {new_error}"
            else:
                return True, "Fixed successfully"
        else:
            return False, "No changes made"

    except Exception as e:
        return False, f"Error processing file: {str(e)}"

def mass_fix_files():
    """Fix all files with syntax errors in critical directories"""

    # Focus on specific directories with errors
    test_patterns = [
        "tests/e2e/test_websocket*.py",
        "tests/mission_critical/*.py",
        "tests/integration/test_websocket*.py",
        "tests/integration/test_*websocket*.py"
    ]

    root = Path(".")
    files_to_fix = set()

    # Collect all matching files
    for pattern in test_patterns:
        files_to_fix.update(root.glob(pattern))

    print(f"ULTIMATE SYNTAX FIXER - Processing {len(files_to_fix)} files")
    print("="*80)

    fixed_count = 0
    still_broken = 0
    skipped = 0

    # Process files in batches
    for file_path in sorted(files_to_fix):
        if file_path.suffix == '.py' and "__pycache__" not in str(file_path):

            # Check if file has syntax errors
            error = check_syntax(file_path)
            if error:
                print(f"FIXING: {file_path}")
                success, message = fix_file_aggressive(file_path)

                if success:
                    print(f"  FIXED: {message}")
                    fixed_count += 1
                else:
                    print(f"  STILL BROKEN: {message}")
                    still_broken += 1
            else:
                skipped += 1
                if skipped % 50 == 0:
                    print(f"  Skipped {skipped} files (no syntax errors)")

    print(f"\nULTIMATE RESULTS:")
    print(f"Files fixed: {fixed_count}")
    print(f"Files still broken: {still_broken}")
    print(f"Files skipped (no errors): {skipped}")

    return fixed_count, still_broken

if __name__ == "__main__":
    fixed, still_broken = mass_fix_files()
    print(f"\nFinal Status: {fixed} files fixed, {still_broken} files still need manual fixes")