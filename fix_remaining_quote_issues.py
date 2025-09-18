#!/usr/bin/env python3
"""
Script to fix remaining complex quote syntax errors in mission critical test files.

This addresses the final 9 files from Issue #1059 that have duplicate docstrings
and mixed quote patterns that the basic script couldn't handle.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def fix_complex_quote_issues(file_path: Path) -> Tuple[bool, int]:
    """
    Fix complex quote syntax errors including duplicate docstrings.

    Returns:
        Tuple of (was_modified, num_fixes)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fixes_made = 0

        # Pattern 1: Duplicate docstrings with four quotes
        # """docstring.""""
        # """docstring.""""
        pattern1 = re.compile(r'(\s*"""[^"]*?)""""\s*\n\s*"""([^"]*?)""""', re.DOTALL)
        content = pattern1.sub(r'\1"""\2"""', content)
        fixes_made += len(pattern1.findall(original_content))

        # Pattern 2: Single line with four quotes at end
        pattern2 = re.compile(r'("""[^"]*?)""""', re.MULTILINE)
        content = pattern2.sub(r'\1"""', content)
        fixes_made += len(pattern2.findall(original_content))

        # Pattern 3: Remove duplicate identical docstring lines
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if this is a docstring line that's duplicated
            if '"""' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if line.strip() == next_line.strip() and '"""' in next_line:
                    # Skip the duplicate line
                    new_lines.append(line)
                    i += 2  # Skip the duplicate
                    fixes_made += 1
                    continue
            new_lines.append(line)
            i += 1

        content = '\n'.join(new_lines)

        # Write back if modified
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fixes_made

        return False, 0

    except Exception as e:
        print(f"ERROR processing {file_path}: {e}")
        return False, 0

def main():
    """Fix remaining complex quote issues in mission critical files."""

    # The 9 remaining problematic files
    problem_files = [
        "test_agent_death_fix_complete.py",
        "test_database_session_isolation.py",
        "test_docker_performance.py",
        "test_jwt_sync_ascii.py",
        "test_mock_policy_violations.py",
        "test_orchestration_edge_cases.py",
        "test_triage_agent_ssot_compliance.py",
        "test_triage_agent_ssot_violations.py",
        "test_websocket_unified_json_handler.py"
    ]

    script_path = Path(__file__).parent
    mission_critical_dir = script_path / "tests" / "mission_critical"

    if not mission_critical_dir.exists():
        print(f"ERROR: Mission critical directory not found: {mission_critical_dir}")
        sys.exit(1)

    print("Fixing remaining complex quote syntax errors...")

    total_files_fixed = 0
    total_fixes = 0

    for filename in problem_files:
        file_path = mission_critical_dir / filename

        if not file_path.exists():
            print(f"  WARNING: File not found: {filename}")
            continue

        was_modified, num_fixes = fix_complex_quote_issues(file_path)

        if was_modified:
            total_files_fixed += 1
            total_fixes += num_fixes
            print(f"  Fixed {filename}: {num_fixes} complex issues")
        else:
            print(f"  No changes needed: {filename}")

    print(f"\nSUMMARY:")
    print(f"  Files targeted: {len(problem_files)}")
    print(f"  Files fixed: {total_files_fixed}")
    print(f"  Total complex fixes: {total_fixes}")

    # Final verification
    print(f"\nFinal verification...")
    remaining_issues = 0

    for filename in problem_files:
        file_path = mission_critical_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '""""' in content:
                        remaining_issues += 1
                        print(f"  Still has issues: {filename}")
            except Exception as e:
                print(f"  Could not verify {filename}: {e}")

    if remaining_issues == 0:
        print("SUCCESS: All quadruple quote issues resolved!")
        print("Golden Path validation readiness: READY")
    else:
        print(f"PARTIAL: {remaining_issues} files still have complex quote issues")
        print("Golden Path validation readiness: IMPROVED")

    print(f"\nBUSINESS IMPACT:")
    print(f"  Critical test files fixed: {total_files_fixed}")
    print(f"  Issue #1059 completion: {((9 - remaining_issues) / 9) * 100:.1f}%")
    print(f"  $500K+ ARR test infrastructure: {'PROTECTED' if remaining_issues == 0 else 'IMPROVING'}")

if __name__ == "__main__":
    main()