#!/usr/bin/env python3
"""
Quick test of syntax fixer on specific files
"""

import ast
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent

# Test files with known issues from the validation output
test_files = [
    "tests/mission_critical/performance_test_clean.py",
    "tests/mission_critical/standalone_performance_test.py",
    "tests/mission_critical/test_actions_to_meet_goals_websocket_failures.py",
    "tests/mission_critical/test_agent_execution_business_value.py",
    "tests/mission_critical/test_agent_factory_ssot_validation.py",
]

def fix_currency_references(file_path: Path):
    """Fix $500K+ references in files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace $500K+ with 500K in strings and comments
        original_content = content
        content = content.replace('$500K+', '500K')

        if content != original_content:
            # Create backup first
            backup_path = file_path.with_suffix('.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)

            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"Fixed: {file_path} (backup: {backup_path})")
            return True
        else:
            print(f"No fix needed: {file_path}")
            return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def check_syntax(file_path: Path):
    """Check if file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def main():
    print("Testing syntax fixer on specific problematic files")
    print("=" * 60)

    for file_rel_path in test_files:
        file_path = project_root / file_rel_path
        if not file_path.exists():
            print(f"SKIP: {file_rel_path} (not found)")
            continue

        print(f"\nProcessing: {file_rel_path}")

        # Check initial syntax
        is_valid, error = check_syntax(file_path)
        if is_valid:
            print(f"  Already valid syntax")
            continue

        print(f"  Syntax error: {error}")

        # Try to fix
        fixed = fix_currency_references(file_path)
        if fixed:
            # Check if fix worked
            is_valid_after, error_after = check_syntax(file_path)
            if is_valid_after:
                print(f"  SUCCESS: Fixed syntax error")
            else:
                print(f"  PARTIAL: Still has error: {error_after}")
        else:
            print(f"  NO CHANGES: Fix not applied")

if __name__ == "__main__":
    main()