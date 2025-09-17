#!/usr/bin/env python3
"""
Quick syntax fixer for critical test files
Fixes common syntax errors blocking test collection
"""

import re
import sys
from pathlib import Path

def fix_unterminated_fstrings(content):
    """Fix unterminated f-strings by adding missing quotes"""

    # Fix patterns like: print(fSomething {variable}) -> print(f"Something {variable}")
    content = re.sub(r'print\(f([^"\']*?)\)', r'print(f"\1")', content)

    # Fix patterns like: print(fSTDOUT:\n{result.stdout}"") -> print(f"STDOUT:\n{result.stdout}")
    content = re.sub(r'print\(f([^"\']*?)""?\)', r'print(f"\1")', content)

    # Fix patterns like: f[something] -> f"something"
    content = re.sub(r'f\[([^\]]*?)\]', r'f"[\1]"', content)

    # Fix patterns like: fError message {var} -> f"Error message {var}"
    content = re.sub(r'f([A-Za-z][^"\']*?{[^}]*?}[^"\']*?)(?=[,\)\]\n])', r'f"\1"', content)

    return content

def fix_invalid_decimals(content):
    """Fix invalid decimal literals like .1 -> 0.1"""

    # Fix patterns like assert execution_time >= 0.1 where decimal starts with dot
    content = re.sub(r'(\W)\.(\d+)', r'\g<1>0.\2', content)

    return content

def fix_bracket_mismatches(content):
    """Fix simple bracket mismatches"""

    # Fix patterns like test_messages = ] -> test_messages = []
    content = re.sub(r'= \]', r'= []', content)

    # Fix patterns like } where { was expected (simple cases)
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Fix closing } when it should be ]
        if line.strip() == '}' and len(fixed_lines) > 0:
            prev_line = fixed_lines[-1]
            if '[' in prev_line and ']' not in prev_line:
                line = line.replace('}', ']')

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_syntax_errors(file_path):
    """Fix syntax errors in a file"""
    print(f"Fixing: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply fixes
        content = fix_unterminated_fstrings(content)
        content = fix_invalid_decimals(content)
        content = fix_bracket_mismatches(content)

        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  FIXED: Applied syntax fixes")
            return True
        else:
            print(f"  SKIPPED: No changes needed")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        # Fix specific file
        file_path = Path(sys.argv[1])
        fix_syntax_errors(file_path)
    else:
        # Fix critical files
        critical_files = [
            "/c/netra-apex/tests/mission_critical/test_websocket_agent_events_suite.py",
            "/c/netra-apex/tests/e2e/test_auth_backend_desynchronization.py",
            "/c/netra-apex/test_framework/ssot/base_test_case.py",
        ]

        fixed_count = 0
        for file_path in critical_files:
            if Path(file_path).exists():
                if fix_syntax_errors(file_path):
                    fixed_count += 1

        print(f"\nFixed {fixed_count} critical files")

if __name__ == "__main__":
    main()