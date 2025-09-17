#!/usr/bin/env python3
"""
Final Syntax Error Fixer - Fix remaining unterminated string literals and specific patterns
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

def fix_unterminated_strings(content):
    """Fix unterminated string literals"""
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        fixed_line = line

        # Pattern 1: Fix lines that start with just a quote
        if line.strip() == '"':
            fixed_line = '"""'

        # Pattern 2: Fix lines with unterminated docstrings at start
        elif re.match(r'^\s*"[^"]*$', line) and not line.strip().endswith('"""'):
            # Check if it's a docstring (after class/def or at module start)
            if i == 0 or (i > 0 and ('class ' in lines[i-1] or 'def ' in lines[i-1] or 'async def' in lines[i-1])):
                fixed_line = line + '"""'
            else:
                # Regular string, close it
                fixed_line = line + '"'

        # Pattern 3: Fix unterminated strings with content
        elif re.search(r'"[^"]*$', line) and not line.strip().startswith('#'):
            # Don't fix if it's already a valid triple quote
            if not '"""' in line and not "'''" in line:
                # Check if quote is opening or closing
                quote_count = line.count('"')
                if quote_count % 2 == 1:  # Odd number means unterminated
                    fixed_line = line + '"'

        # Pattern 4: Fix specific malformed patterns
        fixed_line = re.sub(r'super\(\).__init__\("formatted_string\)', 'super().__init__()', fixed_line)
        fixed_line = re.sub(r'print\("formatted_string\)', 'print("")', fixed_line)
        fixed_line = re.sub(r'"formatted_string\)', '""', fixed_line)
        fixed_line = re.sub(r'env\.set\("TESTING, 1", "test_websocket_comprehensive\)', 'env.set("TESTING", "1")', fixed_line)

        # Pattern 5: Fix missing quotes in specific contexts
        if 'ERROR CRITICAL:' in fixed_line:
            fixed_line = re.sub(r'ERROR CRITICAL: ([^"]+)$', r'# ERROR CRITICAL: \1', fixed_line)

        fixed_lines.append(fixed_line)

    return '\n'.join(fixed_lines)

def fix_specific_patterns(content):
    """Fix other specific syntax error patterns"""

    # Fix missing quotes in assert statements
    content = re.sub(r'assert ([^,]+), ([^"]+)!"', r'assert \1, "\2!"', content)
    content = re.sub(r'assert ([^,]+), ([^"]+)\+"', r'assert \1, "\2"', content)

    # Fix malformed f-strings
    content = re.sub(r'fHealth service', r'"Health service', content)
    content = re.sub(r'f"([^"]*)"([^"]*)"', r'f"\1\2"', content)

    # Fix print statements with malformed strings
    content = re.sub(r'print\("([^"]*)\)\s*\+\s*"([^"]*)"', r'print("\1\2")', content)
    content = re.sub(r'print\(([^)]*)"([^"]*)\)', r'print(\1"\2")', content)

    # Fix string concatenation issues
    content = re.sub(r'" \+ "([^"]*)"', r' + "\1"', content)
    content = re.sub(r'"([^"]*)" \+ ([^"]+)"', r'"\1" + "\2"', content)

    # Fix missing quotes in specific test patterns
    content = re.sub(r'"([^"]*)"([^"]*)"([^"]*)"([^"]*)"', r'"\1\2\3\4"', content)

    return content

def fix_indentation_issues(content):
    """Fix indentation after control structures"""
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        fixed_line = line

        # Check if previous line ends with ':' and current line is not indented
        if i > 0:
            prev_line = lines[i-1].strip()
            if (prev_line.endswith(':') and
                (prev_line.startswith('if ') or prev_line.startswith('try:') or
                 prev_line.startswith('except') or prev_line.startswith('else:') or
                 prev_line.startswith('def ') or prev_line.startswith('class ') or
                 prev_line.startswith('async def') or prev_line.startswith('for ') or
                 prev_line.startswith('while ') or prev_line.startswith('with '))):

                # If current line is not indented or is pass, fix it
                if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                    if line.strip() == 'pass':
                        fixed_line = '    pass'
                    else:
                        # Add 4 spaces of indentation
                        fixed_line = '    ' + line.lstrip()

        fixed_lines.append(fixed_line)

    return '\n'.join(fixed_lines)

def fix_file(file_path):
    """Fix syntax errors in a single file"""
    try:
        # Check if file has syntax errors
        error = check_syntax(file_path)
        if not error:
            return False, "No errors found"

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Apply fixes
        content = original_content
        content = fix_unterminated_strings(content)
        content = fix_specific_patterns(content)
        content = fix_indentation_issues(content)

        # Only write if content changed
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

def main():
    """Find and fix remaining syntax errors"""

    # Focus on critical test directories
    test_patterns = [
        "tests/e2e/test_websocket*.py",
        "tests/mission_critical/*.py",
        "tests/integration/test_websocket*.py",
        "tests/integration/test_*websocket*.py"
    ]

    root = Path(".")
    files_to_fix = set()

    # Collect files with syntax errors
    for pattern in test_patterns:
        files_to_fix.update(root.glob(pattern))

    print(f"FINAL SYNTAX FIXER - Processing {len(files_to_fix)} files")
    print("="*60)

    fixed_count = 0
    error_count = 0

    for file_path in sorted(files_to_fix):
        if file_path.suffix == '.py' and "__pycache__" not in str(file_path):
            # Check if file has syntax errors
            error = check_syntax(file_path)
            if error:
                print(f"FIXING: {file_path}")
                print(f"  Error: {error}")

                success, message = fix_file(file_path)
                if success:
                    print(f"  FIXED: {message}")
                    fixed_count += 1
                else:
                    print(f"  FAILED: {message}")
                    error_count += 1
                print()

    print(f"\nSUMMARY:")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with remaining errors: {error_count}")

    return fixed_count, error_count

if __name__ == "__main__":
    fixed, errors = main()
    print(f"\nFinal result: {fixed} files fixed, {errors} files still have errors")