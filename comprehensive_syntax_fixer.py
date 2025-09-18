#!/usr/bin/env python3
"""
Comprehensive Syntax Fixer - Handles all the remaining syntax error patterns
"""

import re
from pathlib import Path

def fix_comprehensive_syntax_errors(file_path):
    """Fix all types of syntax errors found in the scan."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: Fix unterminated string literals
        # print(" ) -> print("")
        content = re.sub(r'print\("([^"]*)\s*\)', r'print("\1")', content)
        content = re.sub(r'print\(\'\s*\)', "print('')", content)

        # Pattern 2: Fix unmatched parentheses/braces
        # { ) -> {}
        content = re.sub(r'\{\s*\)', '{}', content)
        content = re.sub(r'\[\s*\)', '[]', content)
        content = re.sub(r'\(\s*\}', '()', content)

        # Pattern 3: Fix complex unmatched patterns
        # ({ )) -> ({})
        content = re.sub(r'\(\{\s*\)\)', '({})', content)
        content = re.sub(r'\[\s*\)\)', '[]', content)

        # Pattern 4: Fix common dictionary/list syntax errors
        # payload = { ) -> payload = {}
        content = re.sub(r'=\s*\{\s*\)', ' = {}', content)
        content = re.sub(r'=\s*\[\s*\)', ' = []', content)

        # Pattern 5: Fix unmatched closing braces and brackets
        content = re.sub(r'\}\s*\)', '}', content)
        content = re.sub(r'\]\s*\)', ']', content)

        # Pattern 6: Fix specific syntax errors found in files
        # Fix cases like: async with websockets.connect( )
        content = re.sub(r'async with ([^(]+)\(\s*\)', r'async with \1()', content)

        # Fix line-by-line issues
        lines = content.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Pattern 7: Fix indentation issues after if/try/except/for/while statements
            if (line.strip().endswith(':') and
                i + 1 < len(lines) and
                lines[i + 1].strip() and
                not lines[i + 1].startswith('    ') and
                not lines[i + 1].startswith('\t')):

                # Check if this is a control flow statement that needs indentation
                if any(keyword in line for keyword in ['if ', 'try:', 'except', 'for ', 'while ', 'else:', 'elif ']):
                    fixed_lines.append(line)
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith('#'):
                        # Calculate proper indentation
                        current_indent = len(line) - len(line.lstrip())
                        fixed_lines.append(' ' * (current_indent + 4) + next_line)
                        i += 2  # Skip the next line since we processed it
                        continue

            # Pattern 8: Fix function definitions missing proper structure
            if line.strip().startswith('def ') and not line.strip().endswith(':'):
                if '(' in line and ')' in line:
                    fixed_lines.append(line + ':' if not line.endswith(':') else line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

            i += 1

        content = '\n'.join(fixed_lines)

        # Pattern 9: Fix specific string literal issues
        # Fix mixed quotes in strings
        content = re.sub(r'"([^"]*)"([^"]*)"([^"]*)"', r'"\1\2\3"', content)

        # Pattern 10: Fix remaining unmatched patterns found in the scan
        content = re.sub(r'(\w+)\s*=\s*\{\s*\)\)', r'\1 = {}', content)
        content = re.sub(r'(\w+)\s*=\s*\[\s*\)', r'\1 = []', content)

        # Pattern 11: Fix string interpolation issues
        content = re.sub(r'f"([^"]*)\{\s*\)', r'f"\1{}"', content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all remaining syntax errors comprehensively."""

    # Get all test files from our critical areas
    test_patterns = [
        "tests/e2e/test_websocket*.py",
        "tests/integration/test_*websocket*.py",
        "tests/mission_critical/*.py"
    ]

    root = Path(".")
    files_to_fix = set()

    for pattern in test_patterns:
        files_to_fix.update(root.glob(pattern))

    fixed_count = 0
    total_files = len(files_to_fix)

    print("COMPREHENSIVE SYNTAX FIXER")
    print("="*50)
    print(f"Processing {total_files} files...")

    for file_path in sorted(files_to_fix):
        if file_path.suffix == '.py' and "__pycache__" not in str(file_path):
            if fix_comprehensive_syntax_errors(file_path):
                fixed_count += 1
                print(f"FIXED: {file_path}")

    print(f"\nFixed {fixed_count} files out of {total_files} processed")
    return fixed_count

if __name__ == "__main__":
    main()