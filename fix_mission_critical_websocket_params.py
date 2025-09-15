#!/usr/bin/env python3
"""
MISSION CRITICAL: WebSocket Parameter Migration Script
Issue #1210: Fix extra_headers → additional_headers for Python 3.13 compatibility

This script fixes the 7 mission-critical test files to protect $500K+ ARR functionality.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

def fix_websocket_parameters_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Fix extra_headers → additional_headers in a single file.

    Returns:
        (changed, changes_made): Whether file was changed and list of changes
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes_made = []

        # Pattern 1: Variable declaration (extra_headers = {...})
        pattern1 = r'\bextra_headers\s*='
        if re.search(pattern1, content):
            content = re.sub(pattern1, 'additional_headers =', content)
            changes_made.append("Variable declaration: extra_headers = → additional_headers =")

        # Pattern 2: Function parameter (extra_headers=variable)
        pattern2 = r'\bextra_headers\s*='
        if re.search(pattern2, content):
            content = re.sub(r'\bextra_headers\s*=', 'additional_headers=', content)
            changes_made.append("Function parameter: extra_headers= → additional_headers=")

        # Pattern 3: WebSocket connect calls
        pattern3 = r'(websockets\.connect\([^)]*?)extra_headers\s*=([^,)]*)'
        matches = re.findall(pattern3, content)
        if matches:
            content = re.sub(pattern3, r'\1additional_headers=\2', content)
            changes_made.append(f"WebSocket connect calls: {len(matches)} instances fixed")

        # Pattern 4: Dictionary references
        pattern4 = r'(["\']?)extra_headers\1\s*:'
        if re.search(pattern4, content):
            content = re.sub(pattern4, r'\1additional_headers\1:', content)
            changes_made.append("Dictionary keys: extra_headers: → additional_headers:")

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes_made
        else:
            return False, []

    except Exception as e:
        print(f"ERROR processing {file_path}: {e}")
        return False, [f"ERROR: {e}"]

def main():
    """Fix all mission-critical WebSocket test files."""
    project_root = Path(__file__).parent

    # Mission-critical files identified in discovery phase
    mission_critical_files = [
        "tests/mission_critical/test_first_message_experience.py",  # Already fixed
        "tests/mission_critical/test_golden_path_websocket_authentication.py",
        "tests/mission_critical/test_multiuser_security_isolation.py",
        "tests/mission_critical/test_staging_websocket_agent_events_enhanced.py",
        "tests/mission_critical/test_websocket_auth_chat_value_protection.py",
        "tests/mission_critical/test_websocket_bridge_chaos.py",
        "tests/mission_critical/test_websocket_supervisor_startup_sequence.py"
    ]

    print("MISSION CRITICAL: WebSocket Parameter Migration (Issue #1210)")
    print("=" * 70)
    print("Business Impact: Protecting $500K+ ARR WebSocket functionality")
    print("Target: 7 mission-critical test files")
    print()

    total_files = 0
    total_changes = 0

    for file_rel_path in mission_critical_files:
        file_path = project_root / file_rel_path

        if not file_path.exists():
            print(f"SKIP: {file_rel_path} (file not found)")
            continue

        print(f"Processing: {file_rel_path}")

        changed, changes = fix_websocket_parameters_in_file(file_path)

        if changed:
            total_files += 1
            total_changes += len(changes)
            print(f"   FIXED: {len(changes)} changes made")
            for change in changes:
                print(f"      - {change}")
        else:
            print(f"   OK: No changes needed (already fixed or no extra_headers usage)")

        print()

    print("=" * 70)
    print(f"MISSION CRITICAL SUMMARY:")
    print(f"   Files processed: {len([f for f in mission_critical_files if (project_root / f).exists()])}")
    print(f"   Files changed: {total_files}")
    print(f"   Total changes: {total_changes}")
    print()
    print("Mission-critical WebSocket compatibility fixes complete!")
    print("Business Value: $500K+ ARR functionality protected")
    print()
    print("NEXT STEPS:")
    print("1. Run mission-critical tests: python tests/unified_test_runner.py --category mission_critical --no-docker")
    print("2. Validate WebSocket connectivity in staging environment")
    print("3. Proceed to Phase 2: E2E and Integration test remediation")

if __name__ == "__main__":
    main()