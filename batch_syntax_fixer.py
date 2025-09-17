#!/usr/bin/env python3
"""
Batch Syntax Fixer - Fixes common syntax patterns
"""

import re
from pathlib import Path

def fix_common_syntax_errors(file_path):
    """Fix common syntax error patterns in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: Fix unmatched parentheses - { followed by )
        # payload = { ) -> payload = {
        content = re.sub(r'=\s*\{\s*\)', '= {', content)

        # Pattern 2: Fix closing brace/bracket with wrong parenthesis
        # "] )" -> "]"
        content = re.sub(r'\]\s*\)', ']', content)
        content = re.sub(r'\}\s*\)\)', '}', content)

        # Pattern 3: Fix unterminated strings with ) at end
        # print(" ) -> print("")
        content = re.sub(r'print\("\s*\)', 'print("")', content)

        # Pattern 4: Fix missing indentation after if/try/except statements
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            fixed_lines.append(line)

            # Check if this line ends with : and next line is not indented properly
            if (line.strip().endswith(':') and
                i + 1 < len(lines) and
                lines[i + 1].strip() and
                not lines[i + 1].startswith('    ') and
                not lines[i + 1].startswith('\t') and
                ('if ' in line or 'try:' in line or 'except' in line or 'else:' in line or 'for ' in line or 'while ' in line or 'def ' in line or 'class ' in line)):
                # Next line needs indentation
                next_line = lines[i + 1]
                if next_line.strip():
                    # Add proper indentation
                    current_indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * (current_indent + 4) + next_line.strip())
                    # Skip the original next line since we fixed it
                    lines[i + 1] = ""

        content = '\n'.join(fixed_lines)

        # Pattern 5: Fix specific unterminated string patterns
        content = re.sub(r'print\("([^"]*)\s*\)', r'print("\1")', content)

        # Pattern 6: Fix specific common patterns found in the scan
        content = content.replace('({ ))', '({})')
        content = content.replace('[ )', ']')
        content = content.replace('{ )', '}')

        # Pattern 7: Fix string literals with escaped quotes
        content = re.sub(r'"([^"]*)"s not', r'"\1" not', content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix syntax errors in critical test files."""

    # List of critical files with syntax errors (from our scan)
    critical_files = [
        "tests/e2e/test_websocket_alignment_fixes.py",
        "tests/e2e/test_websocket_auth_startup_timing.py",
        "tests/e2e/test_websocket_auth_timing.py",
        "tests/e2e/test_websocket_comprehensive.py",
        "tests/e2e/test_websocket_dev_docker_connection.py",
        "tests/e2e/test_websocket_message_alignment.py",
        "tests/e2e/test_websocket_realtime_features.py",
        "tests/e2e/test_websocket_session_regression.py",
        "tests/e2e/test_websocket_ui_timing.py",
        "tests/integration/test_agent_websocket_ssot.py",
        "tests/integration/test_websocket_factory_integration.py",
        "tests/integration/test_websocket_reconnection_robust.py"
    ]

    root = Path(".")
    fixed_count = 0

    print("BATCH SYNTAX FIXER")
    print("="*50)

    for file_path_str in critical_files:
        file_path = root / file_path_str
        if file_path.exists():
            print(f"Fixing: {file_path}")
            if fix_common_syntax_errors(file_path):
                fixed_count += 1
                print(f"  FIXED syntax errors")
            else:
                print(f"  - No changes needed")
        else:
            print(f"  ! File not found: {file_path}")

    print(f"\nFixed {fixed_count} files")
    return fixed_count

if __name__ == "__main__":
    main()